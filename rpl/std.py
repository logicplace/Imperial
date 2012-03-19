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
	"""Manages un/structured binary data."""
	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		# String only uses default data size. Number only uses bin as type
		self.regKey("format", "number|[[string|^,number]!0]*")
		self.regKey("times", "number", 1)
		self.regKey("endian", "string", "little")
		self.regKey("pad", "string", "\x00")
		self.regKey("padleft", "number", "false")
		self.regKey("pretty", "number", "false")
		self.regKey("comment", "string", "")
	#enddef

	def importData(self, rom, folder):
		tmp = self["format"].get()
		tmp0 = tmp[0].get()
		fn = self.open(folder,
			(("bin" if len(tmp0) == 1 and isinstance(tmp0[0], rpl.Number) else
			("txt" if tmp0[0].get() == "string" else "rpl"
			)) if len(tmp) == 1 else "rpl"),
			True # Have to check ext, so just ask for the name
		)
		# Or does it always return a period? Seems odd if it does..
		ext = os.path.splitext(fn)[1][len(os.extsep):]
		if ext not in ["bin", "rpl", "txt"]:
			raise rpl.RPLError("Expecting file format bin, rpl, or txt.")
		#endif

		data = self._data = self._rpl.parseDataFile(fn)
		# Standard format is a list of Numbers, Strings, or lists
		# containing [String, Number]
		towrite = r''
		def recurse(fmt, dta):
			for i,x in enumerate(fmt):
				y = dta[i]
				if isinstance(x, rpl.List):
					tmp = x.get()
					if len(tmp) == 2 and isinstance(tmp[1], rpl.Number):
						dtype, dsize = tuple(x.get())
				if isinstance(x, rpl.String):
					try:
						dtype, dsize = x, self._rpl.types[x.get()].defaultSize()
					except KeyError, AttributeError:
						dtype, dsize = x, rpl.Number(1)
					#endtry
				#endif

				# Verify type and recast
				if (dtype == "all"
					or isinstance(y, self.__rpl.types[dtype])
				): pass
				elif issubclass(self.__rpl.types[dtype], y.__class__):
					# Attempt to recast to subclass
					try: y = self.__rpl.types[dtype](y.get())
					except RPLError:
						raise rpl.RPLError("Cannot recast %s to desired type %s." % (y.typeName, dtype))
					#endtry
				else:
					raise rpl.RPLError("Expected type %s got %s." % (dtype, y.typeName))
				#endif

				# Actual importing
				towrite += y.serialize(**{
					"size": dsize,
					"endian": self["endian"]
				})
			#endfor
		#enddef
		recurse(self["format"], data)
	#enddef

	def exportData(self, rom, folder):
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
