import re
import codecs
from sys import stderr
import os
from math import ceil
import copy
import helper

# TODO:
#  * RPLRef issues:
#    * @back (maybe?)
#  * T) Serializers that modify the same file need to compound.
#    Therefore, make a system in which structs request the handler/data to
#    modify, which will open the file and read it if it's the first, but
#    otherwise return the already loaded/modified data to be further modified.
#  * Add referencing multiline strs with @` ` form.

def err(msg): stderr.write(unicode(msg) + "\n")

class RPLError(Exception): pass

class RPL(object):
	"""
	The base type for loading and interpreting RPL files.
	Also handles "execution" and what not.
	"""

	# Constants
	tokenize = re.compile(
		# Whitespace
		(r'\s*(?:'
		 # String: Either "etc" or 'etc' no linebreaks inside
		 r'"([^"\r\n]*)"|'r"'([^'\r\n]*)'|"
		 # Multi-line String: Matches `etc` but multiple in a row
		 # NOTE: This picks up comments and the ` themselves so have to
		 # remove those in processing.
		 r'((?:\s*`[^`]*`\s*(?:#.*)?)+)|'
		 # Number or range (verify syntactically correct range later)
		 # That is, any string of numbers, -, *, :, or :c: where c is one
		 # lowercase letter.
		 r'(%(r1)s%(r2)s%(r1)s:\-*%(r2)s*(?=[ ,]|$))|'
		 # Key: Lowercase letters optionally followed by numbers.
		 # Must be followed by a colon.
		 r'(%(key)s):([ \t]*)|'
		 # Flow Identifier: One of: {}[],
		 r'([{}\[\],])|'
		 # Reference: @StructName.keyname[#][#][#] keyname and indexes are
		 # optional. Can have infinite indexes, but only one keyname.
		 r'@([^%(lit)s.]+(?:\.%(key)s)?(?:\[[0-9]+\])*)|'
		 # Literal: Unquoted string or struct name/type
		 r'([^%(lit)s]+)|'
		 # Comment
		 r'#.*$)'
		) % {
			# Range part 1
			"r1": r'(?:[0-9',
			# Range part 2
			"r2": r']|(?<![a-zA-Z])[a-z](?![a-zA-Z])|\$[0-9a-fA-F]+)',
			# Invalid characters for a Literal
			"lit": r'{}\[\],\$@"#\r\n' r"'",
			# Valid key name
			"key": r'[a-z]+[0-9]*'
		}
	, re.M | re.U)

	multilineStr = re.compile(r'`([^`]*)`\s*(?:#.*)?')

	# For numbers (number and hexnum) and ranges
	number = re.compile(
		# Must start with a number, or a single letter followed by a :
		(r'(?:%(num)s|[a-z](?=:))'
		 # Range split group
		 r'(?:'
		 # Can match a range or times here
		 r'(?:%(bin)s(%(num)s))?'
		 # Must match a split, can either be a number or single letter followed by a :
		 r':(?:%(num)s|[a-z](?=[: ]|$))'
		 r')*'
		 # To be sure we're able to end in a range/times
		 r'(?:%(bin)s(?:%(num)s))?'
		) % {
			# Binary operators
			"bin": r'[\-*]',
			# Valid forms for a number
			"num": r'[0-9]+|\$[0-9a-fA-F]+'
		}
	)
	# Quick check for if a number is a range or not
	isRange = re.compile(r'[:\-*]')

	_statics = {
		"false":   "0",
		"true":    "1",
		"black":   "$000000",
		"white":   "$ffffff",
		"red":     "$ff0000",
		"blue":    "$00ff00",
		"green":   "$0000ff",
		"yellow":  "$ffff00",
		"magenta": "$ff00ff",
		"pink":    "$ff00ff",
		"cyan":    "$00ffff",
		"gray":    "$a5a5a5",
		"byte":    "1",
		"short":   "2",
		"long":    "4",
		"double":  "8",
		"LU":      "LRUD",
		"LD":      "LRDU",
		"RU":      "RLUD",
		"RD":      "RLDU",
		"UL":      "UDLR",
		"UR":      "UDRL",
		"DL":      "DULR",
		"DR":      "DURL",
	}

	def __init__(self):
		# Be sure to call this!
		self.static = {}
		self.types = {}
		self.structs = {}
		self.root = {}
		self.orderedRoot = []
		self.structsByName = {}
		self.sharedDataHandlers = {}
		self.importing = None

		# Registrations
		self.regStruct(Static)
		self.regType(String)
		self.regType(Literal)
		self.regType(Number)
		self.regType(HexNum)
		self.regType(List)
		self.regType(Range)

		for k,v in RPL._statics.iteritems(): self.regStatic(k, v)
	#enddef

	def parse(self, inFile):
		"""
		Read in a file and parse it.
		"""
		raw = helper.readFrom(inFile)

		lastLit, prelit = None, ""
		currentKey = None
		currentStruct = None
		counts = {}
		adder = []

		for token in RPL.tokenize.finditer(raw):
			groups = token.groups() # Used later
			dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = groups
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
					if currentKey or adder:
						add = self.parseData(groups)
						if prelit:
							add = (add[0], prelit + add[1])
							prelit = ""
						#endif
					# Otherwise this might be a struct head
					else: lastLit = lit
				elif prelit:
					error = "Key can only be in a struct."
				elif flow:
					if flow == "{":
						# Open struct
						structHead = lastLit.split(" ")
						lastLit = None

						if len(structHead) > 2:
							error = "Expects only type and name for struct declaration."
						elif currentKey is not None:
							error = 'Cannot have a struct in a key. (Did you mean "type %s {"?)' % currentKey
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
						prelit = key + ":" + afterkey
					else: currentKey = key
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
		"""
		Instantiates data. Used by parse and parseData
		Ensures references and lists are handled appropriately, as well as
		wrapping regular data.
		"""
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

	def parseData(self, data, currentStruct=None, currentKey=None, line=-1, char=-1, raw=False):
		"""
		Parse one value from string form. May also take in a preparsed string
		though this has a different return form.
		Passing as a tuple of preparsed data returns: (type, data)
		Passing as a string returns just the wrapped data.
		"""
		pp = type(data) is tuple
		if pp: dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = data
		else:
			if data == "":
				dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = (
					None, None, None, None, None, None, None, None, ""
				)
			else:
				try: dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = self.tokenize.match(data).groups()
				except AttributeError: raise RPLError("Syntax error in data: %s" % data)
			#endif
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
			elif RPL.isRange.search(num):
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

		if add:
			if raw:
				if type(add) is not tuple: return add
				else: return add[1]
			elif pp or type(add) is not tuple: return add
			else: return self.parseCreate(add, currentStruct, currentKey, line, char)
		elif error: raise RPLError(error)
		elif pp: raise RPLError("Error parsing data.")
		else: raise RPLError("Error parsing data: %s" % data)
	#endif

	def addDef(self, key, value):
		"""
		Add a key/value pair to the Defs struct. Used on the command line.
		"""
		if "Defs" not in self.structsByName:
			defs = self.structsByName["Defs"] = Static(self, "Defs")
		else: defs = self.structsByName["Defs"]
		defs[key] = self.parseData(value, defs, key)
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
		self.orderedRoot.append(new)
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
		try: classRef.typeName
		except AttributeError: classRef.typeName = classRef.__name__.lower()
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
		self.rom = rom = helper.stream(rom)
		self.importing = True
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Doing this in a three step process ensures proper ordering when
		# importing shared data.

		# Do preparations
		toImport, toProcess = [], []
		for x in self:
			if isinstance(x, Serializable):
				if self.wantPort(x, what) and x["import"]:
					x.importPrepare(lfolder)
					toImport.append(x)
				#endif
			elif isinstance(x, Executable): toProcess.append(x)
			#endif
		#endfor
		# Process
		# We have to process this in reverse, because we process forward
		# when exporting. eg. calc x*2 -> map 2->'b' -> writes b, we need
		# to unmap 'b'->2 first then x/2 to have the packed value.
		for x in reversed(toProcess): x.importProcessing()
		# Commit imports
		for x in toImport: x.importData(rom)
		self.importing = None
	#enddef

	def exportData(self, rom, folder, what=[]):
		"""
		Export data from rom into folder according to what.
		"""
		self.rom = rom = helper.stream(rom)
		self.importing = False
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Exports are lazily drawn from the ROM, as there is no ordering
		# necessary since it's all based on fixed positions. Prerequisites are
		# handled properly this way, such as pulling lengths or pointers from
		# other blocks

		# Do preparations
		toExport = []
		for x in self:
			if isinstance(x, Serializable):
				if self.wantPort(x, what) and x["export"]: toExport.append(x)
			elif isinstance(x, Executable): x.exportProcessing()
			#endif
		#endfor
		# Write exports
		for x in toExport: x.exportData(rom, lfolder)
		for x in self.sharedDataHandlers.itervalues(): x.write()
		self.importing = None
	#enddef

	def wrap(self, typeName, value=None):
		"""
		Wrap a value in its respective RPLData class by type name.
		"""
		if typeName in self.types:
			return self.types[typeName](value)
		raise RPLError('No type "%s" defined' % typeName)
	#enddef

	def share(self, share, create, *vargs, **kwargs):
		"""
		Return the handle by key (typically filename) of the shared data.
		Instantiates handle if it doesn't exist.
		Structs that point to the same data should modify the same data, in the
		order that they're listed in the RPL.
		"""
		if share in self.sharedDataHandlers: return self.sharedDataHandlers[share]
		else:
			tmp = create(*vargs, **kwargs)
			tmp.setup(self, share)
			if self.importing: tmp.read()
			self.sharedDataHandlers[share] = tmp
			return tmp
		#endif
	#enddef

	def child(self, name): return self.root[name]
	def __iter__(self): return iter(self.orderedRoot)
