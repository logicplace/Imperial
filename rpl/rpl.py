import re
import codecs
from sys import stderr

def err(msg): stderr.write(unicode(msg) + u"\n")

class RPLError(Exception): pass

class RPL:
	"""
	The base type for loading and interpreting RPL files.
	Also handles "execution" and what not.
	"""

	# Constants
	tokenize = re.compile(
		(r'\s*(?:'                                 # Whitespace
		+r'"([^"\r\n]*)"|'                         # String
		# Have to remove `s in processing
		+r'((?:`[^`]*`\s*)+)|'             # Multi-line String
		#+r'\$([0-9a-fA-F]+)(?![0-9a-fA-F]*[\-:])|' # Hexadecimal number
		# Number or range (verify syntactically correct range later)
		+r'(%(r1)%(r2)%(r1):\-*%(r2)*(?=[ ,]|$))|'
		+r'(%(key)):|'                             # Key
		+r'([{}\[\],])|'                           # Flow Identifier
		+r'@([^%(lit).]+(?:\.%(key))?(?:\[[0-9]+\])*)|' # Reference
		+r'([^%(lit)]+)|'                          # Unquoted string or struct name/type
		+r'#.*$)'                                  # Comment
		) % {
			'r1': r'(?:[0-9'
			,'r2': r']|(?<![a-zA-Z])[a-z](?![a-zA-Z])|\$[0-9a-fA-F]+)'
			,'lit': r'{}\[\],\$"#\r\n'
			,'key': r'[a-z]+[0-9]*'
		}
	, re.M | re.U)

	multilineStr = re.compile(r'`([^`]*)`')

	number = re.compile(
		# Must start with a number, or a single letter followed by a :
		(r'(?:%(numx)|[a-z](?=:))'
		# Range split group
		+r'(?:'
		# Can match a range or times here
		+r'(?:%(bin)(%(numx)))?'
		# Must match a split, can either be a number or single letter followed by a :
		+r':(?:%(numx)|[a-z](?=[: ]|$))'
		+r')*'
		# To be sure we're able to end in a range/times
		+r'(?:%(bin)(?:%(numx)))?'
		) % {
			'bin': r'[\-*]'
			,'numx': r'[0-9]+|\$[0-9a-fA-F]+'
		}
	)
	isRange = re.compile(r'.*[:\-*].*')

	# Predefined
	static = {
		 "false":   0
		,"true":    1
		,"black":   0x000000
		,"white":   0xffffff
		,"red":     0xff0000
		,"blue":    0x00ff00
		,"green":   0x0000ff
		,"yellow":  0xffff00
		,"magenta": 0xff00ff
		,"pink":    0xff00ff
		,"cyan":    0x00ffff
		,"gray":    0xa5a5a5
		,"byte":    1
		,"short":   2
		,"long":    4
		,"double":  8
		,"LU":      "LRUD"
		,"LD":      "LRDU"
		,"RU":      "RLUD"
		,"RD":      "RLDU"
		,"UL":      "UDLR"
		,"UR":      "UDRL"
		,"DL":      "DULR"
		,"DR":      "DURL"
	}

	types = {}
	structs = {}
	root = {}

	def readFrom(self, etc):
		"""
		Helper class to read from a file or stream
		"""
		if type(etc) in [str, unicode]:
			x = codecs.open(etc, encoding="utf-8", mode="r")
			ret = x.read()
			x.close()
			return ret
		else: return etc.read()
	#enddef

	def writeTo(self, etc, data):
		"""
		Helper class to write to a file or stream
		"""
		if type(etc) in [str, unicode]:
			x = codecs.open(etc, encoding="utf-8", mode="w")
			ret = x.write(data)
			x.close()
			return ret
		else: return etc.write(data)
	#enddef

	def parse(self, inFile):
		"""
		Read in a file and parse it.
		"""
		raw = self.readFrom(inFile)
		tokens = self.tokenize.findall(raw)

		lastLit = None
		currentKey = None
		currentStruct = None
		counts = {}
		adder = []

		for token in tokens:
			sstr,mstr,num,key,flow,ref,lit = token.groups()
			add = None
			error = None

			try:
				if lit:
					# Literals can either be the struct head (type and optionally name)
					# or a string that has no quotes.
					lit = lit.rstrip()
					# If the last token was a key or this is inside a list,
					#  this is string data
					if currentKey or adder: add = ("literal", lit)
					# Otherwise this might be a struct head
					else: lastLit = lit
				elif flow:
					if flow == "{":
						# Open struct
						structHead = lastLit.split(" ")
						lastLit = None

						if len(structHead) > 2:
							error = "Expects only type and name for struct declaration."
						elif currentKey is not None:
							error = 'Cannot have a struct in a key. (Did you mean "type %s {"?)' % currentKey
						# TODO: "Cannot have a struct in a data file."
						else:
							# Extract type and name
							structType = structHead[0]
							if structType not in counts: counts[structType] = 0
							else: counts[structType] += 1
							structName = (
								structHead[1] if len(structHead) == 2 else
								"%s%i" % (structType, counts[structType])
							)

							currentStruct = (
								currentStruct if currentStruct else self
							).addChild(structType, structName)
						#endif
					elif flow == "}":
						# Close struct
						if currentStruct is None: error = "} without a {."
						elif adder: error = "Unclosed list."
						elif currentKey is not None:
							error = "Key with no value. (Above here!)"
						#endif

						currentStruct.validate()
						currentStruct = currentStruct.parent()
					elif flow == "[":
						# Begins list
						adder.append([])
					elif flow == "]":
						# End list
						if adder: add = ("list", adder.pop())
						else: error = "] without a [."
					elif flow == ",":
						# Separator
						pass
					#endif
				elif key:
					if currentStruct is None or adder:
						error = "Key can only be in a struct."
					#endif

					currentKey = key
				elif ref: add = ("reference", RPLRef(self, ref, None))
				elif sstr: add = ("string", sstr)
				elif mstr:
					# Need to remove all `s
					add = ("string", String("".join(RPL.multilineStr.findall(mstr))))
				elif num:
					if not RPL.number.match(num):
						error = "Invalid range formatting."
					elif RPL.isRange.match(num):
						# Range
						numList = []
						ranges = num.split(":")

						for r in ranges:
							bounds = r.split("-")
							times = r.split("*")
							if len(bounds) == 2:
								l, r = int(bounds[0]), int(bounds[1])
								numList += map(lambda(x): ("number",x), (
									range(l, r+1) if l < r else range(l, r-1, -1)
								)
							elif len(times) == 2:
								l, r = int(times[0]), int(times[1])
								numList += map(lambda(x): ("number",x), [l] * r)
							elif r in "abcdefghijklmnopqrstuvwxyz":
								numList.append(("string", r))
							elif r[0] == "$": numList.append(("hexnum", int(r[1:], 16)))
							else: numList.append(("number", int(r)))
						#endfor

						add = ("range", numList)
					elif num[0] == "$":
						# Hexnum
						add = ("hexnum", int(num[1:], 16))
					else:
						# Number
						add = ("number", int(num))
					#endif
				# This is for whitespace, comments, etc. Things with no return.
				else: continue
			except RPLError(x): error = x

			if not lit and lastLit:
				error = "Literal with no purpose: %s" % lastLit
			#endif

			if add:
				dtype, val = add
				if type(val) is not list: nl, val = True, [val]
				else: nl = False
				map(lambda(x): self.wrap(x[0], x[1]), val)
				if nl: val = val[0]

				if adder:
					adder[-1].append(val)
				elif currentStruct and currentKey:
					currentStruct[currentKey] = val
					currentKey = None
				else:
					error = "Unused " + dtype
				#endif
			#endif

			if error:
				# Find the position
				pos = token.start()
				err("Error in line %i char %i: %s" % (
					raw.count("\n",0,pos), pos - raw.rfind("\n",0,pos),
					error
				)
				return False
			#endif
		#endfor
	#enddef

	def addChild(self, sType, name):
		"""
		Add a new struct to the root "element"
		"""
		if sType not in self.structs:
			raise RPLError("%s isn't allowed as a substruct of root." % sType)
		#endif
		new = self.structs[sType](self, name)
		self.root[name] = new
		return new
	#enddef

	def __unicode__(self):
		"""
		Write self as an RPL file.
		"""
	#enddef

	def regType(self, name, classRef):
		"""
		Method to register a custom type.
		"""
	#enddef

	def regStatic(self, name, value):
		"""
		Method to register a custom static variable. Use sparingly.
		"""
		self.static[name] = value
	#enddef

	def regStruct(self, name, classRef):
		"""
		Method to register a custom struct.
		"""
	#enddef

	def template(self, outFile):
		"""
		Output a basic RPL template
		"""
		outFile.write("ROM {}\n")
	#enddef

	def verify(self):
		"""
		Stub. You must replace this in your own things.
		Verifies that the selected ROM is the expected one according to the
		RPL's ROM field.
		"""
		return None
	#enddef

	def importData(self, rom, folder, what=[]):
		"""
		Import data from folder into the given ROM according to what.
		"""
	#enddef

	def exportData(self, rom, folder, what=[]):
		"""
		Export data from rom into folder according to what.
		"""
	#enddef

	def gfxTransform(image, info, direction):
		"""
		Transform a 2D image in typical ways
		"""
	#enddef

	def wrap(self, typeName, value):
		if typeName in self.types:
			return self.types[typeName](value)
	#enddef
#endclass

################################################################################
################################### RPLStruct ##################################
################################################################################
class RPLStruct:
	"""
	Base class for a struct
	"""

	# Be sure to define typeName here!

	def __init__(self, rpl, name, parent=None):
		"""
		Be sure to call this with:
		super(StructName,self).__init__(rpl, name)
		"""
		self.__rpl = rpl
		self.__name = name
		self.__parent = parent
		self.__data = {}
		self.__keys = {}
		self.__structs = {}
		self.__children = {}
	#enddef

	def addChild(self, sType, name):
		"""
		Add a new struct as a child of this one
		"""
		if sType not in self.__structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				sType, self.typeName
			))
		#endif
		new = self.__structs[sType](self.__rpl, name, self)
		self.__children[name] = new
		return new
	#enddef

	def parent(self): return self.__parent

	def regKey(self, name, basic, default=None):
		"""
		Register a key by name with type and default.
		"""
		if name not in self.__keys:
			self.__keys[name] = [basic, default]
			return True
		else: return False
	#enddef

	def validate(self):
		"""
		Validate self
		"""
		missingKeys = []
		for k,v in self.__keys.iteritems():
			if k not in self.__data:
				if v[1] is not None: self.__data[k] = v[1]
				else: missingKeys.append(k)
			#endif
		#endfor
		if missingKeys: raise RPLError("Missing keys: " + ", ".join(missingKeys))
		return True
	#enddef

	def __unicode__(self):
		"""
		Write struct to RPL format
		"""
	#enddef

	def __getitem__(self, key):
		"""
		Return data for key
		"""
		return self.__data[key]
	#enddef

	def __setitem__(self, key, value):
		"""
		Set data for key, verifying and casting as necessary
		"""
		if key in self.__keys:
			x = self.__keys[key]
			self.__data = self.__rpl.wrap(x[0], value)
		else: raise KeyError(key)
	#enddef

	def fromBin(self, key, value):
		"""
		Stub. Import data from binary representation instead.
		"""
		pass
	#enddef

	def basic(self):
		"""
		Stub. Return basic data (name by default)
		"""
		return self.__name
	#enddef
