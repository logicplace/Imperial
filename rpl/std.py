#-*- coding:utf-8 -*-
#
# Copyright (C) 2012-2013 Sapphire Becker (http://logicplace.com)
#
# This file is part of Imperial Exchange.
#
# Imperial Exchange is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Imperial Exchange is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Imperial Exchange.  If not, see <http://www.gnu.org/licenses/>.
#

import os, re, Image
import rpl, helper
from rpl import RPLError, RPLBadType
from copy import deepcopy
from math import ceil
from StringIO import StringIO
from collections import OrderedDict as odict

def register(rpl):
	rpl.registerStruct(Data)
	rpl.registerStruct(Format)
	rpl.registerStruct(Map)
	rpl.registerStruct(IOStatic)
	rpl.registerStruct(GenericGraphic)

	rpl.registerType(Bin)
	rpl.registerType(Pixel)
	rpl.registerType(Color)
	rpl.registerType(ReadDir)
	rpl.registerType(Math)
#enddef

def printHelp(moreInfo=[]):
	helper.genericHelp(globals(), moreInfo,
		"std is the standard library for RPL.", "std", [
			# Structs
			Data, Format,
			Map, IOStatic,
			GenericGraphic,
			# Types
			Bin, Pixel,
			Color, ReadDir,
			Math,
		]
	)
#enddef

class DataFile(rpl.Share):
	"""
	.rpl export for data structs.
	"""
	def __init__(self, inFile=None):
		self.base = []
		self.comment = ""
		if inFile is not None: self.read(inFile)
	#enddef

	def read(self):
		"""
		Read from .rpl data file.
		"""
		rpl = self.rpl
		raw = helper.readFrom(self.path)

		base = []
		parents = []
		for token in rpl.specification.finditer(raw):
			groups = token.groups() # Used later
			dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = groups
			sstr = dstr or sstr # Double or single

			# Find the position (used for ref and errors)
			pos = token.start()
			line, char = raw.count("\n",0,pos) + 1, pos - raw.rfind("\n",0,pos) + 1

			add, skipSubInst = None, None

			try:
				if flow and flow in "{}": raise RPLError("Structs not allowed in data files")
				elif flow == "[":
					# Begins list
					parents.append([])
				elif flow == "]":
					# End list
					if parents:
						add = ("list", parents.pop())
						skipSubInst = True
					else: raise RPLError("] without a [.")
				elif sstr or mstr or num or ref or lit:
					add = rpl.parseData(groups, line=line, char=char)
				else: continue

				if add:
					val = rpl.parseCreate(add, None, None, line, char, skipSubInst)

					if parents: parents[-1].append(val)
					else: base.append(val)
				#endif
			except RPLError as err:
				helper.err("Error in line %i char %i: %s" % (
					line, char, err.args[0]
				))
			#endtry
		#endfor

		self.base = base
	#enddef

	def write(self):
		"""
		Write data to a given file.
		"""
		# TODO: Prettyprinting
		comment = "# " + self.comment if self.comment else ""
		helper.writeTo(self.path, comment + os.linesep.join(map(unicode, self.base)))
	#enddef

	def add(self, item):
		"""
		Add item to data. Must be RPLData type.
		"""
		if not isinstance(item, rpl.RPLData):
			raise RPLError("Tried to add non-data to rpl data file.")
		#endif
		self.base.append(item)
	#enddef

	def __getitem__(self, key): return self.base[key]
	def __len__(self): return len(self.base)

	def __iter__(self):
		try: self.iter
		except AttributeError: self.iter = -1
		return self
	#enddef

	# Atypical implementation of next I think, but it makes the code look nicer.
	def next(self):
		try: self.iter += 1
		except AttributeError: self.iter = 0
		try: return self[self.iter]
		except IndexError: raise StopIteration
	#enddef
#endclass

class ImageFile(rpl.Share):
	def __init__(self, width=0, height=0):
		self.dimensions = (width, height)
		self.image = None
		self.pixels = None
	#enddef

	def read(self):
		if self.image is None: self.image = Image.open(self.path).convert("RGBA")
	#enddef

	def write(self):
		if self.image is None: return # Maybe throw an exception?
		ext = os.path.splitext(self.path)[1][1:].lower()
		# Cannot save alpha..
		if ext == "bmp": self.image = self.image.convert("RGB")
		self.image.save(self.path)
	#enddef

	def newImage(self, width=1, height=1, blank=0xffffff):
		self.image = Image.new("RGBA", (width, height))
		self.image.paste(blank, (0, 0, width, height))
		self.pixels = self.image.load()
	#endif

	def ensureSize(self, width, height):
		# Only necessary when writing, remember!
		if self.image is None: return self.newImage(width, height)
		curWidth, curHeight = self.image.size
		if curWidth < width or curHeight < height:
			width = max(curWidth, width)
			height = max(curHeight, height)
			region = self.image.crop((0, 0, width, height))
			region.load()
			self.image = self.image.resize((width, height))
			self.image.paste(0xffffff, (0, 0, width, height))
			self.image.paste(region, (0, 0))
		#endif
	#enddef

	def addRect(self, data, left, top, width, height):
		if self.image is None: self.newImage()
		region = Image.new("RGBA", (width, height))
		region.putdata(data)
		self.image.paste(region, (left, top), region)
	#enddef

	def addImage(self, image, left, top):
		if self.image is None: self.newImage()
		self.image.paste(image, (left, top), image)
	#enddef

	def addPixel(self, rgba, x, y):
		if self.image is None: self.newImage()
		self.pixels[x, y] = rgba
	#enddef

	def getImage(self, left, top, width, height):
		img = self.image.crop((left, top, left + width, top + height))
		img.load()
		return img
	#enddef
#endclass

class ColorScan(object):
	"""
	In the future, this will handle scanning for nearest colors.
	At the moment, I don't care.
	"""
	def __init__(self, palette):
		try: obj = palette.iterkeys()
		except AttributeError: obj = enumerate(palette)

		# Convert to HSL and sort
		self.palette = {}
		for k, v in obj: self.palette[Graphic.hex(v)] = k
	#enddef

	def scan(self, color):
		return self.palette[Graphic.hex(color)]
	#enddef
#endclass

################################################################################
############################# Media Parent Structs #############################
################################################################################

