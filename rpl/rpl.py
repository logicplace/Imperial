import re
import codecs
from sys import stderr
import os

# TODO:
#  * RPLRef issues:
#    * @back
#  * Make TypeChecking standardize []*?

def err(msg): stderr.write(unicode(msg) + u"\n")

class RPLError(Exception): pass

class RPL:
	"""
	The base type for loading and interpreting RPL files.
	Also handles "execution" and what not.
	"""

	# Constants
	tokenize = re.compile(
		(r'\s*(?:'                                # Whitespace
		r'"([^"\r\n]*)"|'r"'([^'\r\n]*)'|"         # String
		# Have to remove `s in processing
		r'((?:\s*`[^`]*`\s*(?:#.*)?)+)|'          # Multi-line String
		# Number or range (verify syntactically correct range later)
		r'(%(r1)s%(r2)s%(r1)s:\-*%(r2)s*(?=[ ,]|$))|'
		r'(%(key)s):|'                            # Key
		r'([{}\[\],])|'                           # Flow Identifier
		r'@([^%(lit)s.]+(?:\.%(key)s)?(?:\[[0-9]+\])*)|' # Reference
		r'([^%(lit)s]+)|'                         # Unquoted string or struct name/type
		r'#.*$)'                                  # Comment
		) % {
			"r1": r'(?:[0-9',
			"r2": r']|(?<![a-zA-Z])[a-z](?![a-zA-Z])|\$[0-9a-fA-F]+)',
			"lit": r'{}\[\],\$@"#\r\n' r"'",
			"key": r'[a-z]+[0-9]*'
		}
	, re.M | re.U)

	multilineStr = re.compile(r'`([^`]*)`\s*(?:#.*)?')

	number = re.compile(
		# Must start with a number, or a single letter followed by a :
		(r'(?:%(numx)s|[a-z](?=:))'
		# Range split group
		+r'(?:'
		# Can match a range or times here
		+r'(?:%(bin)s(%(numx)s))?'
		# Must match a split, can either be a number or single letter followed by a :
		+r':(?:%(numx)s|[a-z](?=[: ]|$))'
		+r')*'
		# To be sure we're able to end in a range/times
		+r'(?:%(bin)s(?:%(numx)s))?'
		) % {
			'bin': r'[\-*]'
			,'numx': r'[0-9]+|\$[0-9a-fA-F]+'
		}
	)
	isRange = re.compile(r'.*[:\-*].*')

	def __init__(self):
		"""Be sure to call this!"""
		self.static = {}
		self.types = {}
		self.structs = {}
		self.root = {}
		self.structsByName = {}

		# Registrations
		self.regStruct(Static)
		self.regType(String)
		self.regType(Literal)
		self.regType(Number)
		self.regType(HexNum)
		self.regType(List)
		self.regType(Range)

		for k,v in {
			 "false":   "0"
			,"true":    "1"
			,"black":   "$000000"
			,"white":   "$ffffff"
			,"red":     "$ff0000"
			,"blue":    "$00ff00"
			,"green":   "$0000ff"
			,"yellow":  "$ffff00"
			,"magenta": "$ff00ff"
			,"pink":    "$ff00ff"
			,"cyan":    "$00ffff"
			,"gray":    "$a5a5a5"
			,"byte":    "1"
			,"short":   "2"
			,"long":    "4"
			,"double":  "8"
			,"LU":      "LRUD"
			,"LD":      "LRDU"
			,"RU":      "RLUD"
			,"RD":      "RLDU"
			,"UL":      "UDLR"
			,"UR":      "UDRL"
			,"DL":      "DULR"
			,"DR":      "DURL"
		}.iteritems(): self.regStatic(k, v)
	#enddef

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

		lastLit = None
		currentKey = None
		currentStruct = None
		counts = {}
		adder = []

		for token in RPL.tokenize.finditer(raw):
			groups = token.groups() # Used later
			dstr,sstr,mstr,num,key,flow,ref,lit = groups
			sstr = dstr or sstr # Double or single
			add, error, skipSubInst = None, None, False

			# Find the position (used for ref and errors)
			pos = token.start()
			line, char = raw.count("\n",0,pos) + 1, pos - raw.rfind("\n",0,pos) + 1

			try:
				if lit:
					# Literals can either be the struct head (type and optionally name)
					# or a string that has no quotes.
					lit = lit.rstrip()
					# If the last token was a key or this is inside a list,
					#  this is string data
					if currentKey or adder: add = self.parseData(groups)
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
							counts[structType] = counts.get(structType, -1) + 1
							if len(structHead) >= 2: structName, genned = structHead[1], False
							else:
								# Form name from type + incrimenter
								# NOTE: There must be a prettier way to do this!
								structName = "%s%i" % (structType, counts[structType])
								while structName in self.structsByName:
									counts[structType] += 1
									structName = "%s%i" % (structType, counts[structType])
								#endwhile
								genned = True
							#endif

							if structName in self.structsByName:
								error = 'Struct name "%s" is already taken' % structName
							else:
								self.structsByName[structName] = currentStruct = (
									currentStruct if currentStruct else self
								).addChild(structType, structName)
								currentStruct._gennedName = genned
							#endif
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
						if adder:
							add = ("list", adder.pop())
							skipSubInst = True
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
				elif sstr or mstr or num or ref:
					add = self.parseData(groups, currentStruct, currentKey, line, char)
				# This is for whitespace, comments, etc. Things with no return.
				else: continue
			except RPLError as x: error = x.args[0]

			if not lit and lastLit:
				error = "Literal with no purpose: %s" % lastLit
			#endif

			if add:
				if type(add) is tuple:
					add = self.parseCreate(add, currentStruct, currentKey, line, char, skipSubInst)
				dtype, val = add.typeName, add # For statics

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
				err("Error in line %i char %i: %s" % (
					line, char, error
				))
				return False
			#endif
		#endfor
	#enddef

	def parseCreate(self, add, currentStruct, currentKey, line, char, skipSubInst=False):
		"""Instantiates data. Used by parse and parseData"""
		dtype, val = add

		# Special handler for references (cause they're so speeshul)
		if dtype == "reference":
			val = RPLRef(self, currentStruct, currentKey, val, line, char)
		elif skipSubInst: val = self.wrap(*add)
		else:
			if type(val) is not list: nl, val = True, [add]
			else: nl = False
			val = map(lambda(x): self.wrap(*x), val)
			if nl: val = val[0]
			else: val = self.wrap(dtype, val)
		#endif

		return val
	#enddef

	def parseData(self, data, currentStruct=None, currentKey=None, line=-1, char=-1):
		"""Parse one value"""
		pp = type(data) is tuple
		if pp: dstr,sstr,mstr,num,key,flow,ref,lit = data
		else:
			try: dstr,sstr,mstr,num,key,flow,ref,lit = self.tokenize.match(data).groups()
			except AttributeError: raise RPLError("Syntax error in data: %s" % data)
		#endif
		sstr = dstr or sstr

		add, error = None, None

		if ref: add = ("reference", ref)
		elif sstr: add = ("string", sstr)
		elif mstr:
			# Need to remove all `s
			add = ("string", "".join(RPL.multilineStr.findall(mstr)))
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
						))
					elif len(times) == 2:
						l, r = int(times[0]), int(times[1])
						numList += map(lambda(x): ("number",x), [l] * r)
					elif r in "abcdefghijklmnopqrstuvwxyz":
						numList.append(("literal", r))
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
		elif lit or (type(data) is str and data == ""):
			if lit in self.static: add = self.static[lit]
			else: add = ("literal", lit.strip())
		elif pp: raise RPLError("Invalid data.")
		else: raise RPLError("Invalid data: %s" % data)

		if add and pp: return add
		elif add and type(add) is not tuple: return add
		elif add: return self.parseCreate(add, currentStruct, currentKey, line, char)
		elif error: raise RPLError(error)
		elif pp: raise RPLError("Error parsing data.")
		else: raise RPLError("Error parsing data: %s" % data)
	#endif

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

	def regType(self, classRef):
		"""
		Method to register a custom type.
		"""
		self.types[classRef.typeName] = classRef
	#enddef

	def regStatic(self, name, value):
		"""
		Method to register a custom static variable. Use sparingly.
		"""
		self.static[name] = self.parseData(value)
	#enddef

	def regStruct(self, classRef):
		"""
		Method to register a custom struct.
		"""
		self.structs[classRef.typeName] = classRef
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

	def wantPort(self, x, what):
		return x and (not what or x.name() in what or wantPort(x.parent(), what))
	#enddef

	def importData(self, rom, folder, what=[]):
		"""
		Import data from folder into the given ROM according to what.
		"""
		rom = self.readFrom(rom)
		lfolder = os.path.split(os.path.normpath(folder))
		for x in self:
			if wantPort(x, what) and x["import"]: x.importData(rom, lfolder)
		#endfor
	#enddef

	def exportData(self, rom, folder, what=[]):
		"""
		Export data from rom into folder according to what.
		"""
		rom = self.readFrom(rom)
		lfolder = os.path.split(os.path.normpath(folder))
		for x in self:
			if wantPort(x, what) and x["export"]: x.exportData(rom, lfolder)
		#endfor
	#enddef

	def wrap(self, typeName, value):
		if typeName in self.types:
			return self.types[typeName](value)
		else: raise RPLError('No type "%s" defined' % typeName)
	#enddef

	def child(self, name): return self.root[name]
	def __iter__(self): return self.root.itervalues()