#endclass

################################################################################
################################# RPLTypeCheck #################################
################################################################################
class RPLTypeCheck(object):
	"""
	Checks a RPLData struct against a set of possibilities.
	The passed syntax is as follows:
	 * type - Type name
	 * type:(allowed values) - A comma separated list of allowed values
	          This is not valid for list-derived types.
	 * all  - Any type allowed
	 * [type, ...] - List containing specific types
	 * |    - Boolean or
	 * []*  - Can either be just the contents, or a list containing multiple
	         of that content. Multipart lists treat commas like |
	 * []*# - Where # is a number indicating the index to match for nonlist
	          version, rather than matching any index.
	 * []+  - Contents may be repeated indefinitely within the list.
	 * []+# - Only repeat the last # elements, 0 or more times.
	 * []!  - May be any one of the contents not in a list, or the whole list.
	 *       ie. Like * but unable to repeat the list.
	 * []!# - See []*#
	 * []~  - Nonnormalizing form of []*
	 * []~# - See []*#
	 * [].  - Nonnormalizing form of []!
	 * [].# - See []*#
	 * ^    - Recurse parent list at this point
	"""

	tokenize = re.compile(
		# Whitespace
		r'\s+|'
		# List forms
		r'([\[\]*+!~.|,])(?:(?<=[*!~.+])([0-9]+))?|'
		r'(?:'
			# Type (or all)
			r'([^\s\[\]*+!~.|,^:]+)'
			# Allowed types (optional)
			r'('
				r':\((?:(?:"[^"]+"|'
				r"'[^']'|[^'"
				r'",]+)\s*,?\s*)+\)'
			r')?|'
			# Recursion operator
			r'(\^)'
		r')'
	)

	def __init__(self, rplOrPreparsed, name=None, syntax=None):
		"""
		You can either pass preparse data or a string that needs to be parsed.
		The former is just for testing, really.
		"""
		# Handle preparsed data
		if name is None and syntax is None: self._root = rplOrPreparsed
		elif name is None or syntax is None:
			raise TypeError("__init__() takes either 1 or 3 arguments (2 given)")
		# Handle unparsed data
		else: self._root = self.__parse(rplOrPreparsed, name, syntax)
	#enddef

	def __parse(self, rpl, name, syntax):
		"""
		FYI: This is one of the most ridiculous looking parsers I've written.
		"""
		lastType = None
		remain = None
		parents = []
		lastWasListEnd, lastWasRep = False, False
		for token in RPLTypeCheck.tokenize.finditer(syntax):
			try:
				#print name, token.groups()
				flow, num, tName, discrete, recurse = token.groups()
				if num: num = int(num)

				if recurse: tName = recurse
				if discrete: discrete = [rpl.parseData(x.strip(), raw=True) for x in discrete[2:-1].split(",")]

				if tName: lastType = RPLTCData(rpl, tName, discrete)
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
					if lastWasListEnd: remain.rep(flow, num)
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
			if parents[0][0] == "or": return RPLTCOr(parents[0][1])
			else: raise RPLError('Key "%s": Unclosed lists.' % name)
		elif lastType: return lastType
		elif remain: return remain
		else: raise RPLError('Key "%s": I did nothing!' % name)
	#enddef

	def verify(self, data): return self._root.verify(data)
