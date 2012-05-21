import rpl as RPL
from rpl import RPLError
import Image
import os
import re

class Standard(RPL.RPL):
	def __init__(self):
		RPL.RPL.__init__(self)
		self.regStruct(Data)
		self.regStruct(Format)
	#enddef
#endclass

class DataFile:
	def __init__(self, inFile=None):
		self._base = []
		self.comment = ""
		if inFile is not None: self.read(inFile)
	#enddef

	def setup(self, rpl, path): self._rpl, self._path = rpl, path

	def read(self):
		"""Read from .rpl data file."""
		rpl = self._rpl
		raw = rpl.readFrom(self._path)

		base = []
		adder = []
		for token in rpl.tokenize.finditer(raw):
			groups = token.groups() # Used later
			dstr,sstr,mstr,num,key,afterkey,flow,ref,lit = groups
			sstr = dstr or sstr # Double or single

			# Find the position (used for ref and errors)
			pos = token.start()
			line, char = raw.count("\n",0,pos) + 1, pos - raw.rfind("\n",0,pos) + 1

			add, skipSubInst = None, None

			try:
				if flow and flow in "{}": raise RPLError("Structs not allowed in data files")
				elif flow == "[":
					# Begins list
					adder.append([])
				elif flow == "]":
					# End list
					if adder:
						add = ("list", adder.pop())
						skipSubInst = True
					else: raise RPLError("] without a [.")
				elif sstr or mstr or num or ref or lit:
					add = rpl.parseData(groups, line=line, char=char)
				else: continue

				if add:
					val = rpl.parseCreate(add, None, None, line, char, skipSubInst)

					if adder: adder[-1].append(val)
					else: base.append(val)
				#endif
			except RPLError as err:
				rpl.err("Error in line %i char %i: %s" % (
					line, char, err.args[0]
				))
			#endtry
		#endfor

		self._base = base
	#enddef

	def write(self):
		"""Write data to a given file."""
		# TODO: Prettyprinting
		comment = "# " + self.comment if self.comment else ""
		self._rpl.writeTo(self._path, comment + os.linesep.join(map(unicode, self._base)))
	#enddef

	def add(self, item):
		"""Add item to data. Must be RPLData type"""
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

################################################################################
#################################### Structs ###################################
################################################################################

class Graphic(RPL.Serializable):
	"""Structs that handle images should inherit this."""

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		self.regKey("rotate", "number", "0")
		self.regKey("mirror", "number", "false")
		self.regKey("flip", "number", "false")
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
	"""Structs that handle sound should inherit this."""
	pass
#endclass

