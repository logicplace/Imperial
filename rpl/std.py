import rpl
import Image
import os
import re

class Standard(rpl.RPL):
	def __init__(self):
		rpl.RPL.__init__(self)
		self.regStruct(Data)
	#enddef

	def parseDataFile(self, inFile):
		#try: self.dataFiles
		#except AttributeError: self.dataFiles = []

		raw = self.readFrom(inFile)

		base = []
		adder = []
		for token in RPL.tokenize.finditer(raw):
			groups = token.groups() # Used later
			dstr,sstr,mstr,num,key,flow,ref,lit = groups
			sstr = dstr or sstr # Double or single

			# Find the position (used for ref and errors)
			pos = token.start()
			line, char = raw.count("\n",0,pos) + 1, pos - raw.rfind("\n",0,pos) + 1

			add, skipSubInst = None, None

			try:
				if flow in "{}": raise RPLError("Structs not allowed in data files")
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
					add = self.parseData(groups, line=line, char=char)
				else: continue

				if add:
					dtype, val = self.parseCreate(add, line=line, char=char, skipSubInst=skipSubInst)

					if adder: adder[-1].append(val)
					else: base.append(val)
				#endif
			except RPLError as err:
				rpl.err("Error in line %i char %i: %s" % (
					line, char, err.args[0]
				)
			#endtry
		#endfor

		#self.dataFiles.append(base)
		return base
	#enddef
#endclass

################################################################################
#################################### Structs ###################################
################################################################################

class Graphic(rpl.Serializable):
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

class Sound(rpl.Serializable):
	"""Structs that handle sound should inherit this."""
	pass
#endclass

class Data(rpl.Serializable):
	"""Manages un/structured binary data.
	What I think this needs to support:
	 * Self-referencing entries for length
	 * Ability to use system's references
	 * Integration with system datatypes
	 * Describe type, size, endian, sign, and padding
	"""
	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		# String only uses default data size. Number only uses bin as type
		self.regKey("format", "string", "")
		self.regKey("times", "number", 1)
		self.regKey("endian", "string", "little")
		self.regKey("pad", "string", "\x00")
		self.regKey("padside", "string", "left")
		self.regKey("pretty", "number", "false")
		self.regKey("comment", "string", "")
		self.regKey("x", "string|[string, number, string|number]+1", "")
	#enddef

	def __setitem__(self, key, value):
		rpl.Serializable.__setitem__(self, key, value)
		# Special handling for keys starting with x
		if key[0] == "x":
			self._data[key] = self._data["x"]
			del self._data["x"]
		#endif
	#enddef

	# TODO: Redo as:
	# data {
	# 	endian: etc
	#
	# 	xlen: [number, 1] # [number, 1, little, signed]
	# 	xstr: [string, @this.xlen]
	# }
	def importData(self, rom, folder):
		"""
		Represents the format of packed data.
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
	#enddef

	def exportData(self, rom, folder):
	#enddef
#endclass

class Map(rpl.Serializable):
	"""
	Translates data
	It seems silly that this is serializable, but it needs to know direction.
	"""
	def __init__(self, rpl, name, parent=None):
		# Yes, it only wants RPLStruct's init, NOT Serializable's!!
		RPLStruct.__init__(self, rpl, name, parent)
		self.regKey("packed", "string|[number|string]+")
		self.regKey("unpacked", "string|[number|string]+")
		self.regKey("data", "[number|string]*")
	#enddef

	def xxData(self, p, u):
		ls = self["data"].get()
		st = isinstance(p, rpl.String) and isinstance(u, rpl.String)
		if not st and (isinstance(p, rpl.String) or isinstance(u, rpl.String)):
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

	def importData(self, rom, folder):
		self.xxData(self["packed"], self["unpacked"])
	#enddef

	def exportData(self, rom, folder):
		self.xxData(self["unpacked"], self["packed"])
	#enddef
#endclass

################################################################################
##################################### Types ####################################
################################################################################
class Bin(rpl.String):
	typeName = "bin"

	def set(self, data):
		rpl.String.__init__(self, data)
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
				rpl.String.binchr.sub(".", l1),
				rpl.String.binchr.sub(".", l2), os.linesep
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