#endclass

# RPL TypeCheck Data
class RPLTCData(object):
	"""
	Helper class for RPLTypeCheck, contains one type.
	"""
	def __init__(self, rpl, t, discrete=None):
		self._rpl, self._type, self._discrete = rpl, t, discrete
	#enddef

	# Starting to feel like I'm overdoing this class stuff :3
	def verify(self, data, parentList=None):
		if self._type == "^":
			if parentList is not None:
				return parentList.verify(data, parentList)
			else: return None
		elif (self._type == "all"
			or isinstance(data, RPLRef)
			or isinstance(data, self._rpl.types[self._type])
		) and (not self._discrete
			or data in self._discrete
		): return data
		elif issubclass(self._rpl.types[self._type], data.__class__):
			# Attempt to recast to subclass
			try: return self._rpl.types[self._type](data.get())
			except RPLError: return None
		else: return None
	#enddef
#endclass

# RPL TypeCheck List
class RPLTCList(object):
	"""
	Helper class for RPLTypeCheck, contains one list.
	"""
	def __init__(self, l, r="]", num=None):
		self._list, self._repeat, self._num = l, r, num
	def rep(self, r, num): self._repeat, self._num = r, num

	def verify(self, data, parentList=None):
		# Make sure data is a list (if it is 0 or more)
		if not isinstance(data, List):
			if self._repeat in "*!~.":
				if self._num is not None:
					# Select only the given index to compare.
					if self._num >= len(self._list):
						raise RPLError("Index not in list.")
					#endif
					tmp = self._list[self._num].verify(data)
					if tmp is None: return None
					elif self._repeat in "*!": return List([tmp])
					else: return tmp
				#endif

				# This seems like strange form but it's the only logical form
				# in my mind. This implies [A,B]* is A|B|[A,B]+ Using * on a
				# multipart list is a little odd to begin with.
				for x in self._list:
					tmp = x.verify(data)
					if tmp is not None:
						if self._repeat in "*!": return List([tmp])
						else: return tmp
					#endif
				#endfor
				return None
			else: return None
		#endif

		# Check lengths
		d = data.get()
		if self._repeat in "+*":
			if self._repeat == "+" and self._num is not None:
				# Number of non-repeating elements
				diff = len(self._list) - self._num
				if len(d) < diff or (len(d)-diff) % self._num: return None
				mod = (lambda(i): i if i < diff else ((i-diff) % self._num) + diff)
			elif (len(d) % len(self._list)) == 0:
				mod = (lambda(i): i % len(self._list))
			else: return None
		elif len(d) == len(self._list):
			mod = (lambda(i): i)
		else: return None

		# Loop through list contents to check them all
		nd = []
		for i,x in enumerate(d):
			nd.append(self._list[mod(i)].verify(d[i], self))
			if nd[-1] is None: return None
		#endfor

		if d != nd: return List(nd)
		else: return data
	#enddef