class Graphic(rpl.Serializable):
	"""
	Structs that handle images should inherit this.
	Do note that this is for flat images. If something were to handle layers,
	it would currently inherit this as well, but have to add a lot of
	functionality. This, however, should not be used for anything using more
	than two dimensions.
	<all><imp rpl.Serializable.all BR /><graphic>
	<transformations>
	Transformations are handled in the order: rotate -> mirror -> flip
	And this is reversed for exporting. But they are spoken about in regards
	to importing throughout the documentation.
	<rotate>
	rotate: Optional. 90 degree interval to rotate clockwise. 1 = 90, 2 = 180,
	        3 = 270 Other intervals are lossy and will not be supported. If you
	        need them rotated in such a way, do it in your graphics editor.
	        (Default: 0)</rotate>
	<mirror>
	mirror: Optional. Mirror the image horizontally. (Default: false)</mirror>
	<flip>
	flip:   Optional. Flip the image vertically. (Default: false)</flip></transformations>
	<blank>
	blank:  Optional. Background color, ie. what to use in places where graphics
	        aren't specifically drawn. (Default: white)</blank>
	<dimensions>
	dimensions: [width, height] of the canvas to draw on. By default it refers
	            to pixels, but *maps may adjust this to pw = width * multiplier;
	            ph = height * multiplier;</dimensions>
	<offset>
	offset: Optional. [x, y] of where to draw the image on the canvas. These are
	        0-based and are (by default) the pixel locations of the image. *maps
	        may adjust this to be px = x * multiplier; py = y * multiplier;
	        (Default: [0, 0])</offset></graphic></all>
	"""

	def __init__(self, top, name, parent=None):
		rpl.Serializable.__init__(self, top, name, parent)

		self.image = None
		self.importing = False
		# Offset Width/Height Multipliers
		self.owm, self.ohm = 1, 1
		# Width/Height Multipliers
		self.wm, self.hm = 1, 1
		self.palette = None
	#enddef

	def register(self):
		rpl.Serializable.register(self)
		self.registerKey("rotate", "number", "0")
		self.registerKey("mirror", "bool", "false")
		self.registerKey("flip", "bool", "false")
		self.registerKey("blank", "color", "white")
		self.registerKey("dimensions", "[number, number]")
		self.registerKey("offset", "[number, number]", "[0, 0]")
	#enddef

	def dimensions(self):
		try:
			dimens = self["dimensions"].get()
			return dimens[0].get() * self.wm, dimens[1].get() * self.hm
		except RPLError: return self.wm, self.hm
	#enddef

	def importTransform(self):
		if self.image is None: return False
		if self["rotate"].get() != 0:
			self.image = self.image.transpose([
				Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270
			][self["rotate"].get() - 1])
		#endif
		if self["mirror"].get(): self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
		if self["flip"].get(): self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
		return True
	#enddef

	def exportTransform(self):
		if self.image is None: return False
		if self["flip"].get(): self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
		if self["mirror"].get(): self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
		if self["rotate"].get() != 0:
			self.image = self.image.transpose([
				Image.ROTATE_270, Image.ROTATE_180, Image.ROTATE_90
			][self["rotate"].get() - 1])
		#endif
		return True
	#enddef

	def importPrepare(self, rom, folder):
		"""
		More often than not you won't have to overwrite this.
		Just set self.owm, self.ohm, self.wm, and self.hm
		"""
		# Read in image
		self.importing = True
		filename = self.open(folder, "png", True)
		image = self.rpl.share(filename, ImageFile)
		image.read()
		offs = self["offset"].get()
		width, height = self.dimensions()
		self.image = image.getImage(
			offs[0].get() * self.owm, offs[1].get() * self.ohm,
			width, height
		)
		# Do this here because export does it last
		self.importTransform()
	#enddef

	def prepareImage(self):
		"""
		Should override this with reading method.
		"""
		width, height = self.dimensions()
		# Palettes can't have per-color transparency? ;~;
		self.image = Image.new("RGBA", (width, height))
		self.image.paste(self["blank"].get(), (0, 0, width, height))
	#enddef

	def exportData(self, rom, folder):
		"""
		More often than not you won't have to overwrite this.
		Just set self.owm, self.ohm, self.wm, and self.hm
		"""
		if self.image is None: self.prepareImage()
		self.exportTransform()
		offs = self["offset"].get()
		offx, offy = offs[0].get() * self.owm, offs[1].get() * self.ohm
		width, height = self.dimensions()
		filename = self.open(folder, "png", True)
		image = self.rpl.share(filename, ImageFile)
		image.ensureSize(offx + width, offy + height)
		image.addImage(self.image, offx, offy)
	#enddef

	def basic(self):
		"""
		This operates under the assumption that if something wants to edit
		the image itself, it should reference the basic value, which will force
		the class to prepare the image (during exporting).
		"""
		if not self.importing: self.prepareImage()
		return rpl.String(self.name)
	#enddef

	def definePalette(self, palette):
		"""
		palette is an object keyed by palette index with value of the color.
		"""
		self.palette = ColorScan(palette)
	#enddef

	def indexOf(self, color):
		"""
		Return palette index of most similar color.
		color is form: 0xaaRRGGBB
		"""
		return self.palette.scan(color)
	#enddef

	@staticmethod
	def col(color):
		"""
		color can be: (r, g, b), (r, g, b, a), or 0xaaRRGGBB
		"""
		if type(color) is tuple:
			if len(color) == 3: return color + (255,)
			else: return color
		#endif
		return (
			(color & 0x00FF0000) >> 16,
			(color & 0x0000FF00) >> 8,
			(color & 0x000000FF),
			255 - ((color & 0xFF000000) >> 24),
		)
	#enddef

	@staticmethod
	def hex(color):
		if type(color) is tuple:
			if len(color) == 3: r, g, b, a = color + (255,)
			else: r, g, b, a = color
			return (
				(255 - (a & 0xff)) << 24 |
				(r & 0xff) << 16 |
				(g & 0xff) << 8 |
				b & 0xff
			)
		#endif
		return color
	#enddef

	@staticmethod
	def rgb2rgbMmhc(color):
		r, g, b, a = Graphic.col(color)
		r, g, b = r / 255.0, g / 255.0, b / 255.0
		M, m = max(r, g, b), min(r, g, b)
		c = M - m
		if c == 0: h = 0
		elif M == r: h = 60 * ((g - b) / c % 6)
		elif M == g: h = 60 * ((b - r) / c + 2)
		elif M == b: h = 60 * ((r - g) / c + 4)
		return r, g, b, a, M, m, h, c
	#enddef

	@staticmethod
	def rgb2hsl(color):
		r, g, b, a, M, m, h, c = Graphic.rgb2rgbMmhc(color)
		l = (M + m) / 2
		s = 0 if c == 0 else c * 100 / (1 - abs(2 * l - 1))
		return int(h), int(s), int(round(l * 100)), a
	#enddef

	@staticmethod
	def rgb2hsv(color):
		r, g, b, a, M, m, h, c = Graphic.rgb2rgbMmhc(color)
		v = M
		s = 0 if c == 0 else c * 100 / v
		return int(h), int(s), int(round(v * 100)), a
	#enddef
#endclass

class Sound(rpl.Serializable):
	"""
	Structs that handle sound should inherit this.
	"""
	# TODO: Learn about sound.
	pass
#endclass

class Model(rpl.Serializable):
	"""
	Structs that handle 3D models should inherit this.
	"""
	# TODO: Learn about models.
	pass
#endclass

class Markup(rpl.Serializable):
	"""
	Structs that handle formatted text should inherit this.
	"""
	# TODO: Implement this.
	pass
#endclass

class Assembly(rpl.Serializable):
	"""
	Structs that handle bytecode should inherit this.
	"""
	# TODO: Implement this.
	pass
#endclass

################################################################################
#################################### Structs ###################################
################################################################################