class DataFormat:
	"""The mutual parent for Data and Format"""
	def __init__(self):
		# String only uses default data size. Number only uses bin as type
		self.regKey("endian", "string", "little")
		self.regKey("pad", "string", "\x00")
		self.regKey("padside", "string", "left")
		self.regKey("sign", "string", "unsigned")
		self.regKey("x", "string|[string, number, string|number]+1", "")

		self._parentClass = RPL.Cloneable if isinstance(self, RPL.Cloneable) else RPL.Serializable
		self._format = {}
		self._command = {}
		self._len = None
		self._count = None
		self.importing = False
	#enddef

	def __parseFormat(self, key):
		fmt = self._format[key]
		if isinstance(fmt, RPL.List):
			fmt = fmt.get()
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
					if self.get(tmp["type"])[0:7] == "Format:":
						self._command[refKey] = ["count", key]
					else: self._command[refKey] = ["len", key]
				#endif
			#endif
			for x in fmt[2:]:
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
				for i in range(self._orderedKeys.index(key)):
					if self._orderedKeys[i][0] == "x":
						first = False
						break
					#endif
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
		fmt = self._format[key]
		if fmt["offset"] is not None: return fmt["offset"]
		for i in range(self._orderedKeys.index(key)-1, -1, -1):
			if self._orderedKeys[i][0] == "x":
				lastKey = self._orderedKeys[i]
				lastFmt = self._format[lastKey]
				lastType = self.get(lastFmt["type"])
				if lastType[0:7] == "Format:":
					size = 0
					for x in self[lastKey]: size += x.len()
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
				fmt = self.__parseFormat(key)
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
							if type(self[com[1]]) is list:
								self._data[key] = RPL.Number(len(self[com[1]]))
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
					if typeName[0:7] == "Format:":
						tmp = []
						ref = self._rpl.child(typeName[7:])
						for i in range(self.get(fmt["size"])):
							t = ref.clone()
							t._base = RPL.Number(address)
							tmp.append(t)
							address += t.len()
						#endfor
						self._data[key] = tmp
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
				# We don't want "x" in here
				self._orderedKeys[-1] = key
				tmp = self._data["x"]
				if isinstance(tmp, RPL.String):
					self._format[key] = RPL.List(
						map((lambda(x): self._rpl.parseData(x)), tmp.get().split())
					)
				else: self._format[key] = tmp
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
		for k in self.iterkeys():
			if k[0] != "x": continue
			self.__parseFormat(k)
		#endfor
		for k in self.iterkeys():
			if k[0] != "x": continue
			if k in self._command: continue
			typeName = self.get(self._format[k]["type"])
			if type(data) is list: self[k] = data.pop(0)
			else: self[k] = data.next()
			if typeName[0:7] == "Format:":
				# Referencing this wouldn't end well. I'm not sure how to
				# handle it either..
				tmp = []
				ref = self._rpl.child(typeName[7:])
				one = ref.countExported()
				for x in self[k].get():
					t = ref.clone()
					if one: x = [x]
					else: x = x.get()
					t.importPrepare(folder, filename, x)
					tmp.append(t)
				#endfor
				self[k] = tmp
			#endif
		#endfor
	#enddef

	def exportDataLoop(self, datafile=None):
		ret = []
		# Ensures everything is loaded and tagged with commands, so nothing
		# is accidentally exported.. Not optimal I don't think?
		for k in self.iterkeys(): self[k]
		for k in self.iterkeys():
			if k[0] != "x": continue
			# We need to do it like this to ensure it had been read from the file...
			data = self[k]
			typeName = self.get(self._format[k]["type"])
			if typeName[0:7] == "Format:":
				ls = []
				for x in data: ls.append(x.exportDataLoop())
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

	def importDataLoop(self, rom):
		base = self["base"].get()
		for k in self.iterkeys():
			if k[0] != "x": continue
			fmt = self._format[k]
			data = self[k]
			if type(data) == list:
				for x in data: x.importDataLoop(rom)
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

	def calculateOffsets(self):
		calcedOffset=0
		for k in self.iterkeys():
			if k[0] != "x": continue
			fmt = self._format[k]
			# Get real offset
			offset = calcedOffset
			if fmt["offset"] is not None and fmt["offsetRefs"]:
				# Remove sum of static offsets
				offset -= fmt["offset"]
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
			if type(data) == list:
				for x in data:
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
		for k in self.iterkeys():
			if k[0] != "x": continue
			fmt = self.__parseFormat(k)
			if self.get(fmt["type"])[0:7] == "Format:":
				for x in self[k]: size += x.len()
			else: size += self.get(fmt["size"])
		#endfor
		self._len = size
		return size
	#enddef

	def countExported(self):
		if self._count is not None: return self._count
		count = 0
		for k in self.iterkeys():
			if k[0] != "x": continue
			self.__parseFormat(k)
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
		self.alsoClone("_format","_command")
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

# TODO: Support txt and bin exports
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
		self.regKey("pretty", "number", "false")
		self.regKey("comment", "string", "")
	#enddef

	def importData(self, rom):
		self.calculateOffsets()
		self.importDataLoop(rom)
	#enddef

	def exportData(self, rom, folder):
		filename = self.open(folder, "rpl", True)
		datafile = self._rpl.share(filename, DataFile)
		datafile.comment = self["comment"].get()
		self.exportDataLoop(datafile)
	#enddef
#endclass

class Map(RPL.Executable):
	"""
	Translates data
	"""
	def __init__(self, rpl, name, parent=None):
		# Yes, it only wants RPLStruct's init, NOT Serializable's!!
		RPL.Executable.__init__(self, rpl, name, parent)
		self.regKey("packed", "string|[number|string]+")
		self.regKey("unpacked", "string|[number|string]+")
		self.regKey("data", "[number|string]*")
	#enddef

	def xxProcessing(self, p, u):
		st = isinstance(p, RPL.String) and isinstance(u, RPL.String)
		if not st and (isinstance(p, RPL.String) or isinstance(u, RPL.String)):
			raise RPLError("Packed and unpacked must be the same type.")
		#endif
		p, u = p.get(), u.get()
		if len(p) != len(u):
			raise RPLError("Packed and unpacked must be the same length.")
		#endif

		np = []
		for x in p: np.append(x.get())
		nu = []
		for x in u: nu.append(x.get())

		def proc(ls):
			newstr = ""
			for i,x in enumerate(ls):
				try:
					if st: newstr += np[nu.index(x)]
					else: x.set(np[nu.index(x)])
				except ValueError:
					if st: newstr += x
				#endtry
			#endfor
			if st: self["data"].set(newstr)
		#enddef

		self["data"].proc(proc)
	#enddef

	def importProcessing(self, rom, folder):
		self.xxProcessing(self["packed"], self["unpacked"])
	#enddef

	def exportProcessing(self, rom, folder):
		self.xxProcessing(self["unpacked"], self["packed"])
	#enddef
#endclass

################################################################################
##################################### Types ####################################
################################################################################
class Bin(RPL.String):
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