#endclass

# RPL TypeCheck Or
class RPLTCOr(object):
	"""
	Helper class for RPLTypeCheck, contains one OR set.
	"""
	def __init__(self, orSet): self._or = orSet

	def verify(self, data, parentList=None):
		for x in self._or:
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
	"""
	Base class for a struct.
	"""

	# Be sure to define typeName here!

	def __init__(self, rpl, name, parent=None):
		# Be sure to call this in your own subclasses!
		self._rpl = rpl
		self._name = name
		self._parent = parent
		self._data = {}
		self._keys = {}
		self._orderedKeys = []
		self._structs = {}
		self._children = {}
		self._orderedChildren = []

		try: self.typeName
		except AttributeError: self.typeName = self.__class__.__name__.lower()
	#enddef

	def addChild(self, sType, name):
		"""
		Add a new struct as a child of this one.
		"""
		if sType not in self._structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				sType, self.typeName
			))
		#endif
		new = self._structs[sType](self._rpl, name, self)
		self._children[name] = new
		self._orderedChildren.append(new)
		return new
	#enddef

	def regKey(self, name, basic, default=None):
		"""
		Register a key by name with type and default.
		"""
		check = RPLTypeCheck(self._rpl, name, basic)
		self._keys[name] = [check,
			None if default is None else check.verify(self._rpl.parseData(default))
		]
	#enddef

	def regStruct(self, classRef):
		"""
		Method to register a custom struct.
		"""
		try: classRef.typeName
		except AttributeError: classRef.typeName = classRef.__name__.lower()
		self._structs[classRef.typeName] = classRef
	#enddef

	def validate(self):
		"""
		Validate self.
		"""
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
		"""
		Write struct to RPL format.
		"""
	#enddef

	def __getitem__(self, key):
		"""
		Return data for key.
		"""
		x = self
		while x and key not in x._data: x = x.parent()
		if x: return x._data[key]
		elif key in self._keys and self._keys[key][1] is not None:
			x._data[key] = self._keys[key][1]
			return x._data[key]
		else: raise RPLError('No key "%s"' % key)
	#enddef

	def __setitem__(self, key, value):
		"""
		Set data for key, verifying and casting as necessary.
		"""
		if key in self._keys:
			# Reference's types are lazily checked
			if key not in self._data: self._orderedKeys.append(key)
			if isinstance(value, RPLRef): self._data[key] = value
			else: self._data[key] = self._keys[key][0].verify(value)
		else: raise RPLError('"%s" has no key "%s".' % (self.typeName, key))
	#enddef

	def name(self): return self._name
	def parent(self): return self._parent

	def basic(self, callers=[]):
		"""
		Stub. Return basic data (name by default).
		"""
		return Literal(self._name)
	#enddef

	def __len__(self):
		"""
		Return number of children (including keys).
		"""
		return len(self._data) + len(self._children)
	#enddef

	def __nonzero__(self): return True
	def child(self, name): return self._children[name]
	def __iter__(self): return iter(self._orderedChildren)
	def iterkeys(self): return iter(self._orderedKeys)

	def get(self, data):
		if isinstance(data, RPLRef): return data.get(this=self)
		else: return data.get()
	#endif

	def set(self, data, val):
		if isinstance(data, RPLRef): return data.set(val, this=self)
		else: return data.set(val)
	#endif