class DataFormat(object):
	"""
	The mutual parent for Data and Format
	"""
	def __init__(self, top, name, parent):
		self.parentClass = rpl.Serializable if isinstance(self, rpl.Serializable) else rpl.RPLStruct
		self.parentClass.__init__(self, top, name, parent)
		self.format = odict()
		self.command = {}
		self._len = None
		self.count = None
		self.importing = False
	#enddef

	def register(self):
		# String only uses default data size. Number only uses bin as type
		self.parentClass.register(self)
		self.registerKey("endian", "string:(little, big)", "little")
		self.registerKey("pad", "string", "\x00")
		self.registerKey("padside", "string:(left, right, center, rcenter)", "right")
		self.registerKey("sign", "string:(unsigned, signed)", "unsigned")
		self.registerKey("x", "string|[string|reference, number|string:(expand), string|number]+1", "")
	#enddef

	def parseFormat(self, key):
		fmt = self.format[key]
		if fmt is None: raise RPLError("No format for key %s." % key)
		if type(fmt) is list:
			# Let's parse and cache this
			tmp = {
				"type": fmt[0],
				"size": fmt[1],
				"offset": None,
				"offsetRefs": [],
				"end": False,
			}
			if fmt[1].reference():
				refKey = self.refersToSelf(fmt[1])
				if refKey:
					if DataFormat.isCounted(tmp["type"]): self.command[refKey] = ["count", key]
					else: self.command[refKey] = ["len", key]
				#endif
			#endif
			for x in fmt[2:]:
				refKey = None
				if x.reference():
					refKey = self.refersToSelf(x)
					if refKey and self.importing:
						try: self.get(x)
						except RPLError:
							self.command[refKey] = ["offset", key]
							tmp["offsetRefs"].append(x)
							continue
						#endtry
					#endif
				#endif
				val = x.get()
				if type(val) in [int, long]:
					if refKey: self.command[refKey] = ["offset", key]
					if tmp["offset"] is None: tmp["offset"] = val
					else: tmp["offset"] += val
				# We can assume it's str, otherwise
				elif val in ["little", "le"]: tmp["endian"] = "little"
				elif val in ["big", "be"]: tmp["endian"] = "big"
				elif val in ["signed", "unsigned"]: tmp["sign"] = val
				elif val in ["left", "right", "center", "rcenter"]: tmp["padside"] = val
				elif val in ["end"]: tmp["end"] = True
				elif len(val) == 1: tmp["padchar"] = val
			#endfor
			if "endian" not in tmp: tmp["endian"] = self["endian"].get()
			if "sign" not in tmp: tmp["sign"] = self["sign"].get()
			if "padside" not in tmp: tmp["padside"] = self["padside"].get()
			if "padchar" not in tmp: tmp["padchar"] = self["pad"].get()
			# If an offset wasn't specified, calculate it from the previous
			# offset plus the previous size. (If it scales from the bottom
			# it must be specified!)
			if tmp["offset"] is None:
				first = True
				for k in self.format:
					if k != key: first = False
					break
				#endfor
				if first: tmp["offset"] = 0
			#endif
			fmt = self.format[key] = tmp
		#endif
		return fmt
	#enddef

	def refersToSelf(self, ref):
		# TODO: Should this also be true if the struct name is its own name?
		# TODO: Should this support multikey or indexing?
		struct, keysets = ref.parts()
		return keysets[0][0] if struct == "this" and keysets and keysets[0][0][0] == "x" else None
	#enddef

	def prepOpts(self, opts, size=True):
		tmp = dict(opts)
		#tmp["type"] = self.get(tmp["type"])
		if size: tmp["size"] = self.get(tmp["size"])
		else: del tmp["size"]
		return tmp
	#endif

	@staticmethod
	def setBase(cls, val):
		try: cls["base"] = val
		except RPLError: cls.base = val
	#enddef

	@staticmethod
	def setLen(cls, val):
		try: cls["size"] = val
		except RPLError: cls.size = val
	#enddef

	@staticmethod
	def isCounted(ref, keylessRefOnly=False):
		return ref.reference() and ref.keyless() and (keylessRefOnly or ref.pointer().sizeFieldType != "len")
	#enddef

	def __getitem__(self, key):
		if key in self.data and self.data[key].struct():
			# TODO: Think this through more.
			if self.data[key].sizeFieldType == "len": return self.data[key].basic()
			else: return self.data[key]
		#endif
		try: return self.parentClass.__getitem__(self, key)
		except RPLError:
			if key[0] == "x":
				# If the key doesn't exist yet, we should attempt to retrieve it
				fmt = self.parseFormat(key)
				if self.importing:
					if key in self.command:
						com = self.command[key]
						if com[0] == "len":
							if DataFormat.isCounted(fmt["type"], True):
								# Grab projected size of referenced struct.
								self.data[key] = rpl.Number(fmt["type"].pointer().len())
							else:
								# Grab size of serialized data.
								# TODO: Should this rather be a projected size?
								self.data[key] = rpl.Number(len(
									self[com[1]].serialize(**self.prepOpts(
										self.format[com[1]], size=False
									))
								))
							#endif
						elif com[0] == "count":
							try:
								typeName = self.pointer(self.parseFormat(com[1])["type"])
								self.data[key] = rpl.Number(len(self[com[1]].clones))
							except RPLBadType: raise RPLError("Tried to count basic type.")
						elif com[0] == "offset":
							return None
							#offset = self.format[com[1]]["offset"]
							#if offset is None: return None
							#self.data[key] = rpl.Number(offset)
						return self.data[key]
					#endif
					raise RPLError("Somehow have not read data for %s." % key)
				else:
					offset = self.offsetOf(key)
					address = base = self.get("base") + offset
					self.rpl.rom.seek(address)
					size, expand = self.get(fmt["size"]), False
					if size == "expand":
						expand = True
						keys = self.format.keys()
						size = self.offsetOf(keys[
							keys.index(key) + 1
						]) - offset
						fmt["size"] = rpl.Number(size)
					#endif
					if DataFormat.isCounted(fmt["type"], True):
						#tmp = []
						ref = self.pointer(fmt["type"])
						def tmpfunc(address):
							t = ref.clone()
							DataFormat.setBase(t, rpl.Number(address))
							if t.sizeFieldType == "len": DataFormat.setLen(t, fmt["size"])
							try: t.exportPrepare
							except AttributeError: pass
							else:
								try: t.exportPrepare(self.rpl.rom, [], [self])
								except TypeError: t.exportPrepare(self.rpl.rom, [])
							#endif
							#tmp.append(t)
							return address + t.len(), t
						#enddef

						# Change this to end address to just use end's functionality
						if expand: size += base
						if fmt["end"] or expand:
							count = 0
							while address < size:
								address, _ = tmpfunc(address)
								count += 1
							#endwhile
							if address > size:
								raise RPLError("Couldn't fit %s.%s into the available space perfectly." % (self.name, key))
							#endif
							# Adjust to the actual value..
							fmt["size"] = rpl.Number(count)
							self.data[key] = ref#rpl.List(tmp)
						elif ref.sizeFieldType == "len":
							# Size is length.
							address, self.data[key] = tmpfunc(address)
						else:
							# Size is count.
							for i in helper.range(size): address, _ = tmpfunc(address)
							self.data[key] = ref#rpl.List(tmp)
						#endif
					else:
						typeName = self.get(fmt["type"])
						self.data[key] = self.rpl.wrap(typeName)
						self.data[key].unserialize(
							self.rpl.rom.read(size),
							**self.prepOpts(fmt)
						)
					#endif
					return self.data[key]
				#endif
			else: raise
		#endtry
	#enddef

	def __setitem__(self, key, value):
		# Special handling for keys starting with x
		# Note: What you set here is NOT the data, so it CANNOT be referenced
		if key[0] == "x":
			if key not in self.format:
				self.parentClass.__setitem__(self, "x", value)
				tmp = self.data["x"]
				try: tmp = tmp.string()
				except RPLBadType: self.format[key] = tmp.get()
				else: self.format[key] = map(self.rpl.parseData, tmp.split())
				if DataFormat.isCounted(self.format[key][0], True):
					# If it's a reference, it needs to be set as managed.
					try: self.format[key][0].pointer().unmanaged = False
					# Does not exist yet... will need to be set in preparation.
					except RPLError: pass
				del self.data["x"]
			else:
				typeName = self.parseFormat(key)["type"]
				if not DataFormat.isCounted(typeName, True):
					# Recast... TODO: Should this generate a validatation or
					# is this enough?
					self.data[key] = self.rpl.wrap(self.get(typeName), value.get())
				else: self.data[key] = value
			#endif
		else:
			self.parentClass.__setitem__(self, key, value)
		#endif
	#enddef

	def importPrepare(self, rom, folder, filename=None, data=None, callers=[]):
		self.importing = True
		if filename is None:
			# Should not initially prepare anything if Format type.
			if self.parentClass != rpl.Serializable: return
			filename = self.open(folder, "rpl", True)
		#endif
		if data:
			if self.countExported() == 1: data = [data]
			else: data = data.get()
		else: data = self.rpl.share(filename, DataFile)
		keys = [x for x in self.format]
		for k in keys: self.parseFormat(k)
		for k in keys:
			if k in self.command: continue
			typeName = self.format[k]["type"]
			if type(data) is list:
				try: self[k] = data.pop(0)
				except IndexError:
					raise rpl.RPLError("Not enough data for %s. Cannot set %s." % (
						self.name, k
					))
				#endtry
			else:
				try: self[k] = data.next()
				except StopIteration:
					raise rpl.RPLError("Not enough data for %s. Cannot set %s." % (
						self.name, k
					))
				#endtry
			#endif
			if DataFormat.isCounted(typeName, True):
				typeName = typeName.pointer()
				typeName.unmanaged = False
				if typeName.sizeFieldType == "len":
					t = typeName.clone()
					DataFormat.setLen(t, self.format[k]["size"])
					try: t.importPrepare(rom, folder, filename, self[k], callers + [self])
					except TypeError: t.importPrepare(rom, folder)
					self[k] = t
				else:
					#tmp = []
					for x in self.get(self[k]):
						t = typeName.clone()
						try: t.importPrepare(rom, folder, filename, x, callers + [self])
						except TypeError as err:
							# TODO: Can Python be more precise about what's
							# raising the error than this?
							if err.args[0].find("importPrepare") == -1: raise
							t.importPrepare(rom, folder)
						#tmp.append(t)
					#endfor
					self[k] = typeName#rpl.List(tmp)
				#endif
			#endif
		#endfor
	#enddef

	def exportPrepare(self, rom, folder, callers=[]):
		keys = [x for x in self.format]
		for k in keys:
			# Set all referenced structs to managed.
			typeName = self.parseFormat(k)["type"]
			if DataFormat.isCounted(typeName, True):
				typeName.pointer().unmanaged = False
			#endif
		#endfor
	#enddef

	def importDataLoop(self, rom, folder, base=None, callers=[]):
		"""
		Initially called from Data.importData
		"""
		if base is None: base = self.get("base")

		for k in self.format:
			fmt = self.format[k]
			data = self[k]
			typeName = self.format[k]["type"]
			if k in self.command:
				com = self.command[k]
				# If this was len, it's currently the size of the serialized data.
				# However, if the key it's for is end type, it needs to be adjusted
				# to the ending address instead.
				# TODO: This currently enforces that if one needs to reference
				# something with the end tag, it needs to be done after that
				# data struct, so that that data struct will be imported first.
				# I don't like this, but moving all this to __getitem__ means
				# that the data can't be changed.. There must be a nicer way to
				# get around this but it might take severe redesigning.
				if com[0] in ["len", "count"]:
					fmtc1 = self.format[com[1]]
					if com[0] == "len" and fmtc1["end"]:
						self[k] = data = rpl.Number(data.get() + fmtc1["offset"])
					elif com[0] == "count" and fmtc1["end"]:
						# This was actually a count, not a size..
						size = 0
						for x in self.pointer(com[1]).clones: size += x.len()
						self[k] = data = rpl.Number(size + fmtc1["offset"])
					#endif
				#endif
			#endif
			if DataFormat.isCounted(typeName):
				for x in data.clones:
					try: x.importDataLoop
					# Handle things not specifically meant to be used as data types.
					except AttributeError: x.importData(rom, folder)
					# Handle things that are.
					else: x.importDataLoop(rom, folder, callers=callers + [self])
				#endfor
			elif DataFormat.isCounted(typeName, True):
				x = self.data[k]
				try: x.importDataLoop
				# Handle things not specifically meant to be used as data types.
				except AttributeError: x.importData(rom, folder)
				# Handle things that are.
				else: x.importDataLoop(rom, folder, callers=callers + [self])
			else:
				data = data.serialize(**self.prepOpts(fmt))
				size = self.get(fmt["size"])
				if size != "expand" and len(data) != size:
					raise RPLError("Expected size %i but size %i returned." % (
						size, len(data)
					))
				#endif
				rom.seek(base + fmt["offset"], 0)
				rom.write(data)
			#endif
		#endfor
	#enddef

	def exportDataLoop(self, rom, folder, datafile=None, callers=[]):
		"""
		Initially called from Data.exportData
		Returns RPLData to write to the file
		"""
		ret = []
		# Ensures everything is loaded and tagged with commands, so nothing
		# is accidentally exported.. TODO: Not optimal I don't think?
		for k in self.format: self[k]
		for k in self.format:
			data = self[k]
			typeName = self.format[k]["type"]
			if DataFormat.isCounted(typeName):
				try: data.exportDataLoop
				except IndexError:
					# Empty list.
					data = rpl.List([])
				except AttributeError:
					# Handle things not specifically meant to be used as data types.
					for x in self.list(data): x.exportData(rom, folder)
					data = None
				else:
					# Handle things that are.
					ls = [x.exportDataLoop(rom, folder, callers=callers + [self]) for x in data.clones]
					data = rpl.List(ls)
				#endtry
			elif DataFormat.isCounted(typeName, True):
				# Length as size field.
				x = self.data[k]
				try: x.exportDataLoop
				except AttributeError:
					# Handle things not specifically meant to be used as data types.
					x.exportData(rom, folder)
					data = None
				else:
					# Handle things that are.
					data = x.exportDataLoop(rom, folder, callers=callers + [self])
				#endif
			#endif
			# A command implies this data is inferred from the data that's
			# being exported, so it shouldn't be exported itself.
			if k not in self.command and data is not None:
				if datafile is None: ret.append(data)
				else: datafile.add(data)
			#endif
		#endfor
		if ret:
			if self.countExported() > 1: return rpl.List(ret)
			else: return ret[0]
		#endif
	#enddef

	def calculateOffsets(self):
		base = self["base"].number()
		calcedOffset = 0
		for k in self.format:
			fmt = self.format[k]
			# Get real offset
			offset = calcedOffset
			if fmt["offsetRefs"]:
				# Remove sum of static offsets
				if fmt["offset"] is not None: offset -= fmt["offset"]
				# TODO: Gonna be difficult if not impossible to properly split
				# these in case of multiple refs..
				if len(fmt["offsetRefs"]) > 1:
					raise RPLError("Cannot import fields that use multiple "
						"references for the offset at the moment."
					)
				#endif
				self.set(fmt["offsetRefs"][0], offset)
			elif fmt["offset"] is not None:
				# Absolute offset
				calcedOffset = offset = fmt["offset"]
			#endif
			fmt["offset"] = calcedOffset
			data = self[k]
			typeName = self.format[k]["type"]
			if DataFormat.isCounted(typeName):
				# Size is count.
				tnr = typeName.pointer()
				for x in data.clones:
					try: x.calculateOffsets
					except AttributeError:
						if fmt["end"]:
							# TODO: Next entry should have an offset
							DataFormat.setBase(x, rpl.Number(base + calcedOffset))
							pass
						else:
							# Size is count
							for c in tnr.clones:
								DataFormat.setBase(c, rpl.Number(base + calcedOffset))
								calcedOffset += c.len()
							#endfor
						#endelse
					else:
						DataFormat.setBase(x, rpl.Number(base + calcedOffset))
						calcedOffset += x.calculateOffsets()
					#endif
				#endfor
			elif DataFormat.isCounted(typeName, True):
				# Size is length.
				x = self.data[k]
				DataFormat.setBase(x, rpl.Number(base + calcedOffset))
				calcedOffset += x.len()
			else:
				size = self.get(fmt["size"])
				if size == "expand":
					# TODO: I hate this
					size = len(self[k].serialize(**self.prepOpts(
						fmt, size=False
					)))
					fmt["size"] = rpl.Number(size)
				#endif
				calcedOffset += size
			#endif
		#endfor
		return calcedOffset
	#enddef

	def offsetOf(self, key):
		fmt = self.parseFormat(key)
		if fmt["offset"] is not None: return fmt["offset"]
		keys = self.format.keys()
		idx = keys.index(key)
		if idx == 0: fmt["offset"] = self["base"].number()
		else:
			prevKey = keys[idx - 1]
			prevFmt = self.parseFormat(prevKey)
			if DataFormat.isCounted(prevFmt["type"]):
				size = 0
				for x in self[prevKey].clones: size += x.len()
			else:
				size = self.get(prevFmt["size"])
				if size == "expand":
					# TODO: Try to calc from bottom instead?
					raise RPLError("Offset of key (%s) following a key "
						"with expanding size must be known." % key
					)
				#endif
			#endif
			if prevFmt["end"]: fmt["offset"] = size
			else: fmt["offset"] = self.offsetOf(prevKey) + size
			if fmt["end"]:
				fmt["size"] = rpl.Number(self.get(fmt["size"]) - fmt["offset"])
				fmt["end"] = False
			#endif
			return fmt["offset"]
		#endfor
	#enddef

	def len(self):
		if self._len is not None: return self._len
		size = 0
		for k in self.format:
			fmt = self.parseFormat(k)
			data = self[k]
			if DataFormat.isCounted(self.format[k]["type"]):
				for x in self.get(data): size += x.len()
			else: size += self.get(fmt["size"])
		#endfor
		self._len = size
		return size
	#enddef

	def countExported(self):
		"""
		Returns how many different values are exported
		"""
		if self.count is not None: return self.count
		count = 0

		# Ensure commands are set...
		for k in self.format: self.parseFormat(k)

		for k in self.format:
			if k not in self.command: count += 1
		#endfor
		self.count = count
		return count
	#enddef