#endclass

################################################################################
################################# RPLTypeCheck #################################
################################################################################
class RPLTypeCheck:
	"""
	Checks a RPLData struct against a set of possibilities.
	The passed syntax is as follows:
	 * type - Type name
	 * all - Any type allowed
	 * [type, ...] - List containing specific types
	 * | - Boolean or
	 * []* - Can either be just the contents, or a list containing multiple
	         of that content. Multipart lists treat commas like |
	 * []+ - Contents may be repeated indefinitely within the list.
	 * []! - May be any one of the contents not in a list, or the whole list.
	 *       ie. Like * but unable to repeat the list.
	 * []~ - Nonnormalizing form of []*
	 * []. - Nonnormalizing form of []!
	 * ^   - Recurse parent list at this point
	"""

	tokenize = re.compile(r'\s+|([\[\]*+!~.|,])|([^\s\[\]*+!~.|,^]+|\^)')

	def __init__(self, rpl, name, syntax):
		"""
		FYI: This is one of the most ridiculous looking parsers I've written
		"""
		lastType = None
		remain = None
		parents = []
		lastWasListEnd, lastWasRep = False, False
		for token in RPLTypeCheck.tokenize.finditer(syntax):
			try:
				flow, tName = token.groups()

				if tName: lastType = RPLTCData(rpl, tName)
				elif flow == "[":
					if lastType is None:
						# New list, append to list/parents
						tmp = ["list",[]]
						if len(parents): parents[-1][1].append(tmp)
						parents.append(tmp)
					else: raise RPLError("Unused type.")
				elif flow == "]":
					if lastType:
						parents[-1][1].append(lastType)
						lastType = None
					#endif

					try:
						if parents[-1][0] == "or":
							# `.pop()` > `[-1] =`
							parents[-1][1][-1] = RPLTCOr(parents.pop()[1])
						#endif
						remain = RPLTCList(parents.pop()[1])
						if len(parents): parents[-1][1][-1] = remain
					except IndexError: raise RPLError("] without [")
					lastWasListEnd = True
				elif flow and flow in "*+!~.":
					if lastWasListEnd: remain.rep(flow)
					else: raise RPLError("Repeater out of place.")
					lastWasRep = True
				elif flow == "|":
					if lastWasListEnd or lastWasRep:
						# If the list was the first part of this OR sequence
						# then it will be in remain and parents[-1][1][-1] if
						# len(parents). parents[-1][0] == "list" in this case.
						# If the list was in the middle the same is true above
						# but parents[-1][0] == "or", so nothing needs to be done
						tmp = ["or",[remain]]
						if not len(parents): parents.append(tmp)
						elif parents[-1][0] == "list":
							parents[-1][1][-1] = tmp
							parents.append(tmp)
						#endif
					elif len(parents) and parents[-1][0] == "or":
						parents[-1][1].append(lastType)
					else:
						# New OR, append to list/parents
						tmp = ["or",[lastType]]
						if len(parents): parents[-1][1].append(tmp)
						parents.append(tmp)
					#endif
					lastType = None
				elif flow == ",":
					try:
						if lastType:
							parents[-1][1].append(lastType)
							lastType = None
						#endif
						if parents[-1][0] == "or":
							# `.pop()` > `[-1] =`
							parents[-1][1][-1] = RPLTCOr(parents.pop()[1])
						#endif
					except IndexError:
						raise RPLError("Comma only allowed in lists")
					#endtry
				#endif

				if flow != "]": lastWasListEnd = False
				if not flow or flow not in "*+!~.": lastWasRep = False
			except RPLError as x:
				raise RPLError('Key "%s" Char %i: %s' % (
					name, token.start(), x.args[0]
				))
			#endtry
		#endfor
		if len(parents):
			if lastType: parents[-1][1].append(lastType)
			if parents[0][0] == "or": self.__root = RPLTCOr(parents[0][1])
			else: raise RPLError('Key "%s": Unclosed lists.' % name)
		elif lastType: self.__root = lastType
		elif remain: self.__root = remain
		else: raise RPLError('Key "%s": I did nothing!' % name)
	#enddef

	def verify(self, data): return self.__root.verify(data)
