import os
import re
import Image
import helper
import rpl as RPL
from rpl import RPLError
from textwrap import dedent
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

	rpl.registerType(Bin)
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
	def __init__(self, width, height):
		self._dimensions = (0, 0)
		self._image = None
		self._pixels = None
	#enddef

	def read(self):
		if self._image is None: self._image = Image.open(self._path)
	#enddef

	def write(self):
		if self._image is None: return # Maybe throw an exception?
		self._image.save(self._path)
	#enddef

	def newImage(self, dimens=(1, 1)):
		self._image = Image.new("RGBA", dimens)
		self._image.paste(0xffffff, (0, 0))
		self._pixels = self._image.load()
	#endif

	def ensureSize(width, height):
		# Only necessary when writing, remember!
		if self._image is None: self.newImage((width, height))
		elif self._image.size[0] < width or self._image.size[1] < height:
			region = self._image.crop((0, 0, width, height))
			region.load()
			self._image.paste(0xffffff, (0, 0))
			self._image.resize((width, height))
			self._image.paste(region, (0, 0))
		#endif
	#enddef

	def addRect(self, data, left, top, right, bottom):
		if self._image is None: self.newImage()
		region = Image.new("RGBA", (right - left, bottom - top))
		region.putdata(data)
		self._image.paste(region, (left, top, right, bottom))
	#enddef

	def addImage(self, image, left, top):
		if self._image is None: self.newImage()
		self._image.paste(image, (left, top))
	#enddef

	def addPixel(self, rgba, x, y):
		if self._image is None: self.newImage()
		self._pixels[x, y] = rgba
	#enddef
#endclass

################################################################################
############################# Media Parent Structs #############################
################################################################################

class Graphic(RPL.Serializable):
	"""
	Structs that handle images should inherit this.
	"""

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		self.registerKey("rotate", "number", "0")
		self.registerKey("mirror", "bool", "false")
		self.registerKey("flip", "bool", "false")
		self.registerKey("blank", "color", "white")
		self.registerKey("dimensions", "[number, number]")
		self.registerKey("offset", "[number, number]", "[0, 0]")
	#enddef

	def importTransform(self, img):
		if self["rotate"] != 0:
			img = img.transpose([
				Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270
			][self["rotate"] - 1])
		#endif
		if self["mirror"]: img = img.transpose(Image.FLIP_LEFT_RIGHT)
		if self["flip"]: img = img.transpose(Image.FLIP_TOP_BOTTOM)
		return img
	#enddef

	def exportTransform(self, img):
		if self["flip"]: img = img.transpose(Image.FLIP_TOP_BOTTOM)
		if self["mirror"]: img = img.transpose(Image.FLIP_LEFT_RIGHT)
		if self["rotate"] != 0:
			img = img.transpose([
				Image.ROTATE_270, Image.ROTATE_180, Image.ROTATE_90
			][self["rotate"] - 1])
		#endif
		return img
	#enddef
#endclass