#endclass

class Format(DataFormat, rpl.RPLStruct):
	"""
	Represents the format of packed data.
	Same as [data] but does not import or export.
	<imp Data.all />
	"""
	typeName = "format"

	def __init__(self, top, name, parent=None):
		DataFormat.__init__(self, top, name, parent)
		self.base = None
	#enddef

	def basic(self, callers=[]):
		"""
		Returns the name with a prefix, used for referencing this as a type.
		"""
		return rpl.Literal("Format:" + self.name)
	#enddef

	def base(self, value=None, rom=None, offset=0):
		if rom is None: rom = self.rpl.rom
		rom.seek(self.base.get() + offset)
		return rom.tell()
	#enddef

	def __getitem__(self, key):
		if key == "base":
			return self.base
		else: return DataFormat.__getitem__(self, key)
	#enddef

	def __setitem__(self, key, value):
		if key == "base":
			self.base = value
		else: return DataFormat.__setitem__(self, key, value)
	#enddef
#endclass

# TODO: Support txt, bin, json, and csv? exports
# TODO: Export RPLs with statics too instead of being so nameless
class Data(DataFormat, rpl.Serializable):
	"""
	Manages un/structured binary data.
	<all>
	To describe the format, one must add keys prefixed with "x"
	Order is important, of course. The format for a field's description is:
	[type, size, offset?, endian?, sign?, pad char?, pad side?, end?]
	All entries with a ? are optional, and order of them doesn't matter.
	    Type: Datatype by name, for example: string, number
	    Size: Size of the field in bytes
	    Offset: Offset from base to where this entry is. By default this is
	            calculated from the sizes, but there are times it may be
	            necessary to supply it (dynamic sizing in the middle).
	    Endian: Only relevant to numbers, can be "little" or "big"
	    Sign: Only relevant to numbers, can be "signed" or "unsigned"
	    Pad char: Only relevant to strings, it's the char to pad with.
	    Pad side: Only relevant to strings, can be "left", "right", "center",
	              or "rcenter"
	    End: Rather than size, Size is actually the address to stop reading.
	         Use the literal word "end"
	<endian>
	endian:  Default endian, may be "little" or "big". Defaults to "little"</endian>
	<pad>
	pad:     Default padding character, default is "$00"</pad>
	<padside>
	padside: Default padside, may be "left", "right", "center", or "rcenter".
	         Default is "right"</padside>
	<sign>
	sign:    Default sign, may be "signed" or "unsigned". Defaults to "unsigned"</sign>
	<pretty>
	pretty:  Pretty print data, particularly relevant to lists.</pretty>
	<comment>
	comment: Comment to write to the file. Great for when sharing the file.</comment>
	<format>
	format:  Copy the x keys from given format struct *at this point* in the
	         data struct. This is a write-only key.</format></all>
	"""
	typeName = "data"

	def register(self):
		DataFormat.register(self)
		self.registerKey("pretty", "bool", "false")
		#self.registerKey("format", "string", "")
		self.registerKey("comment", "string", "")
	#enddef

	def __setitem__(self, key, data):
		if key == "format":
			if data.reference() and data.keyless(): struct = data.pointer()
			else: struct = self.rpl.structsByName[self.get(data)]
			try: struct.format
			except AttributeError:
				raise RPLError("Attempted to reference non-format type in data.format")
			else:
				# Set to managed.
				struct.unmanaged = False
				for x in struct.format:
					self.format[x] = deepcopy(struct.format[x])
					# Update the references (this relies on the above being list form..
					# that means the format should only be used in format: calls..
					for d in self.format[x]:
						if d.reference(): d.container = self
					#endfor
				#endfor
			#endtry
		else: DataFormat.__setitem__(self, key, data)
	#enddef

	def importData(self, rom, folder):
		self.calculateOffsets()
		self.importDataLoop(rom, folder)
	#enddef

	def exportData(self, rom, folder):
		filename = self.open(folder, "rpl", True)
		datafile = self.rpl.share(filename, DataFile)
		datafile.comment = self["comment"].get()
		self.exportDataLoop(rom, folder, datafile)
	#enddef