#endclass

class Static(RPLStruct):
	"""
	A generic struct that accepts all keys. Used to store static information.
	Does not import or export anything.
	"""

	typeName = "static"

	def addChild(self, sType, name):
		"""
		Overwrite this cause Static accepts all root children.
		"""
		if sType not in self._rpl.structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				sType, self.typeName
			))
		#endif
		new = self._rpl.structs[sType](self._rpl, name, self)
		self._children[name] = new
		self._orderedChildren.append(new)
		return new
	#enddef

	def verify(self):
		"""
		Overwrite this cause Static accepts all keys.
		"""
		return True
	#enddef

	def __setitem__(self, key, value):
		"""
		Overwrite this cause Static accepts all keys.
		"""
		if key not in self._data: self._orderedKeys.append(key)
		self._data[key] = value
	#enddef
#endclass

class Serializable(RPLStruct):
	"""
	Inherit this class for data that can be imported and/or exported.
	"""

	# NOTE: There is no typeName because this is not meant to be used directly.

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		self.regKey("base", "hexnum", "$000000")
		self.regKey("file", "string", "")
		self.regKey("ext", "string", "")
		self.regKey("export", "number", "true")
		self.regKey("import", "number", "true")

		self._prepared = False
	#enddef

	def open(self, folder, ext="bin", retName=False, justOpen=False):
		"""
		Helper method for opening files.
		"""
		if not justOpen:
			if type(folder) in [str, unicode]: folder = list(os.path.split(os.path.normpath(folder)))

			# Function to return defined filename or struct's defined name
			# If the filename starts with a / it is considered a subdir of parent
			# structs.
			def fn(x):
				if "file" in x._data:
					f = os.path.normpath(x._data["file"].get())
					if f[0:len(os.sep)] == os.sep: return (True, list(os.path.split(f[len(os.sep):])))
					else: return (False, list(os.path.split(f)))
				else: return (True, None if x._gennedName else [x.name()])
			#enddef

			# Create the filename with extension
			cont, f = fn(self)
			if f[-1].find(os.extsep) != -1: path = f
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
			# TODO: Parse out "already exists" specifically
			except os.error: pass

			# Return requested thing (path or handle)
			if retName: return path
		else: path = folder
		return self._rpl.share(path, codecs.open, x, encoding="utf-8", mode="r+")
	#enddef

	def close(self, handle):
		"""
		Helper method for closing files.
		"""
		try: handle.close()
		except AttributeError: del handle
	#enddef

	def importPrepare(self, key, rom, folder):
		"""
		Stub. Fill this in to import appropriately.
		"""
		pass
	#enddef

	def importData(self, rom, folder):
		"""
		Stub. Fill this in to import appropriately.
		"""
		pass
	#enddef

	def exportData(self, rom, folder):
		"""
		Stub. Fill this in to export appropriately.
		"""
		pass
	#enddef