class Sound(RPL.Serializable):
	"""
	Structs that handle sound should inherit this.
	"""
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
		self.registerKey("endian", "string", "little")
		self.registerKey("pad", "string", "\x00")
		self.registerKey("padside", "string", "left")
		self.registerKey("sign", "string", "unsigned")
		self.registerKey("x", "string|[string, number, string|number]+1", "")

		self._parentClass = RPL.Cloneable if isinstance(self, RPL.Cloneable) else RPL.Serializable
		self._format = odict()
		self._command = {}
		self._len = None
		self._count = None
		self.importing = False
		#endif
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

	def offsetOf(self, key):
		fmt = self._parseFormat(key)
		if fmt["offset"] is not None: return fmt["offset"]
		keys = self._format.keys()
		for i in range(keys.index(key)-1, -1, -1):
			if keys[i][0] == "x":
				lastKey = keys[i]
				lastFmt = self._parseFormat(lastKey)
				lastType = self.get(lastFmt["type"])
				if ":" in lastType:
					size = 0
					for x in self.get(self[lastKey]): size += x.len()
				else: size = self.get(lastFmt["size"])
				fmt["offset"] = self.offsetOf(lastKey) + size
				return fmt["offset"]
			#endif
		#endfor
	#enddef

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
					address = self["base"].get() + offset
					self._rpl.rom.seek(address, 0)
					typeName = self.get(fmt["type"])
					if ":" in typeName:
						tmp = []
						ref = self._rpl.child(typeName[typeName.index(":") + 1:])
						for i in range(self.get(fmt["size"])):
							t = ref.clone()
							t._base = RPL.Number(address)
							if hasattr(t, "exportPrepare"): t.exportPrepare(self._rpl.rom)
							tmp.append(t)
							address += t.len()
						#endfor
						self._data[key] = RPL.List(tmp)
					else:
						self._data[key] = self._rpl.wrap(typeName)
						self._data[key].unserialize(
							self._rpl.rom.read(self.get(fmt["size"])),
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
			else: self._data[key] = value
		else:
			self._parentClass.__setitem__(self, key, value)
		#endif
	#enddef

	def importPrepare(self, folder, filename=None, data=None):
		self.importing = True
		filename = filename or self.open(folder, "rpl", True)
		data = data or self._rpl.share(filename, DataFile)
		keys = [x for x in self._format]
		for k in keys: self._parseFormat(k)
		for k in keys:
			if k in self._command: continue
			typeName = self.get(self._format[k]["type"])
			if type(data) is list:
				if len(data): self[k] = data.pop(0)
				else:
					raise RPL.RPLError("Not enough data for %s. Cannot set %s." % (
						self._name, k
					))
				#endif
			else: self[k] = data.next()
			if ":" in typeName:
				tmp = []
				ref = self._rpl.child(typeName[typeName.index(":") + 1:])
				one = ref.countExported() == 1
				for x in self.get(self[k]):
					t = ref.clone()
					if one: x = [x]
					else: x = x.get()
					t.importPrepare(folder, filename, x)
					tmp.append(t)
				#endfor
				self[k] = RPL.List(tmp)
			#endif
		#endfor
	#enddef

	def importDataLoop(self, rom):
		"""
		Initially called from Data.importData
		"""
		base = self["base"].get()
		for k in self._format:
			fmt = self._format[k]
			data = self[k]
			typeName = self.get(self._format[k]["type"])
			if ":" in typeName:
				for x in self.get(data): x.importDataLoop(rom)
			else:
				data = data.serialize(**self.prepOpts(fmt))
				size = self.get(fmt["size"])
				if len(data) != size:
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
		calcedOffset=0
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
				fmt["offsetRefs"][0].set(offset)
			#endif
			data = self[k]
			fmt["offset"] = calcedOffset
			typeName = self.get(self._format[k]["type"])
			if ":" in typeName:
				for x in self.get(data):
					x._base = RPL.Number(calcedOffset)
					calcedOffset += x.calculateOffsets()
				#endfor
			else: calcedOffset += self.get(fmt["size"])
		#endfor
		return calcedOffset
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
	[type, size, offset?, endian?, sign?, pad char?, pad side?]
	All entries with a ? are optional, and order of them doesn't matter.
	Type: Datatype by name, for example: string, number
	Size: Size of the field in bytes
	Offset: Offset from base to where this entry is. By default this is
	        calculated from the sizes, but there are times it may be
	        necessary to supply it (dynamic sizing in the middle).
	Endian: Only relevant to numbers, can be "little" or "big"
	Sign: Only relevant to numbers, can be "signed" or "unsigned"
	Pad char: Only relevant to strings, it's the char to pad with.
	Pad side: Only relevant to strings, can be "left", "right", or "center"
	"""
	typeName = "data"

	def __init__(self, rpl, name, parent=None):
		RPL.Serializable.__init__(self, rpl, name, parent)
		DataFormat.__init__(self)
		self.registerKey("pretty", "bool", "false")
		self.registerKey("comment", "string", "")
	#enddef

	def importData(self, rom):
		self.calculateOffsets()
		self.importDataLoop(rom)
	#enddef

	def exportData(self, folder):
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
	"""
	def __init__(self, rpl, name, parent=None):
		Graphic.__init__(self, rpl, name, parent)
		self.registerKey("read", "string", "LRUD")
		self.registerKey("pixel", "[string]*")
		self.registerKey("dimen", "[number, number]", "")
		self.registerKey("pallet", "[color]+", "[]")

		self._image = None
	#enddef

	def __setitem__(self, key, data):
		if key == "pallet":
			l = data.get()

			# If there's no alpha data in the pallet...
			for x in l:
				if x & 0xff000000: return Graphic.__setitem__(self, key, data)
			#endfor

			# ...set all of the alpha to fully visible
			for i in range(len(l)): l[i] |= 0xff000000
		#endif
		return Graphic.__setitem__(self, key, data)
	#enddef

	def exportPrepare(self, rom):
		self._image = Image("RGBA", (self["width"].get(), self["height"].get()))
		self._image.paste(self["blank"].get(), (0, 0))
	#enddef

	def exportData(self, folder):
		filename = self.open(folder, "png", True)
		image = self._rpl.share(filename, ImageFile)
		image.ensureSize(self["width"].get(), self["height"].get())
	#enddef
#endclass

class Map(RPL.Executable):
	"""
	Translates data.
	TODO: More info
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
		RPL.String.__init__(self, data)
		data = re.sub(r'\s', "", self._data)
		self._data = u""
		for i in xrange(0, len(data), 2):
			self._data += unichr(int(data[i:i+2], 16))
		#endfor
	#endif

	def __unicode__(self):
		tmp = self._data
		ret = u""
		while tmp:
			l1, l2 = tmp[0:8], tmp[8:]
			ret += "`%s %s` # %s %s%s" % (
				Bin.line2esc(l1), Bin.line2esc(l2)[0:-1],
				RPL.String.binchr.sub(".", l1),
				RPL.String.binchr.sub(".", l2), os.linesep
			)
		#endwhile
	#enddef

	@staticmethod
	def line2esc(ln):
		ret = u""
		for x in ln: ret += u"%02x " % ord(x)
		return ret
	#enddef
#endclass

class Pixel(RPL.String):
	typeName = "pixel"

	specification = re.compile(r'(\d+)([bBxX])([rgbRGBhslHSLwWaAi0]+)')

	def set(self, data, bigEndian):
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
		 * Index in a pallet
		 * 0 is ignored
		"""
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
		rgb = helper.onOfIn("rRgGbB", self._format)
		hsl = helper.onOfIn("hHsSlL", self._format)
		ww = helper.onOfIn("wW", self._format)
		index = "i" in self._format
		if int(rgb) + int(hsl) + int(ww) + int(index) > 1:
			raise RPLError("Invalid pixel format, must only use one group.")
		#endif
		if rgb:   self._group = 0
		if hsl:   self._group = 1
		if ww:    self._group = 2
		if index: self._group = 3
		self._alpha = helper.onOfIn("aA", self._format)

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

	def read(stream, pallet, leftovers):
		"""
		leftovers: (data, number of bits)
		"""
		values = {
			"R": 0,
			"G": 0,
			"B": 0,
			"H": 0,
			"S": 0,
			"L": 0,
			"W": 0,
			"A": 0,
			"i": 0,
		}

		if leftovers[1]:
			bytes = leftovers[0] + stream.read(self._bytes + (1 if leftovers[1] < self._extraBits else 0))
			byte = 0
			mask = 1 << (leftovers[1] - 1)
		else:
			bytes = stream.read(self._bytes + (1 if self._extraBits else 0))
			byte = 0
			mask = 0x80
		#endif

		for x in self._expanded:
			if x != "0":
				bit = 1 if bytes[byte] & mask else 0
				if x in "rgbhslwa": bit ^= 1
				values[x] = values[x] << 1 | bit
			#endif
			mask >>= 1
			if mask == 0:
				byte += 1
				mask = 0x80
			#endif
		#endfor

		if mask == 0x80: leftovers = ("", 0)
		else:
			leftovers = (bytes[byte], {
				0x40: 7, 0x20: 6, 0x10: 5,
				0x08: 4, 0x04: 3, 0x02: 2, 0x01: 1,
			}[mask])
		#endif

		a = 0xff
		if self._group == 0: r, g, b = values["R"], values["G"], values["B"]
		#elif self._group == 1: TODO
		elif self._group == 2: r, g, b = values["W"], values["W"], values["W"]
		elif self._group == 3: r, g, b, a = pallet[values["i"]]
		if self._alpha: a = values["A"]

		return a << 24 | b << 16 | g << 8 | r
	#enddef

	@staticmethod
	def little(val, length):
		length /= 8
		# TODO: blahhhhh idec
	#enddef
#endclass

class Color(RPL.Named):
	typeName = "color"

	_names = {
		"black":   0x000000,
		"white":   0xffffff,
		"red":     0xff0000,
		"blue":    0x00ff00,
		"green":   0x0000ff,
		"yellow":  0xffff00,
		"magenta": 0xff00ff,
		"pink":    0xff00ff,
		"cyan":    0x00ffff,
		"gray":    0xa5a5a5,
	}

	def set(self, data):
		if type(data) in [int, long]:
			if data & ~0xffffffff: raise RPLError("Colors must be 3-4 byte values.")
			else: self._data = data
		else: RPL.Named.set(data, ["int", "long"])
	#enddef

	def __unicode__(self):
		return RPL.Named.__unicode__(self, "$%06x")
	#enddef
#endclass