#	def prepareForProc(self, cloneName, cloneKey, cloneRef):
#		# This only matters here when exporting, it should already be prepared
#		# when importing.
#		if self.importing: return
#		for k in self.format:
#			dataType = self.get(self.parseFormat(k)["type"])
#			# We only care about the format types
#			if dataType[0:7] != "Format:": continue
#			# If this needs to be prepared, run the get to read in the data
#			if dataType[7:] == cloneName: self[k]
#			# Note we don't break here because it can be referenced multiple times
#		#endfor
#	#enddef
#endclass

def reverseEvery(data, x):
	return "".join(["".join(reversed(data[i:i+x])) for i in helper.range(0, len(data), x)])
#enddef

class GenericGraphic(Graphic):
	"""
	Manage generic graphical content.
	<if all><imp Graphic.all /></if>
	<read>
	read: Read direction. See [readdir].</read>
	<pixel>
	pixel: List of pixel formats, in order. More often than not there will
	       only be one pixel format. It will loop through these when it
	       reaches the end. See [pixel].</pixel>
	<palette>
	palette: 0-based palette. Use i form in palette to index against this.</palette>
	<reverse>
	reverse: Reverse the order of the bytes every X bytes. Example:
	         Data is: 0x01 23 45 67
	         reverse: 2
	         Final data is: 0x23 01 67 45</reverse>
	"""
	typeName = "graphic"

	def __init__(self, top, name, parent=None):
		Graphic.__init__(self, top, name, parent)
		self.image = None
	#enddef

	def register(self):
		Graphic.register(self)
		self.registerKey("read", "readdir", "LRUD")
		self.registerKey("pixel", "[pixel]*")
		self.registerKey("palette", "[color]+", "[]")
		self.registerKey("padding", "[string:(none, row, pixel, column), number]", "[none, 0]")
		self.registerKey("reverse", "math", "0")
	#enddef

	def padfuncDef(self, width, height):
		padmethod, padmod = tuple([x.get() for x in self["padding"].get()])
		if self.rpl.importing:
			if padmethod == "row":
				widthmo = width - 1
				def padfunc(i, prev, leftover, stream):
					if i % width == widthmo:
						tmpmod = (stream.tell() - prev) % padmod
						#print "Skipping %i.%i bytes" % (padmod - tmpmod  if tmpmod else 0, 8 - leftover if leftover else 0)
						return (padmod - tmpmod  if tmpmod else 0, 0)
					#endif
					return (None, leftover)
				#enddef
			elif padmethod == "column":
				heightmo = height - 1
				def padfunc(i, prev, leftover, stream):
					if i % height == heightmo:
						tmpmod = (stream.tell() - prev) % padmod
						return (padmod - tmpmod  if tmpmod else 0, 0)
					return (None, leftover)
				#enddef
			elif padmethod == "pixel":
				def padfunc(i, prev, leftover, stream):
					tmpmod = (stream.tell() - prev) % padmod
					return (padmod - tmpmod  if tmpmod else 0, 0)
				#enddef
			else:
				def padfunc(i, prev, leftover, stream): return (None, leftover)
			#endif
		else:
			if padmethod == "row":
				widthmo = width - 1
				def padfunc(i, prev, leftovers, pos=None, stream=None):
					if i % width == widthmo:
						tmpmod = ((pos or stream.tell()) - prev) % padmod
						leftovers[1] = 0
						return padmod - tmpmod  if tmpmod else 0
					#endif
					return None
				#enddef
			elif padmethod == "column":
				heightmo = height - 1
				def padfunc(i, prev, leftovers, pos=None, stream=None):
					if i % height == heightmo:
						tmpmod = ((pos or stream.tell()) - prev) % padmod
						leftovers[1] = 0
						return padmod - tmpmod if tmpmod else 0
					#endif
					return None
				#enddef
			elif padmethod == "pixel":
				def padfunc(i, prev, leftovers, pos=None, stream=None):
					tmpmod = ((pos or stream.tell()) - prev) % padmod
					leftovers[1] = 0
					return padmod - tmpmod if tmpmod else 0
				#enddef
			else:
				def padfunc(i, prev, leftovers, pos=None, stream=None): return None
			#endif
		#endif
		return padfunc
	#enddef

	def importData(self, rom, folder):
		read = self["read"].get()
		width, height = tuple([x.get() for x in self["dimensions"].get()])

		# Create padding function...
		prev = 0
		padfunc = self.padfuncDef(width, height)

		# Prepare palette
		self.definePalette([x.tuple() for x in self["palette"].get()])

		# Prepare data
		leftover = 0
		data = self.image.load()
		pixels = self["pixel"].get()
		stream = StringIO()
		for idx, x, y in self["read"].rect(width, height):
			leftover = pixels[idx % len(pixels)].write(stream, self, leftover, data[x, y])
			skip, leftover = padfunc(idx, prev, leftover, stream)
			if skip is not None:
				if skip: stream.write("\x00" * skip)
				prev = stream.tell()
			#endif
		#endfor

		# Commit to ROM
		reverse = self["reverse"].get({
			"w": width, "width": width,
			"h": height, "height": height,
		})
		if reverse: rom.write(reverseEvery(stream.getvalue(), reverse))
		else: rom.write(stream.getvalue())
	#enddef

	def prepareImage(self):
		Graphic.prepareImage(self)
		width, height = tuple([x.get() for x in self["dimensions"].get()])
		numPixels = width * height

		# Create padding function...
		prev = 0
		padfunc = self.padfuncDef(width, height)

		# Collect size of data to read
		pixels = self["pixel"].get()
		bytes = self.len(numPixels, padfunc, pixels)

		# Prepare palette
		palette = [x.tuple() for x in self["palette"].get()]

		# Read pixels
		self.rpl.rom.seek(self["base"].number())
		reverse = self["reverse"].get({
			"w": width, "width": width,
			"h": height, "height": height,
		})
		if reverse: stream = StringIO(reverseEvery(self.rpl.rom.read(bytes), reverse))
		else: stream = StringIO(self.rpl.rom.read(bytes))

		leftovers, data, prev = ["", 0], [], 0
		for i in helper.range(numPixels):
			data.append(pixels[i % len(pixels)].read(stream, palette, leftovers))
			tmp = padfunc(i, prev, leftovers, stream=stream)
			if tmp is not None:
				#print "Skipping %i bytes." % tmp
				stream.seek(tmp, 1)
				prev = stream.tell()
			#endif
		#endfor

		# Paste to image
		self.image.putdata(data)

		# Transform resultant image by read.
		# Since this is confusing, here's a full readout:
		# LRUD: Nothing
		# LRDU: FLIP_TOP_BOTTOM
		# RLUD: FLIP_LEFT_RIGHT
		# RLDU: FLIP_TOP_BOTTOM, FLIP_LEFT_RIGHT
		# UDLR: ROTATE_270, FLIP_TOP_BOTTOM
		# UDRL: ROTATE_90
		# DULR: ROTATE_270
		# DURL: ROTATE_90, FLIP_TOP_BOTTOM
		primary, secondary = self["read"].ids()
		# if xxDU
		if secondary == 3: self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
		# if xxLR
		elif secondary == 0: self.image = self.image.transpose(Image.ROTATE_270)
		# if xxRL
		elif secondary == 1: self.image = self.image.transpose(Image.ROTATE_90)
		# if RLxx
		if primary == 1: self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
		# if UDLR or DURL
		elif primary - secondary == 2: self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
	#enddef

	def len(self, numPixels=None, padfunc=None, pixels=None):
		if numPixels is None or padfunc is None:
			width, height = tuple([x.get() for x in self["dimensions"].get()])
			numPixels = width * height
			padfunc = self.padfuncDef(width, height)
		#endif
		prev, bytes, leftovers = 0, 0, ["", 0]
		pixels = pixels or self["pixel"].get()
		# TODO: Make more efficient for repeated rows or uniform pixel size...
		for i in helper.range(numPixels):
			pixel = pixels[i % len(pixels)]
			bytes += pixel.bytes
			leftovers[1] += pixel.extraBits
			if leftovers[1] >= 8:
				bytes += 1
				leftovers[1] -= 8
			#endif
			tmp = padfunc(i, prev, leftovers, bytes)
			if tmp is not None:
				bytes += tmp
				prev = bytes
			#endif
		#endfor
		#bytes = bytes * numPixels + int(ceil(extraBits * numPixels / 8))
		return bytes
	#enddef