#endclass

class RPLTCData:
	"""Helper class for RPLTypeCheck, contains one type"""
	def __init__(self, rpl, t): self.__rpl, self.__type = rpl, t

	# Starting to feel like I'm overdoing this class stuff :3
	def verify(self, data, parentList=None):
		if self.__type == "^":
			if parentList is not None:
				return parentList.verify(data, parentList)
			else: return None
		elif (self.__type == "all"
			or isinstance(data, self.__rpl.types[self.__type])
		): return data
		elif issubclass(self.__rpl.types[self.__type], data.__class__):
			# Attempt to recast to subclass
			try: return self.__rpl.types[self.__type](data.get())
			except RPLError: return None
		else: return None
	#enddef
#endclass

class RPLTCList:
	"""Helper class for RPLTypeCheck, contains one list"""
	def __init__(self, l, r="]"): self.__list, self.__repeat = l,r
	def rep(self, r): self.__repeat = r

	def verify(self, data, parentList=None):
		# Make sure data is a list (unless repeat is * or !)
		if not isinstance(data, List):
			if self.__repeat in "*!~.":
				# This seems like strange form but it's the only logical form
				# in my mind. This implies [A,B]* is A|B|[A,B]+ Using * on a
				# multipart list is a little odd to begin with.
				for x in self.__list:
					tmp = x.verify(data)
					if tmp is not None:
						if self.__repeat in "*!": return List([tmp])
						else: return tmp
					#endif
				#endfor
			else: return None
		#endif

		# Check lengths
		d = data.get()
		if self.__repeat in "+*":
			if len(d) % len(self.__list): return None
		elif len(d) != len(self.__list): return None

		# Loop through list contents to check them all
		nd = []
		for i,x in enumerate(self.__list):
			# This conditional should prevent infinite recursion.
			nd.append(x.verify(d[i], self if parentList != self else None))
			if nd[-1] is None: return None
		#endfor

		if d != nd: return List(nd)
		else: return data
	#enddef