#endclass

class Executable(RPLStruct):
	"""
	Inherit this class for structs that do processing on data, rather than
	directly importing or exporting.
	"""
	def importProcessing(self):
		"""
		Stub. Fill this in to process data before importing.
		"""
		pass
	#enddef

	def exportProcessing(self):
		"""
		Stub. Fill this in to process data before exporting.
		"""
		pass
	#enddef
#endclass

class Cloneable(RPLStruct):
	"""
	Inherit this class for structs that can have multiple instances of itself.
	This is a very complex subject for RPL, and will probably not be commonly
	used.
	"""
	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)

		self._clone = set()
		self._clones = []
	#enddef

	def alsoClone(self, *add):
		self._clone |= set(add)
	#enddef

	def clone(self):
		new = self.__class__(self._rpl, self._name, self._parent)
		# Clone isn't copied cause that should be done in the init
		for x in [
			"_data", "_keys", "_orderedKeys", "_structs", "_children",
			"_orderedChildren"
		] + list(self._clone):
			setattr(new, x, copy.deepcopy(getattr(self, x)))
		#endfor
		self._clones.append(new)
		return new
	#enddef

	def clones(self): return iter(self._clones)
#endclass

################################################################################
#################################### RPLRef ####################################
################################################################################
class RPLRef:
	"""
	Manages references to other fields.
	"""

	spec = re.compile(r'@?([^.]+)(?:\.([^\[]*))?((?:\[[0-9]+\])*)')
	heir = re.compile(r'^(?=.)((w*)back_?)?((g*)parent)?$')

	typeName = "reference"

	def __init__(self, rpl, container, mykey, ref, line, char):
		self._rpl = rpl
		self._container = container
		self._mykey = mykey
		self._pos = (line, char)

		self._struct, self._key, idxs = self.spec.match(ref).groups()
		if idxs: self._idxs = map(int, idxs[1:-1].split("]["))
		else: self._idxs = []
	#enddef

	def __unicode__(self):
		"""
		Output ref to RPL format.
		"""
		ret = "@%s" % self._struct
		if self._key: ret += "."+self._key
		if self._idxs: ret += "[%s]" % "][".join(self._idxs)
		return ret
	#enddef

	def parts(self): return self._struct, self._key, self._idxs

	def pointer(self, callers=[], this=None):
		# When a reference is made, this function should know what struct made
		# the reference ("this", ie. self._container) BUT also the chain of
		# references up to this point..
		# First check if we're referring to self or referrer and/or parents.
		heir = RPLRef.heir.match(self._struct)
		if self._struct == "this" or heir:
			if self._container is None or self._mykey is None:
				raise RPLError("Cannot use relative references in data form.")
			#endif
			# Referrer history
			if heir and heir.group(1):
				try: ret = callers[-1 - len(heir.group(2))]
				except IndexError: raise RPLError("No %s." % self._struct)
			# "this" or parents only
			else: ret = this or self._container
			# "parent"
			if heir and heir.group(3):
				ret = ret.parent()
				# The gs (great/grand) in g*parent
				for g in heir.group(4):
					try: ret = ret.parent()
					except Exception as x:
						if ret is not None: raise x
					#endtry
					if ret is None: raise RPLError("No %s." % self._struct)
				#endfor
			#endif
		else: ret = self._rpl.structsByName[self._struct]
		return ret
	#enddef

	def getFromIndex(self, ret, callers):
		callersAndSelf = callers + [self]
		for i, x in enumerate(self._idxs):
			try:
				if isinstance(ret, RPLRef): ret = ret.get(callersAndSelf)[x]
				elif isinstance(ret, List): ret = ret.get()[x]
				else: raise IndexError
			except IndexError:
				raise RPLError("List not deep enough. Failed on %ith index." % i)
			#endtry
		#endfor

		if isinstance(ret, RPLRef): ret = ret.get(callersAndSelf, True)
		return ret
	#endif

	def get(self, callers=[], retCl=False, this=None):
		"""
		Return referenced value.
		"""
		ret = self.pointer(callers, this)
		if not self._key: ret = ret.basic()
		else: ret = ret[self._key]
		ret = self.getFromIndex(ret, callers)

		# Verify type
		if (self._container is not None and self._mykey is not None
		and self._mykey in self._container._keys):
			# TODO: Combobulate data to verify..?
			#ret = self._container._keys[self._mykey][0].verify(data)
			pass
		#endif
		if retCl: return ret
		else: return ret.get()
		#endif
	#endif

	def set(self, data, callers=[], retCl=False, this=None):
		"""Set referenced value (these things are pointers, y'know"""
		ret = self.pointer(callers, this)

		if not self._key:
			try:
				# This passes unwrapped data
				ret.setBasic(data)
				return True
			except AttributeError: return False
		else:
			k = self._key
			if self._idxs:
				oret = None
				callersAndSelf = callers + [self]
				for i, x in enumerate(self._idxs):
					try:
						oret = ret[k]
						if isinstance(ret, RPLRef): ret = ret[k].get(callersAndSelf)
						else: ret = ret[k].get()
						ret[x] # Throw error if it doesn't exist
						k = x
					except IndexError:
						raise RPLError("List not deep enough. Failed on %ith index." % (i-1))
					#endtry
				#endfor
			#endif
			# Needs to wrap data
			datatype = {
				str: "string", unicode:"string", int: "number", long:"number",
				list: "list"
			}[type(data)]
			if datatype == "list" and isinstance(data[0], RPLData):
				skipSubInst = True
			else: skipSubInst = False
			ret[k] = self._rpl.parseCreate(
				(datatype, data), None, None, *self._pos, skipSubInst=skipSubInst
			)
			if self._idxs: oret.set(ret)
			return True
		#endif
	#enddef

	def proc(self, func, callers=[], clone=None):
		"""Used by executables"""
		point = clone or self.pointer(callers)
		if clone is None and isinstance(point, Cloneable):
			for x in point.clones(): self.proc(func, callers, x)
		else:
			# TODO: Better error wording
			if not self._key: raise RPLError("Tried to proc on basic reference.")
			# TODO: Check that I'm doing callers right here. I think it's right
			# but I don't wanna think that hard right now.
			self.getFromIndex(point[self._key], callers).proc(func, callers + [self])
		#endif
	#enddef