#endclass

class Map(rpl.RPLStruct):
	"""
	Translates data. When exporting, it will look for the value in packed and
	output the corresponding value in unpacked. When importing, it does the
	reverse. un/packed keys may either both be lists or both be strings.
	String form is good for translating text between a ROM's custom encoding
	and ASCII or UTF8. Lists can translate numbers or strings. The benefit here
	being that it can translate strings longer than one character. However do
	remember that strings in RPL are UTF8 as it is. But if the custom encoding
	is multibyte, this will help.
	<packed>
	packed:   What the value should look like when packed.</packed>
	<unpacked>
	unpacked: What the value should look like when unpacked.</unpacked>
	<unmapped>
	unmapped: Method to handle data not represented in un/packed. May be:
	          except: Throw an exception.
	          add:    Write it as is.
	          drop:   Ignore it.</unmapped>
	<cast>
	cast:     Type to cast unpacked values to, if more specific than the
	          interpreted type.</cast>
	<string>
	string:   Type to cast unpacked strings to specifically, if strings and
	          numbers are both present.</string>
	<number>
	number:   Type to cast unpacked numbers to specifically, if strings and
	          numbers are both present.</number>
	<width>
	width:    Byte width for packed values. The default is some kind of voodoo.
	          If set to "dynamic" it will allow dynmically sized strings through.
	          If set to "all" then the entire data is used for the mapping.
	          If set to a number, then the data is split at the given interval.</width>
	"""
	typeName = "map"
	sizeFieldType = "len"

	def __init__(self, top, name, parent=None):
		rpl.RPLStruct.__init__(self, top, name, parent)
		self.base, self.size, self.myData = None, None, None
	#enddef

	def register(self):
		self.registerKey("packed", "string|[number|string]+")
		self.registerKey("unpacked", "string|[number|string]+")
		self.registerKey("unmapped", "string:(except, add, addstr, addstring, addnum, addnumber, drop)", "except")
		self.registerKey("cast", "string", "")
		self.registerKey("string", "string", "")
		self.registerKey("number", "string", "")
		self.registerKey("width", "number|string:(dynamic,all)", "")
	#enddef

	def serializePacked(self, options):
		packed = []
		for x in self["packed"].get():
			try: x.serialize
			except AttributeError: packed.append(rpl.String(x).serialize(**options))
			else: packed.append(x.serialize(**options))
		#endfor
		return packed
	#enddef

	def prepare(self, callers):
		# Retrieve mappings and set mode.
		try: packed, unpacked, mode, utype = self["packed"].list(), self["unpacked"].list(), 0, 0
		except rpl.RPLBadType:
			try: unpacked, mode, utype = self["unpacked"].list(), 1, 0
			except rpl.RPLBadType: unpacked, mode, utype = self["unpacked"].string(), 1, 1
		#endtry

		# Determine width.
		width = self["width"].get()
		if width == "": width = "dynamic" if mode else "all"

		# Create un/serialization options.
		options, remaining = {}, ["padside", "padchar", "endian", "sign"]
		for c in callers[::-1]:
			for o in remaining[:]:
				try:
					options[o] = c.get(o)
					remaining.remove(o)
				except RPLError: pass
			#endfor
			if not remaining: break
		#endfor
		if width == "all": options["size"] = self.size.number()
		elif width != "dynamic": options["size"] = width

		# Serialize packed values.
		packed = self.serializePacked(options)

		# If it's dynamic but all are the same size, just force a known width.
		# TODO: Should this only be when defaulting?
		if width == "dynamic":
			tmp = map(len, packed)
			if tmp.count(tmp[0]) == len(packed): width = tmp[0]
		#endif

		# Ensure lengths of packed and unpacked are the same.
		if len(packed) != len(unpacked):
			raise RPLError(
				"Packed (len: %i) and unpacked (len: %i) must be the same length."
				% (len(packed), len(unpacked))
			)
		#endif

		# Available basic types.
		if utype: types = ["string"]
		else:
			types = []
			for x in unpacked:
				try:
					x.number()
					if "number" not in types: types.append("number")
				except RPLBadType:
					if "string" not in types: types.append("string")
				#endtry
				if len(types) == 2: break
			#endfor
		#endif

		# Back these up for speed.
		return (
			options, packed, unpacked, mode, self["cast"].string(),
			self["string"].string(), self["number"].string(), width, types
		)
	#enddef

	def importPrepare(self, rom, folder, filename=None, data=None, callers=[]):
		# This can only be used as a data's type.
		if data is not None: self.myData = data
	#enddef

	def exportPrepare(self, rom, folder, callers=[]):
		# This can only be used as a data's type.
		if not callers: return

		options, packed, unpacked, mode, cast, string, number, width, types = self.prepare(callers)

		# Read data from ROM.
		self.rpl.rom.seek(self.base.number())
		bindata = self.rpl.rom.read(self.size.number())

		def tmpfunc(data, expand):
			# Loop through packed and attempt unserialize to the respective type.
			for i, p in enumerate(packed):
				if expand:
					if len(p) > len(data): continue
					d = data[:len(p)]
				else: d = data
				if p == d:
					# Match found!
					u = unpacked[i]
					try: d, t = u.number(), 0
					except rpl.RPLBadType:
						# String type.
						d, t = u.string(), 1
					except AttributeError:
						# unpacked is a unicode string
						d, t = u, 1
					#endtry

					if expand:
						# Chop off what was actually used from data.
						return d, t, data[len(p):]
					else: return d, t
				#endif
			#endfor

			# If we arrive here, no match was found.
			if expand: raise RPLError("Impossible to continue mapping dynamically sized map on bad match.")
			action = self["unmapped"].get()[0:6] # Hack for normalizing addstr/num.
			stringInterp = self.rpl.wrap("string").unserialize(data, **options).string()
			numberInterp = self.rpl.wrap("number").unserialize(data, **options).number()
			if action == "drop": return None
			elif action == "addstr": d = stringInterp
			elif action == "addnum": d = numberInterp
			elif len(types) == 1:
				# Has to be the only base type interpreted.
				d, t = (stringInterp, 1) if types[0] == "string" else (numberInterp, 0)
			elif mode == 1:
				# Has to be a string
				d, t = stringInterp, 1
			else:
				# Dunno, just print the hex.
				d = u''.join(["%02x" % ord(x) for x in data])
				if action == "add":
					raise RPLError(u"Cannot add unmapped value: %s Try using addstr or addnum instead." % unicode(d))
			#endif

			if action == "except":
				raise RPLError(u"Unmapped value: %s" % unicode(d))
			elif action[0:3] == "add": return d, t
		#enddef

		# Interpret.
		if width == "all": myData, typ = tmpfunc(bindata, False)
		elif width == "dynamic":
			# Read until exhausted. Assumes string map.
			ret = u""
			while bindata:
				tmp, typ, bindata = tmpfunc(bindata, True)
				if tmp is not None: ret += tmp
			#endwhile
			myData = ret
		else:
			# Chunk and map. Assumes string map.
			ret = u""
			for i in helper.range(0, len(bindata), width):
				tmp, typ = tmpfunc(bindata[i:i + width], False)
				if tmp is not None: ret += tmp
			#endfor
			myData = ret
		#endif
		self.myData = self.rpl.wrap((number or cast or "number") if typ == 0 else (string or cast or "string"), myData)
	#enddef

	def importDataLoop(self, rom, folder, base=None, callers=[]):
		options, packed, unpacked, mode, cast, string, number, width, types = self.prepare(callers)

		try: unpacked[0].get
		except AttributeError: unpacked = list(unpacked)
		else: unpacked = [x.get() for x in unpacked]

		def tmpfunc(data):
			try: return packed[unpacked.index(data)]
			except IndexError:
				# No match
				action = self["unmapped"].get()[0:6] # Hack for normalizing addstr/num.
				try: stringInterp = self.rpl.wrap(string or cast or "string", data)
				except RPLBadType: action = "addnum"
				try: numberInterp = self.rpl.wrap(number or cast or "number", data)
				except RPLBadType: action = "addstr"
				if action == "drop": return None
				elif action == "addstr": d = stringInterp
				elif action == "addnum": d = numberInterp
				elif len(types) == 1:
					# Has to be the only base type interpreted.
					d = stringInterp if types[0] == "string" else numberInterp
				elif mode == 1:
					# Has to be a string
					d = stringInterp
				else:
					# Dunno, just print the hex.
					d = u''.join(["%02x" % ord(x) for x in data])
					if action == "add":
						raise RPLError(u"Cannot add unmapped value: %s Try using addstr or addnum instead." % unicode(d))
					#endif
				#endif

				if action == "except":
					raise RPLError(u"Unmapped value: %s" % unicode(d))
				elif action[0:3] == "add": return d.serialize(**options)
			#endtry
		#enddef

		# Interpret.
		self.rpl.rom.seek(self.base.number())
		if width == "all":
			tmp = tmpfunc(self.myData.get())
			if tmp is not None: self.rpl.rom.write(tmp)
		else:
			# Writes until exhausted. Assumes string map.
			ret = r""
			for x in self.myData.string():
				tmp = tmpfunc(x)
				if tmp is not None: ret += tmp
			#endwhile
			self.rpl.rom.write(ret)
		#endif
	#endif

	def exportDataLoop(self, rom, folder, datafile=None, callers=[]):
		return self.myData
	#enddef

	def basic(self):
		# DataFormat.__getitem__ export branch calls this.
		return self.myData
	#enddef

	def len(self):
		return self.size.number()
	#enddef
