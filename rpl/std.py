import os
import re
import Image
import helper
import rpl as RPL
from rpl import RPLError
from copy import deepcopy
from math import ceil
from textwrap import dedent
from StringIO import StringIO
from collections import OrderedDict as odict

#
# Copyright (C) 2012 Sapphire Becker (http://logicplace.com)
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
#endclass

def printHelp(more_info=[]):
	print(
		"std is the standard library for RPL.\n"
		"It offers the structs:\n"
		"  data  format  map  iostatic\n\n"
		"And the types:\n"
		"  bin\n"
	)
	if not more_info: print "Use --help std [structs...] for more info"
	infos = {
		"data": Data, "format": Format,
		"map": Map, "iostatic": IOStatic,
		"bin": Bin,
	}
	for x in more_info:
		if x in infos: print dedent(infos[x].__doc__)
	#endfor
#enddef

class DataFile(RPL.Share):
	"""
	.rpl export for data structs.
	"""
	def __init__(self, inFile=None):
		self._base = []
		self.comment = ""
		if inFile is not None: self.read(inFile)
	#enddef

	def read(self):
		"""
		Read from .rpl data file.
		"""
		rpl = self._rpl
		raw = helper.readFrom(self._path)

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

		self._base = base
	#enddef

	def write(self):
		"""
		Write data to a given file.
		"""
		# TODO: Prettyprinting
		comment = "# " + self.comment if self.comment else ""
		helper.writeTo(self._path, comment + os.linesep.join(map(unicode, self._base)))
	#enddef

	def add(self, item):
		"""
		Add item to data. Must be RPLData type.
		"""
		if not isinstance(item, RPL.RPLData):
			raise RPLError("Tried to add non-data to rpl data file.")
		#endif
		self._base.append(item)
	#enddef

	def __getitem__(self, key): return self._base[key]
	def __len__(self): return len(self._base)

	def __iter__(self):
		try: self._iter
		except AttributeError: self._iter = -1
		return self
	#enddef

	# Atypical implementation of next I think, but it makes the code look nicer.
	def next(self):
		try: self._iter += 1
		except AttributeError: self._iter = 0
		try: return self[self._iter]
		except IndexError: raise StopIteration
	#enddef
#endclass

class ImageFile(RPL.Share):
	def __init__(self, width=0, height=0):
		self._dimensions = (width, height)
		self._image = None
		self._pixels = None
	#enddef

	def read(self):
		if self._image is None: self._image = Image.open(self._path).convert("RGBA")
	#enddef

	def write(self):
		if self._image is None: return # Maybe throw an exception?
		ext = os.path.splitext(self._path)[1][1:].lower()
		# Cannot save alpha..
		if ext == "bmp": self._image = self._image.convert("RGB")
		self._image.save(self._path)
	#enddef

	def newImage(self, width=1, height=1, blank=0xffffff):
		self._image = Image.new("RGBA", (width, height))
		self._image.paste(blank, (0, 0, width, height))
		self._pixels = self._image.load()
	#endif

	def ensureSize(self, width, height):
		# Only necessary when writing, remember!
		if self._image is None: return self.newImage(width, height)
		curWidth, curHeight = self._image.size
		if curWidth < width or curHeight < height:
			width = max(curWidth, width)
			height = max(curHeight, height)
			region = self._image.crop((0, 0, width, height))
			region.load()
			self._image = self._image.resize((width, height))
			self._image.paste(0xffffff, (0, 0, width, height))
			self._image.paste(region, (0, 0))
		#endif
	#enddef

	def addRect(self, data, left, top, width, height):
		if self._image is None: self.newImage()
		region = Image.new("RGBA", (width, height))
		region.putdata(data)
		self._image.paste(region, (left, top))
	#enddef

	def addImage(self, image, left, top):
		if self._image is None: self.newImage()
		self._image.paste(image, (left, top))
	#enddef

	def addPixel(self, rgba, x, y):
		if self._image is None: self.newImage()
		self._pixels[x, y] = rgba
	#enddef

	def getImage(self, left, top, width, height):
		img = self._image.crop((left, top, left + width, top + height))
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
		self._palette = {}
		for k, v in obj: self._palette[Graphic.hex(v)] = k
	#enddef

	def scan(self, color):
		return self._palette[Graphic.hex(color)]
	#enddef
#endclass

################################################################################
############################# Media Parent Structs #############################
################################################################################