#endclass

class RPLTCOr:
	"""Helper class for RPLTypeCheck, contains one OR set"""
	def __init__(self, orSet): self.__or = orSet

	def verify(self, data, parentList=None):
		for x in self.__or:
			tmp = x.verify(data, parentList)
			if tmp is not None: return tmp
		#endfor
		return None
	#enddef
#endclass

################################################################################
################################### RPLStruct ##################################
################################################################################
class RPLStruct(object):
	"""Base class for a struct"""

	# Be sure to define typeName here!

	def __init__(self, rpl, name, parent=None):
		"""Be sure to call this in your own subclasses!"""
		self._rpl = rpl
		self._name = name
		self._parent = parent
		self._data = {}
		self._keys = {}
		self._structs = {}
		self._children = {}

		try: self.typeName
		except AttributeError: self.typeName = self.__class__.__name__.lower()
	#enddef

	def addChild(self, sType, name):
		"""Add a new struct as a child of this one"""
		if sType not in self._structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				sType, self.typeName
			))
		#endif
		new = self._structs[sType](self._rpl, name, self)
		self._children[name] = new
		return new
	#enddef

	def regKey(self, name, basic, default=None):
		"""Register a key by name with type and default."""
		self._keys[name] = [RPLTypeCheck(basic), default]
	#enddef

	def regStruct(self, classRef):
		"""
		Method to register a custom struct.
		"""
		self._structs[classRef.typeName] = classRef
	#enddef

	def validate(self):
		"""Validate self"""
		missingKeys = []
		for k,v in self._keys.iteritems():
			if k not in self._data:
				# Should this wrap? Or verify? Or should the definers have to do that?
				if v[1] is not None: self._data[k] = v[1]
				else: missingKeys.append(k)
			#endif
		#endfor
		if missingKeys: raise RPLError("Missing keys: " + ", ".join(missingKeys))
		return True
	#enddef

	def __unicode__(self):
		"""Write struct to RPL format"""
	#enddef

	def __getitem__(self, key):
		"""Return data for key"""
		x = self
		while x and key not in x._data: x = x.parent()
		if x: return x._data[key]
		else: raise RPLError('No key "%s"' % key)
	#enddef

	def __setitem__(self, key, value):
		"""Set data for key, verifying and casting as necessary"""
		if key in self._keys:
			# Reference's types are lazily checked
			if isinstance(value, RPLRef): self._data[key] = value
			else: self._data[key] = self._keys[key][0].verify(value)
		else: raise RPLError('"%s" has no key "%s".' % (self.typeName, key))
	#enddef

	def name(self): return self._name
	def parent(self): return self._parent

	def basic(self, callers=[]):
		"""Stub. Return basic data (name by default)"""
		return Literal(self._name)
	#enddef

	def __len__(self):
		"""Return number of children (including keys)"""
		return len(self._data) + len(self._children)
	#enddef

	def __nonzero__(self): return True
	def child(self, name): return self._children[name]
	def __iter__(self): return self._children.itervalues()