#endclass

class Static(RPLStruct):
	"""
	A generic struct that accepts all keys. Used to store static information.
	Does not import or export anything.
	"""

	typeName = "static"

	def __init__(self, rpl, name):
		"""Honestly, this is just an example."""
		super(Static,self).__init__(rpl, name)
	#enddef

	def verify(self):
		"""Overwrite this cause Static accepts all keys"""
		return True
	#enddef

	def __setitem__(self, key, value):
		"""Overwrite this cause Static accepts all keys"""
		self.__data[key] = value
	#enddef
#endclass

################################################################################
#################################### RPLRef ####################################
################################################################################
class RPLRef:
	"""
	Manages references to other fields
	"""

	spec = re.compile(r'@?([^.]+)(?:\.([^\[]*))?((?:\[[0-9]+\])*)')
	heir = re.compile(r'(g*)parent')

	def __init__(self, rpl, ref, pos):
		self.__rpl = rpl
		self.__pos = pos

		self.__struct, self.__key, idxs = self.spec.match(ref).groups()
		if idxs: self.__idxs = map(int, idxs[1:-1].split("]["))
		else: self.__idxs = []
	#enddef

	def __unicode__(self):
		"""Output ref to RPL format"""
		ret = "@%s" % self.__struct
		if self.__key: ret += "."+self.__key
		if self.__idxs: ret += "[%s]" % "][".join(self.__idxs)
		return ret
	#enddef