#endclass

################################################################################
#################################### RPLData ###################################
################################################################################

class RPLData(object):
	def __init__(self, data=None):
		if data is not None: self.set(data)
	#enddef

	def get(self): return self._data
	def set(self, data): self._data = data

	def proc(self, func, clone=None):
		"""
		Used by executables.
		"""
		self.set(func(self.get()))
	#enddef

	#def defaultSize(self)       # Returns default size for use by Data struct
	#def serialize(self, **kwargs)         # Return binary form of own data.
	#def unserialize(self, data, **kwargs) # Parse binary data and set to self.

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
			raise RPLError('Type "%s" expects unicode or str. Got "%s"' % (
				self.typeName, type(data).__name__
			))
		#endif
		self._data = String.escape.sub(String.replIn, data)
	#enddef

	def __unicode__(self):
		return '"' + String.binchr.sub(String.replOut, self._data) + '"'
	#enddef

	def serialize(self, **kwargs):
		rstr = self._data.encode("utf8")
		if "size" not in kwargs or not kwargs["size"]: return rstr
		# TODO: This can split a utf8 sequence at the end. Need to fix..
		rstr = rstr[0:min(kwargs["size"], len(rstr))]
		rpad = kwargs["padchar"] * (kwargs["size"] - len(rstr))
		if rpad == "": return rstr
		padside = kwargs["padside"]
		if padside == "left": return rpad + rtsr
		elif padside[1:] == "center":
			split = (ceil if padside[0] == "r" else int)(len(rpad) / 2)
			return rpad[0:split] + rtsr + rpad[split:0]
		elif padside == "right": return rtsr + rpad
	#enddef

	def unserialize(self, data, **kwargs): self._data = data.decode("utf8")

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

	def serialize(self, **kwargs):
		big, ander, ret = (kwargs["endian"] == "big"), 0xff, r''
		for i in range(kwargs["size"]):
			c = chr((self._data & ander) >> (i*8))
			if big: ret = c + ret
			else: ret += c
			ander <<= 8
		#endfor
		return ret
	#enddef

	def unserialize(self, data, **kwargs):
		big = (kwargs["endian"] == "big")
		size = len(data)
		self._data = 0
		for i,x in enumerate(data):
			if big: shift = size-i-1
			else: shift = i
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