#endclass

class Static(RPLStruct):
	"""
	A generic struct that accepts all keys. Used to store static information.
	Does not import or export anything.
	"""

	typeName = "static"

	def __init__(self, rpl, name, parent=None):
		"""Honestly, this is just an example."""
		RPLStruct.__init__(self, rpl, name, parent)
	#enddef

	def addChild(self, sType, name):
		"""Overwrite this cause Static accepts all root children"""
		if sType not in self._rpl.structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				sType, self.typeName
			))
		#endif
		new = self._rpl.structs[sType](self._rpl, name, self)
		self._children[name] = new
		return new
	#enddef

	def verify(self):
		"""Overwrite this cause Static accepts all keys"""
		return True
	#enddef

	def __setitem__(self, key, value):
		"""Overwrite this cause Static accepts all keys"""
		self._data[key] = value
	#enddef
#endclass

class Serializable(RPLStruct):
	"""Inherit this class for data that can be imported and/or exported"""

	# NOTE: There is no typeName because this is not meant to be used directly.

	def __init__(self, rpl, name, parent=None):
		"""Register self"""
		RPLStruct.__init__(self, rpl, name, parent)
		self.regKey("base", "hexnum", "$000000")
		self.regKey("file", "string", '""')
		self.regKey("ext", "string", '""')
		self.regKey("export", "number", "true")
		self.regKey("import", "number", "true")
	#enddef

	def open(self, folder, ext="bin", retName=False, justOpen=False):
		"""Helper method for opening files"""
		if not justOpen:
			if type(folder) is not list: folder = os.path.split(os.path.normpath(folder))

			# Function to return defined filename or struct's defined name
			# If the filename starts with a / it is considered a subdir of parent
			# structs.
			def fn(x):
				if "file" in x._data:
					f = os.path.normpath(x._data["file"].get())
					if f[0:len(os.sep)] == os.sep: return (True, os.path.split(f[len(os.sep):]))
					else: return (False, os.path.split(f))
				else: return (True, None if x._gennedName else [x.name()])
			#enddef

			# Create the filename with extension
			cont, f = fn(self)
			if os.extsep in f: path = f
			else: path = f[0:-1] + ["%s%s%s" % (f[-1], os.extsep, self["ext"] or ext)]

			# Traverse parents for directory structure while requested
			x = self.parent()
			while cont and x:
				cont, name = fn(x)
				if name: path = name + path
				x = x.parent()
			#endwhile

			# Finalize path, make directories
			path = os.path.normpath(os.path.join(*(folder + path)))
			try: os.makedirs(os.path.dirname(path))
			except os.error: pass

			# Return requested thing (path or handle)
			if retName: return path
		else: path = folder
		return codecs.open(path, encoding="utf-8", mode="r+")
	#enddef

	def close(self, handle):
		"""Helper method for closing files"""
		try: handle.close()
		except AttributeError: del handle
	#enddef

	def importData(self, rom, folder):
		"""Stub. Fill this in to import appriately"""
		pass
	#enddef

	def exportData(self, rom, folder):
		"""Stub. Fill this in to export appriately"""
		pass
	#enddef