#endclass

# Input/Output [dependent] Static
class IOStatic(rpl.Static):
	"""
	Returned data from a key depends on whether we're importing or exporting.
	Format is key: [import, export]
	"""
	typeName = "iostatic"

	def __getitem__(self, key):
		return rpl.Static.__getitem__(self, key)[0 if self.rpl.importing else 1]
	#enddef

	def __setitem__(self, key, value):
		if key not in self.data:
			# Initial set
			try:
				if len(value.list()) != 2: raise RPLBadType()
			except RPLBadType:
				raise RPLError("IOStatic requires each entry to be a list of two values.")
			#endtry
			# This is supposed to be a static! So it should be fine to .get() here.
			self.data[key] = value.list()
		else:
			# When references set it
			self.data[key][0 if self.rpl.importing else 1] = value
		#endif
	#enddef
#endclass

################################################################################
##################################### Types ####################################
################################################################################
class Bin(rpl.String):
	"""
	Manages binary data.
	Prints data in a fancy, hex editor-like way.
	"""
	typeName = "bin"

	def set(self, data):
		rpl.String.set(self, data)
		data = re.sub(r'\s', "", self.data)
		self.data = ""
		for i in helper.range(0, len(data), 2):
			self.data += chr(int(data[i:i+2], 16))
		#endfor
	#endif

	def __unicode__(self):
		tmp = self.data
		ret = u""
		lastComment = ""
		while tmp:
			l1, l2 = tmp[0:8], tmp[8:16]
			b1, b2 = Bin.line2esc(l1), Bin.line2esc(l2)[0:-1]
			ret += lastComment
			if l2:
				ret += "`%s %s`" % (b1, b2)
				pad = 23 - len(b2)
			else:
				ret += "`%s`" % b1[0:-1]
				pad = 49 - len(b1)
			#endif
			lastComment = "%s # %s" % (
				" " * pad,
				rpl.String.binchr.sub(".", l1),
			)
			if l2: lastComment += " " + rpl.String.binchr.sub(".", l2) + os.linesep
			tmp = tmp[16:]
		#endwhile
		return ret + "," + lastComment[1:]
	#enddef

	def serialize(self, **kwargs): return self.data
	def unserialize(self, data, **kwargs): self.data = data

	@staticmethod
	def line2esc(ln):
		ret = u""
		for x in ln: ret += u"%02x " % ord(x)
		return ret
	#enddef
#endclass

#PIXEL = 0
class Pixel(rpl.String):
	typeName = "pixel"

	specification = re.compile(r'(\d+)([bBxX])([rgbRGBhslHSLwWaAi0]+)')

	def set(self, data, bigEndian=True):
		"""
		Format: type desc
		type:
		  0x or x for hexadecimal, #x for number of nibbles
		  0b or b for binary, #b for number of bits
		desc: [rgbRGBhslHSLwWaAi0]+
		Each entry in desc represents the number of bits given by type.
		Full data is read, same bits are masked and concatenated then interpreted
		by the given endian.
		Lower case letters are the inverse of the uppercase versions. ie. R is
		reddest at 1 and r is reddest at 0. The special case being i.
		Meanings:
		 * Red
		 * Green
		 * Blue
		 * Hue
		 * Saturation
		 * Lightness
		 * White
		 * Alpha
		 * Index in a palette
		 * 0 is ignored
		"""
		self.source = data
		self.bigEndian = bigEndian

		tokens = Pixel.specification.match(data)
		if not tokens: raise RPLError("Invalid pixel format.")
		self.type = tokens.group(2)
		self.bits = (lambda(x): (1 if tokens.group(2) in "bB" else 4)*x)(
			max(int(tokens.group(1)), 1)
		)
		self.format = tokens.group(3)

		# Read this many bytes from the stream
		self.bytes = int(len(self.format) * self.bits / 8)
		self.extraBits = len(self.format) * self.bits % 8

		# Does a pixel fit perfectly within the certain number of bytes
		#self.even = (len(self.format) * self.bits) & 0x7 == 0

		# Expand the format
		self.expanded = ""
		for x in self.format: self.expanded += x * self.bits

		# Which "group" this is using (RGBA?, HSLA?, WA?, I)
		rgb = helper.oneOfIn("rRgGbB", self.format)
		hsl = helper.oneOfIn("hHsSlL", self.format)
		ww = helper.oneOfIn("wW", self.format)
		index = "i" in self.format
		if int(rgb) + int(hsl) + int(ww) + int(index) > 1:
			raise RPLError("Invalid pixel format, must only use one group.")
		#endif
		if rgb:   self.group = 0
		if hsl:   self.group = 1
		if ww:    self.group = 2
		if index: self.group = 3
		self.alpha = helper.oneOfIn("aA", self.format)

		self.max = {}
		for x in "RGBHSLWAI":
			self.max[x] = (1 << (self.expanded.count(x.lower()) + self.expanded.count(x))) - 1
		#endif
	#enddef

	def __unicode__(self):
		return (
			u"%ix" % (self.bits >> 2)
			if self.type in "xX" else
			u"%ib" % self.bits
		) + self.format
	#enddef

	def write(self, stream, palette, leftovers, pixel):
		"""
		leftovers: number of bits
		"""
		#global PIXEL
		r, g, b, a = pixel
		val  = {
			"R": int(round(r * self.max["R"] / 255)) if self.max["R"] else 0,
			"G": int(round(g * self.max["G"] / 255)) if self.max["G"] else 0,
			"B": int(round(b * self.max["B"] / 255)) if self.max["B"] else 0,
			# TODO: Calc HSL values
			# Silently ensure a grayscale value
			"W": int(round((r + b + g) / 3 * 255 / self.max["W"])) if self.max["W"] else 0,
			"A": int(round(a * 255 / self.max["A"])) if self.max["A"] else 0,
		}
		if self.max["I"]:
			try: val["I"] = palette.indexOf((r, g, b, a))
			except KeyError:
				try: val["I"] = palette.indexOf((r, g, b, 0xff))
				except KeyError:
					# TODO: Search for most similar color
					raise RPLError("No entry in palette for #%02x%02x%02x.%i%%." % (r, g, b, a * 100 / 255))
				#endtry
			#endtry
		else: val["I"] = 0

		mask = {}
		for k, x in self.max.iteritems(): mask[k] = (x + 1) >> 1
		bytes, bits = [0], 8 - (leftovers + 1)
		for x in self.expanded[::-1]:
			if bits == -1:
				bytes.insert(0, 0)
				bits = 7
			#endif
			if x != "0":
				u = x.upper()
				bit = 1 if val[u] & mask[u] else 0
				if x in "rgbhslwa": bit ^= 1
				bytes[0] |= bit << bits
			#endif
			bits -= 1
			mask[u] >>= 1
		#endfor
		if bits == -1: bits = 0
		else: bits = 8 - (bits + 1)

		#print "Pixel [%i,%i] starting from $%06x.%i" % (PIXEL % 71, int(PIXEL / 71), stream.tell() - (1 if leftovers else 0), leftovers),
		#PIXEL += 1
		if leftovers:
			stream.seek(-1, 1)
			lastChar = ord(stream.read(1))
			stream.seek(-1, 1)
			bytes[0] |= lastChar
		#endif
		bytes = "".join(map(chr, bytes))
		stream.write(bytes)
		#print "Writing %i.%i bytes. #%02x%02x%02x.%i%% Data: %s" % (len(bytes) - (1 if bits or leftovers else 0), bits + (8 - leftovers if leftovers else 0), r, g, b, a * 100 / 255, "".join(["%02x" % ord(c) for c in bytes]))

		return bits
	#enddef

	def read(self, stream, palette, leftovers):
		"""
		leftovers: (data, number of bits)
		"""
		global PIXEL
		values = {
			"R": 0,
			"G": 0,
			"B": 0,
			"H": 0,
			"S": 0,
			"L": 0,
			"W": 0,
			"A": 0,
			"I": 0,
		}

		#print "Pixel [%i,%i] starting from $%06x.%i" % (PIXEL % 71, int(PIXEL / 71), stream.tell(), leftovers[1]),
		#PIXEL += 1
		if leftovers[1]:
			bytes = leftovers[0] + stream.read(self.bytes + (1 if leftovers[1] < self.extraBits else 0))
			byte = 0
			mask = 1 << (leftovers[1] - 1)
		else:
			bytes = stream.read(self.bytes + (1 if self.extraBits else 0))
			byte = 0
			mask = 0x80
		#endif

		curbyte = ord(bytes[byte])
		for x in self.expanded:
			if x != "0":
				bit = 1 if curbyte & mask else 0
				if x in "rgbhslwa": bit ^= 1
				x = x.upper()
				values[x] = values[x] << 1 | bit
			#endif
			mask >>= 1
			if mask == 0:
				byte += 1
				mask = 0x80
				try: curbyte = ord(bytes[byte])
				except IndexError: curbyte = None
			#endif
		#endfor

		if mask == 0x80: leftovers[0], leftovers[1] = "", 0
		else:
			leftovers[0], leftovers[1] = bytes[byte], {
				         0x40: 7, 0x20: 6, 0x10: 5,
				0x08: 4, 0x04: 3, 0x02: 2, 0x01: 1,
			}[mask]
		#endif

		# Make them relative to max values
		for x in "RGBHSLWA":
			if self.max[x]: values[x] = int(round(values[x] * 255 / self.max[x]))
		#endfor

		a = 0xff
		if self.group == 0: r, g, b = values["R"], values["G"], values["B"]
		#elif self.group == 1: TODO
		elif self.group == 2: r, g, b = values["W"], values["W"], values["W"]
		elif self.group == 3: r, g, b, a = palette[values["I"]]
		if self.alpha: a = values["A"]

		#print "#%02x%02x%02x.%i%%" % (r, g, b, a * 100 / 255)
		return (r, g, b, a)
	#enddef