class Graphic(RPL.Serializable):
	"""
	Structs that handle images should inherit this.
	Do note that this is for flat images. If something were to handle layers,
	it would currently inherit this as well, but have to add a lot of
	functionality. This, however, should not be used for anything using more
	than two dimensions.
	Transformations are handled in the order: rotate -> mirror -> flip
	And this is reversed for exporting. But they are spoken about in regards
	to importing throughout the documentation.
	rotate: 90 degree interval to rotate clockwise. 1 = 90, 2 = 180, 3 = 270
	        Other intervals are lossy and will not be supported. If you need
	        them rotated in such a way, do it in your graphics editor.
	mirror: Mirror the image horizontally.
	flip:   Flip the image vertically.
	blank:  Background color, ie. what to use in places where graphics aren't
	        specifically drawn.
	dimensions: [width, height] of the canvas to draw on. By default it refers
	            to pixels, but *maps may adjust this to pw = width * multiplier;
	            ph = height * multiplier;
	offset: [x, y] of where to draw the image on the canvas. These are 0-based
	        and are (by default) the pixel locations of the image. *maps may
	        adjust this to be px = x * multiplier; py = y * multiplier;
	"""

	def __init__(self, rpl, name, parent=None):
		RPL.Serializable.__init__(self, rpl, name, parent)
		self.registerKey("rotate", "number", "0")
		self.registerKey("mirror", "bool", "false")
		self.registerKey("flip", "bool", "false")
		self.registerKey("blank", "color", "white")
		self.registerKey("dimensions", "[number, number]")
		self.registerKey("offset", "[number, number]", "[0, 0]")

		self._image = None
		self.importing = False
		# Offset Width/Height Multipliers
		self._owm, self._ohm = 1, 1
		# Width/Height Multipliers
		self._wm, self._hm = 1, 1
		self._palette = None
	#enddef

	def dimensions(self):
		try:
			dimens = self["dimensions"].get()
			return dimens[0].get() * self._wm, dimens[1].get() * self._hm
		except RPLError: return self._wm, self._hm
	#enddef

	def importTransform(self):
		if self._image is None: return False
		if self["rotate"].get() != 0:
			self._image = self._image.transpose([
				Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270
			][self["rotate"].get() - 1])
		#endif
		if self["mirror"].get(): self._image = self._image.transpose(Image.FLIP_LEFT_RIGHT)
		if self["flip"].get(): self._image = self._image.transpose(Image.FLIP_TOP_BOTTOM)
		return True
	#enddef

	def exportTransform(self):
		if self._image is None: return False
		if self["flip"].get(): self._image = self._image.transpose(Image.FLIP_TOP_BOTTOM)
		if self["mirror"].get(): self._image = self._image.transpose(Image.FLIP_LEFT_RIGHT)
		if self["rotate"].get() != 0:
			self._image = self._image.transpose([
				Image.ROTATE_270, Image.ROTATE_180, Image.ROTATE_90
			][self["rotate"].get() - 1])
		#endif
		return True
	#enddef

	def importPrepare(self, rom, folder):
		"""
		More often than not you won't have to overwrite this.
		Just set self._owm, self._ohm, self._wm, and self._hm
		"""
		# Read in image
		self.importing = True
		filename = self.open(folder, "png", True)
		image = self._rpl.share(filename, ImageFile)
		image.read()
		offs = self["offset"].get()
		width, height = self.dimensions()
		self._image = image.getImage(
			offs[0].get() * self._owm, offs[1].get() * self._ohm,
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
		self._image = Image.new("RGBA", (width, height))
		self._image.paste(self["blank"].get(), (0, 0, width, height))
	#enddef

	def exportData(self, rom, folder):
		"""
		More often than not you won't have to overwrite this.
		Just set self._owm, self._ohm, self._wm, and self._hm
		"""
		if self._image is None: self.prepareImage()
		self.exportTransform()
		offs = self["offset"].get()
		offx, offy = offs[0].get() * self._owm, offs[1].get() * self._ohm
		width, height = self.dimensions()
		filename = self.open(folder, "png", True)
		image = self._rpl.share(filename, ImageFile)
		image.ensureSize(offx + width, offy + height)
		image.addImage(self._image, offx, offy)
	#enddef

	def basic(self):
		"""
		This operates under the assumption that if something wants to edit
		the image itself, it should reference the basic value, which will force
		the class to prepare the image (during exporting).
		"""
		if not self.importing: self.prepareImage()
		return RPL.String(self._name)
	#enddef

	def definePalette(self, palette):
		"""
		palette is an object keyed by palette index with value of the color.
		"""
		self._palette = ColorScan(palette)
	#enddef

	def indexOf(self, color):
		"""
		Return palette index of most similar color.
		color is form: 0xaaRRGGBB
		"""
		return self._palette.scan(color)
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

class Sound(RPL.Serializable):
	"""
	Structs that handle sound should inherit this.
	"""
	# TODO: Learn about sound.
	pass
#endclass

################################################################################
#################################### Structs ###################################
################################################################################

class DataFormat(object):
	"""
	The mutual parent for Data and Format
	"""
	def __init__(self):
		# String only uses default data size. Number only uses bin as type
		self.registerKey("endian", "string:(little, big)", "little")
		self.registerKey("pad", "string", "\x00")
		self.registerKey("padside", "string:(left, right, center, rcenter)", "right")
		self.registerKey("sign", "string:(unsigned, signed)", "unsigned")
		self.registerKey("x", "string|[string, number|string:(expand), string|number]+1", "")

		self._parentClass = RPL.Cloneable if isinstance(self, RPL.Cloneable) else RPL.Serializable
		self._format = odict()
		self._command = {}
		self._len = None
		self._count = None
		self.importing = False
	#enddef

	def _parseFormat(self, key):
		fmt = self._format[key]
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
			if isinstance(fmt[1], RPL.RPLRef):
				refKey = self.refersToSelf(fmt[1])
				if refKey:
					if ":" in self.get(tmp["type"]):
						self._command[refKey] = ["count", key]
					else: self._command[refKey] = ["len", key]
				#endif
			#endif
			for x in fmt[2:]:
				refKey = None
				if isinstance(x, RPL.RPLRef):
					refKey = self.refersToSelf(x)
					if refKey and self.importing:
						try: self.get(x)
						except RPLError:
							self._command[refKey] = ["offset", key]
							tmp["offsetRefs"].append(x)
							continue
						#endtry
					#endif
				#endif
				val = x.get()
				if type(val) in [int, long]:
					if refKey: self._command[refKey] = ["offset", key]
					if tmp["offset"] is None: tmp["offset"] = val
					else: tmp["offset"] += val
				# We can assume it's str, otherwise
				elif val in ["little", "le"]: tmp["endian"] = "little"
				elif val in ["big", "be"]: tmp["endian"] = "big"
				elif val in ["signed", "unsigned"]: tmp["sign"] = val
				elif val in ["left", "right", "center", "rcenter"]: tmp["padside"] = val
				elif val in ["end"]: tmp["end"] = True
				#elif val.find(":") != -1:
				#	pos = val.find(":")
				#	tmp["command"] = [val[0:pos], val[pos+1:]]
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
				for k in self._format:
					if k != key: first = False
					break
				#endfor
				if first: tmp["offset"] = 0
			#endif
			fmt = self._format[key] = tmp
		#endif
		return fmt
	#enddef

	def refersToSelf(self, ref):
		# TODO: Should this also be true if the struct name is its own name?
		struct, key, idxs = ref.parts()
		return key if struct == "this" and key[0] == "x" else None
	#enddef

	def prepOpts(self, opts, size=True):
		tmp = dict(opts)
		tmp["type"] = self.get(tmp["type"])
		if size: tmp["size"] = self.get(tmp["size"])
		else: del tmp["size"]
		return tmp
	#endif

	def __getitem__(self, key):
		try: return self._parentClass.__getitem__(self, key)
		except RPLError:
			if key[0] == "x":
				# If the key doesn't exist yet, we should attempt to retrieve it
				fmt = self._parseFormat(key)
				if self.importing:
					if key in self._command:
						com = self._command[key]
						if com[0] == "len":
							# TODO: Grab size of serialized data for Format types
							self._data[key] = RPL.Number(len(
								self[com[1]].serialize(**self.prepOpts(
									self._format[com[1]], size=False
								))
							))
						elif com[0] == "count":
							typeName = self.get(self._parseFormat(com[1])["type"])
							if ":" in typeName:
								self._data[key] = RPL.Number(len(self.get(self[com[1]])))
							else: raise RPLError("Tried to count non-Format type.")
						elif com[0] == "offset":
							return None
							#offset = self._format[com[1]]["offset"]
							#if offset is None: return None
							#self._data[key] = RPL.Number(offset)
						#endif
						return self._data[key]
					#endif
					raise RPLError("Somehow have not read data for %s." % key)
				else:
					offset = self.offsetOf(key)
					address = base = self.base(offset=offset)
					typeName = self.get(fmt["type"])
					size, expand = self.get(fmt["size"]), False
					if size == "expand":
						expand = True
						keys = self._format.keys()
						size = self.offsetOf(keys[
							keys.index(key) + 1
						]) - offset
						fmt["size"] = RPL.Number(size)
					#endif
					if ":" in typeName:
						tmp = []
						ref = self._rpl.structsByName[typeName[typeName.index(":") + 1:]]
						def tmpfunc(address):
							t = ref.clone()
							t._base = RPL.Number(address)
							if hasattr(t, "exportPrepare"): t.exportPrepare(self._rpl.rom, [])
							tmp.append(t)
							return address + t.len()
						#enddef
						if expand: size += base # Change this to end address to just use end's functionality
						if fmt["end"] or expand:
							count = 0
							while address < size:
								address = tmpfunc(address)
								count += 1
							#endwhile
							if address > size:
								raise RPLError("Couldn't fit %s.%s into the available space perfectly." % (self._name, key))
							#endif
							# Adjust to the actual value..
							fmt["size"] = RPL.Number(count)
						else:
							# Size is count
							for i in helper.range(size): address = tmpfunc(address)
						#endif
						self._data[key] = RPL.List(tmp)
					else:
						self._data[key] = self._rpl.wrap(typeName)
						self._data[key].unserialize(
							self._rpl.rom.read(size),
							**self.prepOpts(fmt)
						)
					#endif
					return self._data[key]
				#endif
			else: raise
		#endtry
	#enddef

	def __setitem__(self, key, value):
		# Special handling for keys starting with x
		# Note: What you set here is NOT the data, so it CANNOT be referenced
		if key[0] == "x":
			if key not in self._format:
				self._parentClass.__setitem__(self, "x", value)
				tmp = self._data["x"]
				if isinstance(tmp, RPL.String):
					self._format[key] = map(self._rpl.parseData, tmp.get().split())
				else: self._format[key] = tmp.get()
				del self._data["x"]
			else:
				typeName = self.get(self._parseFormat(key)["type"])
				if ":" not in typeName:
					# Recast... TODO: Should this generate a validatation or
					# is this enough?
					self._data[key] = self._rpl.wrap(typeName, value.get())
				else: self._data[key] = value
		else:
			self._parentClass.__setitem__(self, key, value)
		#endif
	#enddef

	def importPrepare(self, rom, folder, filename=None, data=None):
		self.importing = True
		filename = filename or self.open(folder, "rpl", True)
		data = data or self._rpl.share(filename, DataFile)
		keys = [x for x in self._format]
		for k in keys: self._parseFormat(k)
		for k in keys:
			if k in self._command: continue
			typeName = self.get(self._format[k]["type"])
			if type(data) is list:
				try: self[k] = data.pop(0)
				except IndexError:
					raise RPL.RPLError("Not enough data for %s. Cannot set %s." % (
						self._name, k
					))
				#endtry
			else:
				try: self[k] = data.next()
				except StopIteration:
					raise RPL.RPLError("Not enough data for %s. Cannot set %s." % (
						self._name, k
					))
				#endtry
			#endif
			if ":" in typeName:
				tmp = []
				ref = self._rpl.structsByName[typeName[typeName.index(":") + 1:]]
				one = ref.countExported() == 1
				for x in self.get(self[k]):
					t = ref.clone()
					if one: x = [x]
					else: x = x.get()
					t.importPrepare(rom, folder, filename, x)
					tmp.append(t)
				#endfor
				self[k] = RPL.List(tmp)
			#endif
		#endfor
	#enddef

	def importDataLoop(self, rom, base=None):
		"""
		Initially called from Data.importData
		"""
		if base is None: base = self.base(rom=rom)

		for k in self._format:
			fmt = self._format[k]
			data = self[k]
			typeName = self.get(self._format[k]["type"])
			if k in self._command:
				com = self._command[k]
				# If this was len, it's currently the size of the serialized data.
				# However, if the key it's for is end type, it needs to be adjusted
				# to the ending address instead.
				# TODO: This currently enforces that if one needs to reference
				# something with the end tag, it needs to be done after that
				# data struct, so that that data struct will be imported first.
				# I don't like this, but moving all this to __getitem__ means
				# that the data can't be changed.. There must be a nicer way to
				# get around this but it might take severe redesigning.
				if com[0] == "len" and self._format[com[1]]["end"]:
					self[k] = data = RPL.Number(data.get() + self._format[com[1]]["offset"])
				elif com[0] == "count" and self._format[com[1]]["end"]:
					# This was actually a count, not a size..
					size = 0
					for x in self.get(com[1]): size += x.len()
					self[k] = data = RPL.Number(size + self._format[com[1]]["offset"])
				#endif
			#endif
			if ":" in typeName:
				for x in self.get(data): x.importDataLoop(rom)
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

	def exportDataLoop(self, datafile=None):
		"""
		Initially called from Data.exportData
		Returns RPLData to write to the file
		"""
		ret = []
		# Ensures everything is loaded and tagged with commands, so nothing
		# is accidentally exported.. Not optimal I don't think?
		for k in self._format: self[k]
		for k in self._format:
			# We need to do it like this to ensure it had been read from the file...
			data = self[k]
			typeName = self.get(self._format[k]["type"])
			if ":" in typeName:
				ls = [x.exportDataLoop() for x in self.get(data)]
				data = RPL.List(ls)
			#endif
			# A command implies this data is inferred from the data that's
			# being exported, so it shouldn't be exported itself.
			if k not in self._command:
				if datafile is None: ret.append(data)
				else: datafile.add(data)
			#endif
		#endfor
		if ret:
			if self.countExported() > 1: return RPL.List(ret)
			else: return ret[0]
		#endif
	#enddef

	def calculateOffsets(self):
		calcedOffset = 0
		for k in self._format:
			fmt = self._format[k]
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
			typeName = self.get(self._format[k]["type"])
			if ":" in typeName:
				for x in self.get(data):
					x._base = RPL.Number(calcedOffset)
					calcedOffset += x.calculateOffsets()
				#endfor
			else:
				size = self.get(fmt["size"])
				if size == "expand":
					# TODO: I hate this
					size = len(self[k].serialize(**self.prepOpts(
						fmt, size=False
					)))
					fmt["size"] = RPL.Number(size)
				#endif
				calcedOffset += size
			#endif
		#endfor
		return calcedOffset
	#enddef

	def offsetOf(self, key):
		fmt = self._parseFormat(key)
		if fmt["offset"] is not None: return fmt["offset"]
		keys = self._format.keys()
		idx = keys.index(key)
		if idx == 0: fmt["offset"] = self.base()
		else:
			prevKey = keys[idx - 1]
			prevFmt = self._parseFormat(prevKey)
			if ":" in self.get(prevFmt["type"]):
				size = 0
				for x in self.get(self[prevKey]): size += x.len()
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
				fmt["size"] = RPL.Number(self.get(fmt["size"]) - fmt["offset"])
				fmt["end"] = False
			#endif
			return fmt["offset"]
		#endfor
	#enddef

	def len(self):
		if self._len is not None: return self._len
		size = 0
		for k in self._format:
			fmt = self._parseFormat(k)
			data = self[k]
			typeName = self.get(self._format[k]["type"])
			if ":" in typeName:
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
		if self._count is not None: return self._count
		count = 0

		# Ensure commands are set...
		for k in self._format: self._parseFormat(k)

		for k in self._format:
			if k not in self._command: count += 1
		#endfor
		self._count = count
		return count
	#enddef
#endclass

class Format(DataFormat, RPL.Cloneable):
	"""
	Represents the format of packed data.
	See Data for specifics
	"""
	typeName = "format"

	def __init__(self, rpl, name, parent=None):
		RPL.Cloneable.__init__(self, rpl, name, parent)
		DataFormat.__init__(self)
		self._base = None
	#enddef

	def basic(self, callers=[]):
		"""
		Returns the name with a prefix, used for referencing this as a type.
		"""
		return RPL.Literal("Format:" + self._name)
	#enddef

	def base(self, value=None, rom=None, offset=0):
		if rom is None: rom = self._rpl.rom
		rom.seek(self._base.get() + offset)
		return rom.tell()
	#enddef

	def __getitem__(self, key):
		if key == "base":
			return self._base
		else: return DataFormat.__getitem__(self, key)
	#enddef
#endclass

# TODO: Support txt, bin, json, and csv? exports
# TODO: Export RPLs with statics too instead of being so nameless
class Data(DataFormat, RPL.Serializable):
	"""
	Manages un/structured binary data.
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
	endian:  Default endian, may be "little" or "big". Defaults to "little"
	pad:     Default padding character, default is "$00"
	padside: Default padside, may be "left", "right", "center", or "rcenter".
	         Default is "right"
	sign:    Default sign, may be "signed" or "unsigned". Defaults to "unsigned"
	pretty:  Pretty print data, particularly relevant to lists.
	comment: Comment to write to the file. Great for when sharing the file.
	format:  Copy the x keys from given format struct *at this point* in the
	         data struct. This is a write-only key.
	"""
	typeName = "data"

	def __init__(self, rpl, name, parent=None):
		RPL.Serializable.__init__(self, rpl, name, parent)
		DataFormat.__init__(self)
		self.registerKey("pretty", "bool", "false")
		#self.registerKey("format", "string", "")
		self.registerKey("comment", "string", "")
	#enddef

	def __setitem__(self, key, data):
		if key == "format":
			data = data.get()
			if data[0:7] == "Format:": data = data[7:]
			struct = self._rpl.structsByName[data]
			for x in struct._format:
				self._format[x] = deepcopy(struct._format[x])
				# Update the references (this relies on the above being list form..
				# that means the format should only be used in format: calls..
				for d in self._format[x]:
					if isinstance(d, RPL.RPLRef): d._container = self
				#endfor
			#endfor
		else: DataFormat.__setitem__(self, key, data)
	#enddef

	def importData(self, rom, folder):
		self.calculateOffsets()
		self.importDataLoop(rom)
	#enddef

	def exportData(self, rom, folder):
		filename = self.open(folder, "rpl", True)
		datafile = self._rpl.share(filename, DataFile)
		datafile.comment = self["comment"].get()
		self.exportDataLoop(datafile)
	#enddef

	def prepareForProc(self, cloneName, cloneKey, cloneRef):
		# This only matters here when exporting, it should already be prepared
		# when importing.
		if self.importing: return
		for k in self._format:
			dataType = self.get(self._parseFormat(k)["type"])
			# We only care about the format types
			if dataType[0:7] != "Format:": continue
			# If this needs to be prepared, run the get to read in the data
			if dataType[7:] == cloneName: self[k]
			# Note we don't break here because it can be referenced multiple times
		#endfor
	#enddef
#endclass

class GenericGraphic(Graphic):
	"""
	Manage generic graphical content.
	read: Read direction. This can be almost any combination of L, R, U, and D.
	      LRUD is the general reading direction: Start in upper left and read
	      to the right until width, then go down a row.
	      LRDU is how bitmap files are read.
	      Other valid combinations: RLUD, RLDU, UDLR, DULR, UDRL, DURL
	      One can shorten these to the first and third letters, eg. LU.
	pixel: List of pixel formats, in order. More often than not there will
	       only be one pixel format. It will loop through these when it
	       reaches the end.
	palette: 0-based palette. Use i form in palette to index against this.
	"""
	typeName = "graphic"

	def __init__(self, rpl, name, parent=None):
		Graphic.__init__(self, rpl, name, parent)
		self.registerKey("read", "readdir", "LRUD")
		self.registerKey("pixel", "[pixel]*")
		self.registerKey("palette", "[color]+", "[]")
		self.registerKey("padding", "[string:(none, row, pixel, column), number]", "[none, 0]")

		self._image = None
	#enddef

	def importData(self, rom, folder):
		read = self["read"].get()
		width, height = tuple([x.get() for x in self["dimensions"].get()])

		# Create padding function...
		prev = 0
		padmethod, padmod = tuple([x.get() for x in self["padding"].get()])
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

		# Prepare palette
		self.definePalette([x.get() for x in self["palette"].get()])

		# Prepare data
		leftover = 0
		data = self._image.load()
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
		rom.write(stream.getvalue())
	#enddef

	def prepareImage(self):
		Graphic.prepareImage(self)
		width, height = tuple([x.get() for x in self["dimensions"].get()])
		numPixels = width * height

		# Create padding function...
		prev = 0
		padmethod, padmod = tuple([x.get() for x in self["padding"].get()])
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

		# Collect size of data to read
		bytes, leftovers = 0, ["", 0]
		pixels = self["pixel"].get()
		# TODO: Make more efficient for repeated rows or uniform pixel size...
		for i in helper.range(numPixels):
			pixel = pixels[i % len(pixels)]
			bytes += pixel._bytes
			leftovers[1] += pixel._extraBits
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

		# Prepare palette
		palette = [x.get() for x in self["palette"].get()]

		# Read pixels
		self.base()
		stream = StringIO(self._rpl.rom.read(bytes))
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
		self._image.putdata(data)

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
		if secondary == 3: self._image = self._image.transpose(Image.FLIP_TOP_BOTTOM)
		# if xxLR
		elif secondary == 0: self._image = self._image.transpose(Image.ROTATE_270)
		# if xxRL
		elif secondary == 1: self._image = self._image.transpose(Image.ROTATE_90)
		# if RLxx
		if primary == 1: self._image = self._image.transpose(Image.FLIP_LEFT_RIGHT)
		# if UDLR or DURL
		elif primary - secondary == 2: self._image = self._image.transpose(Image.FLIP_TOP_BOTTOM)
	#enddef
#endclass

class Map(RPL.Executable):
	"""
	Translates data. When exporting, it will look for the value in packed and
	output the corresponding value in unpacked. When importing, it does the
	reverse. un/packed keys may either both be lists or both be strings.
	String form is good for translating text between a ROM's custom encoding
	and ASCII or UTF8. Lists can translate numbers or strings. The benefit here
	being that it can translate strings longer than one character. However do
	remember that strings in RPL are UTF8 as it is. But if the custom encoding
	is multibyte, this will help.
	packed:   What the value should look like when packed.
	unpacked: What the value should look like when unpacked.
	data:     Reference to the data to modify. Data must be a string or number.
	unmapped: Method to handle data not represented in un/packed. May be:
	          except: Throw an exception.
	          add:    Write it as is.
	          drop:   Ignore it.
	"""
	typeName = "map"

	def __init__(self, rpl, name, parent=None):
		RPL.Executable.__init__(self, rpl, name, parent)
		self.registerKey("packed", "string|[number|string]+")
		self.registerKey("unpacked", "string|[number|string]+")
		self.registerKey("data", "[number|string]*")
		self.registerKey("unmapped", "string:(except, add, drop)", "except")
	#enddef

	def doProcessing(self, p, u):
		st = isinstance(p, RPL.String) and isinstance(u, RPL.String)
		if not st and (isinstance(p, RPL.String) or isinstance(u, RPL.String)):
			raise RPLError("Packed and unpacked must be the same type.")
		#endif
		p, u = p.get(), u.get()
		if len(p) != len(u):
			raise RPLError(
				"Packed (len: %i) and unpacked (len: %i) must be the same length."
				% (len(p), len(u))
			)
		#endif

		if st: nu = u
		else:
			nu = [x.get() for x in u]
		#endif

		def procString(string):
			if type(string) not in [str, unicode]:
				raise RPLError("Must use string data with string maps."
					"Tried to map %s." % type(string).__name__
				)
			#endif
			newstr = ""
			for i, x in enumerate(string):
				try:
					newstr += p[nu.index(x)]
				except ValueError:
					action = self["unmapped"].get()
					if action == "except":
						raise RPLError(u'Unmapped value: %s' % unicode(RPL.String(x)))
					elif action == "add": newstr += x
				#endtry
			#endfor
			return newstr
		#enddef

		def proc(data):
			if type(data) is list:
				newlist = []
				for i, x in enumerate(data):
					try:
						newlist.append(p[nu.index(x.get())])
					except ValueError:
						action = self["unmapped"].get()
						if action == "except":
							raise RPLError(u"Unmapped value: %s" % unicode(x))
						elif action == "add": newlist.append(x)
					#endtry
				#endfor
				return newlist
			else:
				try: return p[nu.index(data)].get()
				except ValueError:
					action = self["unmapped"].get()
					if action == "except":
						raise RPLError(u"Unmapped value: %s" % unicode(data))
					elif action == "add": return data
				#endtry
			#endif
		#enddef

		if st: self["data"].proc(procString)
		else: self["data"].proc(proc)
	#enddef

	def importProcessing(self):
		self.doProcessing(self["packed"], self["unpacked"])
	#enddef

	def exportProcessing(self):
		self.doProcessing(self["unpacked"], self["packed"])
	#enddef
#endclass

# Input/Output [dependent] Static
class IOStatic(RPL.Static):
	"""
	Returned data from a key depends on whether we're importing or exporting.
	Format is key: [import, export]
	"""
	typeName = "iostatic"

	def __getitem__(self, key):
		idx = 0 if self._rpl.importing else 1
		return self._data[key][idx]
	#enddef

	def __setitem__(self, key, value):
		if key not in self._data:
			# Initial set
			if not isinstance(value, RPL.List) or len(value.get()) != 2:
				raise RPLError("IOStatic requires each entry to be a list of two values.")
			#endif
			# This is supposed to be a static! So it should be fine to .get() here.
			self._data[key] = value.get()
		else:
			# When references set it
			idx = 0 if self._rpl.importing else 1
			self._data[key][idx] = value
		#endif
	#enddef
#endclass

################################################################################
##################################### Types ####################################
################################################################################
class Bin(RPL.String):
	"""
	Manages binary data.
	Prints data in a fancy, hex editor-like way.
	"""
	typeName = "bin"

	def set(self, data):
		RPL.String.set(self, data)
		data = re.sub(r'\s', "", self._data)
		self._data = ""
		for i in helper.range(0, len(data), 2):
			self._data += chr(int(data[i:i+2], 16))
		#endfor
	#endif

	def __unicode__(self):
		tmp = self._data
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
				RPL.String.binchr.sub(".", l1),
			)
			if l2: lastComment += " " + RPL.String.binchr.sub(".", l2) + os.linesep
			tmp = tmp[16:]
		#endwhile
		return ret + "," + lastComment[1:]
	#enddef

	def serialize(self, **kwargs): return self._data
	def unserialize(self, data, **kwargs): self._data = data

	@staticmethod
	def line2esc(ln):
		ret = u""
		for x in ln: ret += u"%02x " % ord(x)
		return ret
	#enddef