#endclass

################################################################################
#################################### RPLData ###################################
################################################################################

class RPLData:
	def __init__(self, data): self.set(data)
	def get(self): return self.__data
	def set(self, data): return self.__data = data
#endclass

class String(RPLData):
	"""String basic type"""
	escape = re.compile(r'$($|[0-9a-fA-F]{2})')
	binchr = re.compile(r'[\x00-\x08\x0a-\x1f\x7f-\xff]')
	def set(self, data):
		if type(data) is str: data = unicode(data)
		elif type(data) is not unicode:
			raise TypeError('Type "string" expects unicode or str.')
		#endif
		self.__data = String.escape.sub(String.replIn, data)
	#enddef

	def __unicode__(self):
		return '"' + String.binchr.sub(String.replOut, self.__data) + '"'
	#enddef

	@staticmethod
	def replIn(mo):
		if mo.group(1) == "$": return "$"
		else: return unichr(int(mo.group(1), 16))
	#enddef

	@staticmethod
	def replOut(mo):
		if mo.group(0) == "$": return "$$"
		else: return "$%02x" % ord(mo.group(0))
	#enddef
#endclass

class Number(RPLData):
	"""Number basic type"""
	def set(self, data):
		if type(data) not in [int, long]:
			raise TypeError('Type "number" expects int or long.')
		#endif
		self.__data = data
	#enddef

	def __unicode__(self): return str(self.__data)
#endclass

class HexNum(Number):
	"""HexNum interpreted type"""
	def __unicode__(self): return "$%x" % self.__data
#endclass

class List(RPLData):
	"""List basic type"""
	def set(self, data):
		if type(data) is not list:
			raise TypeError('Type "list" expects list.')
		#endif
		self.__data = data
	#enddef

	def __unicode__(self):
		return "[ " + ", ".join(map(unicode, self.__data)) + " ]"
	#enddef
#enclass

class Range(List):
	"""Range interpreted type"""
	pass
#endclass