#endclass

################################################################################
#################################### RPLRef ####################################
################################################################################
class RPLRef:
	"""Manages references to other fields"""

	spec = re.compile(r'@?([^.]+)(?:\.([^\[]*))?((?:\[[0-9]+\])*)')
	heir = re.compile(r'^(?=.)((w*)back_?)?((g*)parent)?$')

	typeName = "reference"

	def __init__(self, rpl, container, mykey, ref, line, char):
		self.__rpl = rpl
		self.__container = container
		self.__mykey = mykey
		self.__pos = (line, char)

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

	def get(self, callers=[], retCl=False):
		"""Return referenced value"""
		# When a reference is made, this function should know what struct made
		#  the reference ("this", ie. self.__container) BUT also the chain of
		#  references up to this point..
		# First check if we're referring to self or referrer and/or parents
		heir = RPLRef.heir.match(self.__struct)
		if self.__struct == "this" or heir:
			if self.__container is None or self.__mykey is None:
				raise RPLError("Cannot use relative references in data form.")
			#endif
			# Referrer history
			if heir and heir.group(1):
				try: ret = callers[-1 - len(heir.group(2))]
				except IndexError: raise RPLError("No %s." % self.__struct)
			# "this" or parents only
			else: ret = self.__container
			# "parent"
			if heir and heir.group(3):
				ret = ret.parent()
				# The gs (great/grand) in g*parent
				for g in heir.group(4):
					try: ret = ret.parent()
					except Exception as x:
						if ret is not None: raise x
					#endtry
					if ret is None: raise RPLError("No %s." % self.__struct)
				#endfor
			#endif
		else: ret = self.__rpl.structsByName[self.__struct]

		if not self.__key: ret = ret.basic()
		else: ret = ret[self.__key]
		callersAndSelf = callers + [self]
		for i,x in enumerate(self.__idxs):
			try:
				if isinstance(ret, RPLRef): ret = ret.get(callersAndSelf)[x]
				else: ret = ret.get()[x]
			except IndexError:
				raise RPLError("List not deep enough. Failed on %ith index." % i)
			#endtry
		#endfor

		if isinstance(ret, RPLRef): ret = ret.get(callersAndSelf, True)

		# Verify type
		if (self.__container is not None and self.__mykey is not None
		and self.__mykey in self.__container._keys):
			ret = self.__container._keys[self.__mykey][0].verify(data)
		#endif

		if retCl: return ret
		else: return ret.get()
		#endif
	#endif
#endclass

################################################################################
#################################### RPLData ###################################
################################################################################

class RPLData(object):
	def __init__(self, data): self.set(data)
	def get(self): return self._data
	def set(self, data): self._data = data

	#def defaultSize(self)       # Returns default size for use by Data struct
	#def serialize(self, **opts)         # Return binary form of own data.
	#def unserialize(self, data, **opts) # Parse binary data and set to self.

	def __eq__(self, data):
		"""Compare data contained in objects)"""
		if not isinstance(data, RPLData): data = RPL.parseData(RPL(), data)
		if isinstance(self, data.__class__) or isinstance(data, self.__class__):
			d1, d2 = self.get(), data.get()
			if type(d1) is list and type(d2) is list:
				if len(d1) != len(d2): return False
				for i,x in enumerate(d1):
					if not RPLData.__eq__(x, d2[i]): return False
				#endfor
				return True
			#endif
			return d1 == d2
		else: return False
	#enddef