#endclass

#PIXEL = 0
class Pixel(RPL.String):
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
		self._source = data
		self._bigEndian = bigEndian

		tokens = Pixel.specification.match(data)
		if not tokens: raise RPLError("Invalid pixel format.")
		self._type = tokens.group(2)
		self._bits = (lambda(x): (1 if tokens.group(2) in "bB" else 4)*x)(
			max(int(tokens.group(1)), 1)
		)
		self._format = tokens.group(3)

		# Read this many bytes from the stream
		self._bytes = int(len(self._format) * self._bits / 8)
		self._extraBits = len(self._format) * self._bits % 8

		# Does a pixel fit perfectly within the certain number of bytes
		#self._even = (len(self._format) * self._bits) & 0x7 == 0

		# Expand the format
		self._expanded = ""
		for x in self._format: self._expanded += x * self._bits

		# Which "group" this is using (RGBA?, HSLA?, WA?, I)
		rgb = helper.oneOfIn("rRgGbB", self._format)
		hsl = helper.oneOfIn("hHsSlL", self._format)
		ww = helper.oneOfIn("wW", self._format)
		index = "i" in self._format
		if int(rgb) + int(hsl) + int(ww) + int(index) > 1:
			raise RPLError("Invalid pixel format, must only use one group.")
		#endif
		if rgb:   self._group = 0
		if hsl:   self._group = 1
		if ww:    self._group = 2
		if index: self._group = 3
		self._alpha = helper.oneOfIn("aA", self._format)

		self._max = {}
		for x in "RGBHSLWAI":
			self._max[x] = (1 << (self._expanded.count(x.lower()) + self._expanded.count(x))) - 1
		#endif
	#enddef

	def __unicode__(self):
		return (
			u"%ix" % (self._bits >> 2)
			if self._type in "xX" else
			u"%ib" % self._bits
		) + self._format
	#enddef

	def write(self, stream, palette, leftovers, pixel):
		"""
		leftovers: number of bits
		"""
		#global PIXEL
		r, g, b, a = pixel
		val  = {
			"R": int(round(r * self._max["R"] / 255)) if self._max["R"] else 0,
			"G": int(round(g * self._max["G"] / 255)) if self._max["G"] else 0,
			"B": int(round(b * self._max["B"] / 255)) if self._max["B"] else 0,
			# TODO: Calc HSL values
			# Silently ensure a grayscale value
			"W": int(round((r + b + g) / 3 * 255 / self._max["W"])) if self._max["W"] else 0,
			"A": int(round(a * 255 / self._max["A"])) if self._max["A"] else 0,
		}
		if self._max["I"]:
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
		for k, x in self._max.iteritems(): mask[k] = (x + 1) >> 1
		bytes, bits = [0], 8 - (leftovers + 1)
		for x in self._expanded[::-1]:
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
			bytes = leftovers[0] + stream.read(self._bytes + (1 if leftovers[1] < self._extraBits else 0))
			byte = 0
			mask = 1 << (leftovers[1] - 1)
		else:
			bytes = stream.read(self._bytes + (1 if self._extraBits else 0))
			byte = 0
			mask = 0x80
		#endif

		curbyte = ord(bytes[byte])
		for x in self._expanded:
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
			if self._max[x]: values[x] = int(round(values[x] * 255 / self._max[x]))
		#endfor

		a = 0xff
		if self._group == 0: r, g, b = values["R"], values["G"], values["B"]
		#elif self._group == 1: TODO
		elif self._group == 2: r, g, b = values["W"], values["W"], values["W"]
		elif self._group == 3:
			val = palette[values["I"]]
			a, r, g, b = (
				(val & 0xff000000) >> 24, (val & 0xff0000) >> 16,
				(val & 0xff00) >> 8, val & 0xff
			)
		if self._alpha: a = values["A"]

		#print "#%02x%02x%02x.%i%%" % (r, g, b, a * 100 / 255)
		return (r, g, b, a)
	#enddef

	@staticmethod
	def little(val, length):
		length /= 8
		# TODO: blahhhhh idec
	#enddef