#endclass

class Color(rpl.Named, rpl.HexNum, rpl.Literal, rpl.List):
	typeName = "color"

	names = {
		"black":       0x00000000,
		"white":       0x00ffffff,
		"red":         0x00ff0000,
		"blue":        0x0000ff00,
		"green":       0x000000ff,
		"yellow":      0x00ffff00,
		"magenta":     0x00ff00ff,
		"pink":        0x00ff00ff,
		"cyan":        0x0000ffff,
		"gray":        0x00a5a5a5,
		"grey":        0x00a5a5a5,
		"transparent": 0xff000000,
	}

	def set(self, data):
		if type(data) in [int, long]:
			if data & ~0xffffffff: raise RPLError("Colors must be 3-4 byte values.")
			else: self.data = data
		elif type(data) in [list, tuple]:
			self.data = (
				(data[0] & 0xff) << 16 |
				(data[1] & 0xff) << 8 |
				(data[2] & 0xff)
			)
			if len(data) == 4: self.data |= (255 - (data[3] & 0xff)) << 24
		else: rpl.Named.set(self, data, ["int", "long"])
	#enddef

	def __unicode__(self):
		return rpl.Named.__unicode__(self, "$%06x")
	#enddef

	def tuple(self):
		return (
			(self.data & 0x00ff0000) >> 16,
			(self.data & 0x0000ff00) >> 8,
			(self.data & 0x000000ff),
			255 - ((self.data & 0xff000000) >> 24),
		)
	#enddef
#endclass

class ReadDir(rpl.Literal):
	"""
	This can be almost any combination of L, R, U, and D.
	LRUD is the general reading direction: Start in upper left and read to the
	right until width, then go down a row. This is how many languages, including
	English, are read.
	RLUD is how Hebrew and Arabic are read.
	UDRL is how traditional Japanese is read.
	LRDU is how bitmap pixels are read.
	Other valid combinations: RLDU, UDLR, DULR, DURL
	One can shorten these to the first and third letters, eg. LU.
	"""
	typeName = "readdir"

	valid = [
		"LRUD", "LRDU", "RLUD", "RLDU", "UDLR", "UDRL", "DULR",
		"DURL", "LU", "LD", "RU", "RD", "UL", "UR", "DL", "DR"
	]

	def set(self, data):
		rpl.Literal.set(self, data)
		if self.data in ReadDir.valid:
			self.primary, self.secondary = (
				"LRUD".index(self.data[0]),
				"LRUD".index(self.data[1 if len(self.data) == 2 else 2])
			)
		else:
			raise RPLError("Reading direction must be one of: %s." %
				helper.list2english(ReadDir.valid, "or")
			)
		#endif
	#endif

	def ids(self): return self.primary, self.secondary

	def rect(self, width, height):
		self.index, self.width, self.height = 0, width, height
		# Inner is Vertical, Inner Range, Outer Range
		self.iv = False
		if   self.primary == 0: self.ir = helper.range(self.width,)
		elif self.primary == 1: self.ir = helper.range(self.width - 1, -1, -1)
		elif self.primary == 2: self.iv, self.ir = True, helper.range(self.height,)
		elif self.primary == 3: self.iv, self.ir = True, helper.range(self.height - 1, -1, -1)
		if   self.secondary == 0: self.ori = iter(helper.range(self.width,))
		elif self.secondary == 1: self.ori = iter(helper.range(self.width - 1, -1, -1))
		elif self.secondary == 2: self.ori = iter(helper.range(self.height,))
		elif self.secondary == 3: self.ori = iter(helper.range(self.height - 1, -1, -1))
		if self.iv: self.x = self.ori.next()
		else: self.y = self.ori.next()
		self.iri = iter(self.ir)
		return self
	#enddef

	def __iter__(self): return self

	def next(self):
		try: ii = self.iri.next()
		except StopIteration:
			# Let this raise stop iteration when it's done
			if self.iv: self.x = self.ori.next()
			else: self.y = self.ori.next()
			self.iri = iter(self.ir)
			return self.next()
		else:
			if self.iv: i, x, y = self.index, self.x, ii
			else: i, x, y = self.index, ii, self.y
			self.index += 1
			return i, x, y
		#endif
	#enddef
#endclass

class Math(rpl.Literal, rpl.Number):
	"""
	Handles mathematics.
	TODO: Currently does not handle Order of Operations or parenthesis.
	Available operators: + - * / ^ %
	Division is integer. ^ is power of.
	Variables may be passed, see respective key for details.
	"""
	typeName = "math"

	specification = re.compile(r'([+\-*/^%()])')

	def set(self, data):
		if type(data) in [int, long]: data = str(data)
		rpl.Literal.set(self, data)
		self.tokens = Math.specification.split(self.data.replace(" ", ""))
	#enddef

	def get(self, var={}):
		# Simple math for now...
		# TODO: Currently does not handle OoO or parens
		num, pos, nextop = None, True, None
		for i, x in enumerate(self.tokens):
			try: xn = int(x)
			except:
				if x in var: xn = var[x]
				else: xn = None
			#endif

			if x == "+":
				if num is None: pos = True
				else: nextop = "+"
			elif x == "-":
				if num is None: pos = False
				else: nextop = "-"
			elif xn is not None:
				if num is None: num = xn
				elif nextop is None:
					raise RPLError("Two sequential numbers with no operator.")
				elif nextop == "+": num += xn
				elif nextop == "-": num -= xn
				elif nextop == "*": num *= xn
				elif nextop == "/": num /= xn
				elif nextop == "^": num **= xn
				elif nextop == "%": num %= xn
				nextop = None
			elif x in "*/^%":
				if num is None:
					raise RPLError("Cannot have %s as first operation in a group." % x)
				else: nextop = x
			else: raise RPLError("Unknown variable or operator.")
		#endfor

		return num
	#enddef
#endclass
