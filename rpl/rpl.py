import re
import codecs
from copy import deepcopy
#from textwrap import dedent

class RPL:
	"""
	The base type for loading and interpreting RPL files.
	Also handles "execution" and what not.
	"""

	# Constants
	tokenize = re.compile(
		(r'\s*(?:'                                 # Whitespace
		+r'"([^"\r\n]*)"|'                         # String
		# Have to remove `s in postprocessing
		+r'((?:`(?:\\.|[^`])*`\s*)+)|'             # Multi-line String
		+r'\$([0-9a-fA-F]+)(?![0-9a-fA-F]*[\-:])|' # Hexadecimal number
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
		tokens = self.tokenize.findall(self.readFrom(inFile))

		for token in tokens:
		#endfor
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

	def __init__(self, rpl, name):
		"""
		Be sure to call this with:
		super(StructName,self).__init__(rpl, name)
		"""
		self.__rpl = rpl
		self.__name = name
		self.__data = {}
		self.__keys = {}
	#enddef

	def regKey(self, name, basic, default=None):
		"""
		Register a key by name with type and default.
		"""
		if name not in self.__keys:
			self.__keys[name] = [basic, default]
			return True
		else: return False
	#enddef

	def parse(self, obj):
		"""
		Parse object, verifying entries
		"""
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
			self.__data =self.__rpl.wrap(x[0], value)
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
	def __init__(self, rpl, name):
		"""Honestly, this is just an example."""
		super(Static,self).__init__(rpl, name)
	#enddef

	def parse(self, obj):
		"""Overwrite this cause Static accepts all keys"""
		self.__data = deepcopy(obj)
	#enddef

	def __setitem__(self, key, value):
		"""Overwrite this cause Static accepts all keys"""
		self.__data[key] = value
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