#endclass

class Color(RPL.Named, RPL.HexNum, RPL.Literal, RPL.List):
	typeName = "color"

	_names = {
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
			else: self._data = data
		elif type(data) in [list, tuple]:
			self._data = (
				(data[0] & 0xff) << 16 |
				(data[1] & 0xff) << 8 |
				(data[2] & 0xff)
			)
			if len(data) == 4: self._data |= (255 - (data[3] & 0xff)) << 24
		else: RPL.Named.set(self, data, ["int", "long"])
	#enddef

	def __unicode__(self):
		return RPL.Named.__unicode__(self, "$%06x")
	#enddef

	def tuple(self):
		return (
			(self._data & 0x00ff0000) >> 16,
			(self._data & 0x0000ff00) >> 8,
			(self._data & 0x000000ff),
			255 - ((self._data & 0xff000000) >> 24),
		)
	#enddef
#endclass

class ReadDir(RPL.Literal):
	typeName = "readdir"

	valid = [
		"LRUD", "LRDU", "RLUD", "RLDU", "UDLR", "UDRL", "DULR",
		"DURL", "LU", "LD", "RU", "RD", "UL", "UR", "DL", "DR"
	]

	def set(self, data):
		RPL.Literal.set(self, data)
		if self._data in ReadDir.valid:
			self.primary, self.secondary = (
				"LRUD".index(self._data[0]),
				"LRUD".index(self._data[1 if len(self._data) == 2 else 2])
			)
		else:
			raise RPLError("Reading direction must be one of: %s." %
				helper.list2english(ReadDir.valid, "or")
			)
		#endif
	#endif

	def ids(self): return self.primary, self.secondary

	def rect(self, width, height):
		self._index, self._width, self._height = 0, width, height
		# Inner is Vertical, Inner Range, Outer Range
		self._iv = False
		if   self.primary == 0: self._ir = helper.range(self._width,)
		elif self.primary == 1: self._ir = helper.range(self._width - 1, -1, -1)
		elif self.primary == 2: self._iv, self._ir = True, helper.range(self._height,)
		elif self.primary == 3: self._iv, self._ir = True, helper.range(self._height - 1, -1, -1)
		if   self.secondary == 0: self._ori = iter(helper.range(self._width,))
		elif self.secondary == 1: self._ori = iter(helper.range(self._width - 1, -1, -1))
		elif self.secondary == 2: self._ori = iter(helper.range(self._height,))
		elif self.secondary == 3: self._ori = iter(helper.range(self._height - 1, -1, -1))
		if self._iv: self._x = self._ori.next()
		else: self._y = self._ori.next()
		self._iri = iter(self._ir)
		return self
	#enddef

	def __iter__(self): return self

	def next(self):
		try: ii = self._iri.next()
		except StopIteration:
			# Let this raise stop iteration when it's done
			if self._iv: self._x = self._ori.next()
			else: self._y = self._ori.next()
			self._iri = iter(self._ir)
			return self.next()
		else:
			if self._iv: i, x, y = self._index, self._x, ii
			else: i, x, y = self._index, ii, self._y
			self._index += 1
			return i, x, y
		#endif
	#enddef