#endclass

class String(RPLData):
	"""String basic type"""
	typeName = "string"

	escape = re.compile(r'\$(\$|[0-9a-fA-F]{2})')
	binchr = re.compile(r'[\x00-\x08\x0a-\x1f\x7f-\xff]')
	def set(self, data):
		if type(data) is str: data = unicode(data)
		elif type(data) is not unicode:
			raise RPLError('Type "%s" expects unicode or str.' % self.typeName)
		#endif
		self._data = String.escape.sub(String.replIn, data)
	#enddef

	def __unicode__(self):
		return '"' + String.binchr.sub(String.replOut, self._data) + '"'
	#enddef

	def serialize(self): return self._data.encode("utf8")
	def unserialize(self, data): self._data = data.decode("utf8")

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

class Literal(String):
	"""Literal basic type"""
	typeName = "literal"

	def __unicode__(self):
		return String.binchr.sub(String.replOut, self._data)
	#enddef
#endclass

class Number(RPLData):
	"""Number basic type"""
	typeName = "number"

	def set(self, data):
		if type(data) not in [int, long]:
			raise RPLError('Type "%s" expects int or long.'  % self.typeName)
		#endif
		self._data = data
	#enddef

	def __unicode__(self): return str(self._data)

	def defaultSize(self): return 4
	def serialize(self, **opts):
		big, ander, ret = (opts["endian"] == "big"), 0xff, r''
		for i in range(opts["size"]):
			c = chr(self._data & ander >> ((i-1)*8))
			if big: ret = c + ret
			else: ret += c
			ander <<= 8
		#endfor
		return ret
	#enddef
	def unserialize(self, data, **opts):
		big = (opts["endian"] == "big")
		size = len(data)
		self._data = 0
		for i,x in enumerate(data):
			if big: shift = size-i+1
			else: shift = i-1
			self._data |= ord(x) << (shift*8)
		#endfor
	#enddef
#endclass

class HexNum(Number):
	"""HexNum interpreted type"""
	typeName = "hexnum"

	def __unicode__(self): return "$%x" % self._data
#endclass

class List(RPLData):
	"""List basic type"""
	typeName = "list"

	def set(self, data):
		if type(data) is not list:
			raise RPLError('Type "%s" expects list.' % self.typeName)
		#endif
		self._data = data
	#enddef

	def __unicode__(self):
		return "[ " + ", ".join(map(unicode, self._data)) + " ]"
	#enddef
#enclass

class Range(List):
	"""Range interpreted type"""
	typeName = "range"

	def set(self, data):
		if type(data) is not list:
			raise TypeError('Type "%s" expects list.' % self.typeName)
		#endif
		for x in data:
			if not isinstance(x, Number) and (not isinstance(x, Literal)
			or len(x.get()) != 1):
				raise RPLError('Types in a "%s" must be a number or one character literal' % self.typeName)
			#endif
		#endfor
		self._data = data
	#enddef

	def __unicode__(self):
		ret, posseq, negseq, mul, last = [], [], [], [], None
		for x in self._data:
			d = x.get()
			if isinstance(x, Literal): ret.append(d)
			elif last is None: last = d
			else:
				isPos = (d - last == 1)
				isNeg = (last - d == 1)
				isSame = (last == d)
				if not isNeg and negseq:
					ret.append("%i-%i" % (negseq[0], negseq[-1]))
					negseq = []
				if not isPos and posseq:
					ret.append("%i-%i" % (posseq[0], posseq[-1]))
					posseq = []
				if not isSame and mul:
					ret.append("%i*%i" % (mul[0], len(mul)))
					mul = []
				#endif
				if isPos: posseq.append(d)
				elif isNeg: negseq.append(d)
				elif isSame: mul.append(d)
				else: ret.append(unicode(d))
			#endif
		#endfor
		return ":".join(ret)
	#enddef
#endclass

