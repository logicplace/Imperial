import os
import re
import copy
import codecs
import helper
from math import ceil
from zlib import crc32
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

# TODO:
#  * RPLRef issues:
#    * @back (maybe?)
#  * T) Serializers that modify the same file need to compound.
#    Therefore, make a system in which structs request the handler/data to
#    modify, which will open the file and read it if it's the first, but
#    otherwise return the already loaded/modified data to be further modified.
#  * Add referencing multiline strs with @` ` form.

class RPLError(Exception): pass

class RecurseIter(object):
	"""
	Iterator used by both RPL and RPLStruct to recurse their children.
	"""
	def __init__(self, children):
		self._children, self._iter = children.itervalues(), None
	#enddef

	def __iter__(self): return self

	def next(self):
		try:
			# This will be None at the beginning and after completing a child.
			if self._iter: return self._iter.next()
			else: raise StopIteration
		except StopIteration:
			# Raised when child has completed. Continue to next child.
			child = self._children.next() # This will raise if we're done
			self._iter = child.recurse()
			# This order makes it return itself before returning any of its children
			return child
		#endtry
	#enddef
#endclass

# TODO: Sometime I need to make RPL and RPLStruct inherit the same class
# for their redundant functions..
class RPL(object):
	"""
	The base type for loading and interpreting RPL files.
	Also handles "execution" and what not.
	The commandline and any other programs that may use this system will
	interface with this object.
	"""

	# Constants
	specification = re.compile(
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
		 r'(%(r1)s%(r2)s%(r1)s:\-*+~%(r2)s*(?=[,\]\s]|$))|'
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
			# Between these parts, one can add more things to this set.
			# It's used above to add :\-*+~ in one portion.
			# Range part 2
			"r2": r']|(?<!\w)[a-z](?=:)|(?<=:)[a-z](?!\w)|\$[0-9a-fA-F]+)',
			# Invalid characters for a Literal
			"lit": r'{}\[\],\$@"#\r\n' r"'",
			# Valid key name
			"key": r'[a-z]+[0-9]*'
		}
	, re.M | re.U)

	# Used to parse a multiline string token into its real data
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
			"bin": r'[\-*+~]',
			# Valid forms for a number
			"num": r'[0-9]+|\$[0-9a-fA-F]+'
		}
	)

	# Quick check for if a number is a range or not
	isRange = re.compile(r'[:\-*+~]')

	def __init__(self):
		self.types = {}              # Registered data types
		self.structs = {}            # Structs allowed in the root
		self.root = odict()          # Top-level structs in the rpl file
		self.structsByName = {}      # All structs in the file
		self.sharedDataHandlers = {} # Used by RPL.share
		self.importing = None        # Used by RPL.share, NOTE: I would like to remove this..
		self.alreadyLoaded   = ["helper", "__init__", "rpl"]
		self.alreadyIncluded = []    # These are used by RPL.load
		self.defaultTemplateStructs = ["RPL", "ROM"] # What to include in the default template

		# Registrations
		self.registerStruct(StructRPL)
		self.registerStruct(ROM)
		self.registerStruct(Static)

		self.registerType(String)
		self.registerType(Literal)
		self.registerType(Path)
		self.registerType(Number)
		self.registerType(HexNum)
		self.registerType(List)
		self.registerType(Range)
		self.registerType(Bool)
		self.registerType(Size)
	#enddef

	def parse(self, inFile, onlyCareAboutTypes=[]):
		"""
		Read in a file and parse it. The form is essentially structs with
		key/value pairs in them. Each struct type has different functionality
		and there are different datatypes as well. There are also references.

		Values may only be contained in keys which may only be contained in
		structs.

		Therefore the root may only contain structs.

		Key names and struct types must be lowercase. Both may be trailed
		by numbers as well.

		It is convention for a struct name to be proper case, but is not
		required by the parser.

		Key/value pairs may be separated with a comma or a newline. Values
		within a list follow the same convention. The only value that cannot
		be separated by a newline (from a directly following value of the same
		type) is the multiline string. For example:

		list: [
			`str1`
			`still str1`
		]
		# vs.
		list: [
			`str1`,
			`str2`
		]

		The basic datatypes are: number, string, and list. They are the absolute
		base types of the system, and I for one think that's so for any system.
		There are more basic forms, however, the make up the syntax. Each type
		from then on is derived from one of the above three basic types. These
		are all of the types and their syntax (Name(Comment)):
		Number:                                    1234
		HexNum(Hexadecimal Number):                $12a4B0

		String:                                    "abcdef"
		Literal:                                   abcdef

		List:                                      [1, "abc", etc]
		Range(List form: [1,2,3,4,5,5,x,4]):       1-4:5*2:x:4

		Reference(To basic data):                  @SomeStruct
		Reference(To a key's value):               @SomeStruct.key
		Reference(To a value within a key's list): @SomeStruct.key[3][0]

		You may see tests/rpls/rpl.rpl for an example.
		"""
		raw = helper.readFrom(inFile) # Raw data from file

		# Prelit allows colons to be inside literals.
		lastLit, prelit = None, "" # Helpers for literal forming
		currentKey = None          # What key the next value is for
		currentStruct = None       # What struct we are currently parsing
		counts = {}                # How many of a certain struct type we've enountered
		parents = []               # Current hierarchy of structs and lists

		for token in RPL.specification.finditer(raw):
			groups = token.groups() # Used later
			dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = groups
			sstr = dstr or sstr # Double or single quoted string
			# (type, value) to add; error to throw; skip list childs' instantiations
			add, error, skipSubInst = None, None, False

			# Find the position (used for ref and errors)
			pos = token.start()
			# Line and character numbers are 1-based (because gedit is 1-based o/ )
			line, char = raw.count("\n",0,pos) + 1, pos - raw.rfind("\n",0,pos) + 1

			try:
				if lit:
					# Literals can either be the struct head (type and optionally name)
					# or a string that has no quotes.
					lit = lit.rstrip()
					# If the last token was a key or this is inside a list, this
					# is string data (as a literal type).
					if currentKey or parents:
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
							elif not onlyCareAboutTypes or structType in onlyCareAboutTypes:
								self.structsByName[structName] = currentStruct = (
									currentStruct if currentStruct else self
								).addChild(structType, structName)
								currentStruct._gennedName = genned
							#endif
						#endif
					elif flow == "}":
						# Close struct
						if currentStruct is None: error = "} without a {."
						elif parents: error = "Unclosed list."
						elif currentKey is not None:
							error = "Key with no value. (Above here!)"
						#endif

						# TODO: The second condition is kinda hacky, it's meant to avoid
						# loading external things in partial-parsing mode..
						if isinstance(currentStruct, StructRPL) and not onlyCareAboutTypes:
							self.load(currentStruct)
						#endif
						currentStruct = currentStruct.parent()
					elif flow == "[":
						# Begins list
						parents.append([])
					elif flow == "]":
						# End list
						if parents:
							add = ("list", parents.pop())
							skipSubInst = True
						else: error = "] without a [."
					elif flow == ",":
						# Separator (only really directs the regex)
						pass
					#endif
				elif key:
					if currentStruct is None or parents:
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
				dtype = add[0]
				val = self.parseCreate(add, currentStruct, currentKey, line, char, skipSubInst)

				if parents:
					parents[-1].append(val)
				elif currentStruct and currentKey:
					currentStruct[currentKey] = val
					currentKey = None
				else:
					error = "Unused " + dtype
				#endif
			#endif

			if error:
				raise RPLError("Error in line %i char %i: %s" % (
					line, char, error
				))
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
			# So I don't have to have two branches doing the same thing we
			# regard the data as a list for now, and change it back after.
			if type(val) is not list: nl, val = True, [add]
			else: nl = False
			val = map(lambda(x): self.wrap(*x), val)
			if nl: val = val[0]
			else: val = self.wrap(dtype, val)
		#endif

		return val
	#enddef

	@staticmethod
	def numOrHex(num):
		if num[0] == "$": return ("hexnum", int(num[1:], 16))
		else: return ("number", int(num))
	#enddef

	def parseData(self, data, currentStruct=None, currentKey=None, line=-1, char=-1, raw=False):
		"""
		Parse one value from string form. May also take in a preparsed string
		though this has a different return form.
		Passing as a tuple of preparsed data returns: (type, data)
		Passing as a string returns just the wrapped data.
		You may use raw to return unwrapped data, without type.
		"""
		pp = type(data) is tuple
		if pp: dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = data
		else:
			if data == "":
				dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = (
					None, None, None, None, None, None, None, None, ""
				)
			else:
				try: dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = RPL.specification.match(data).groups()
				except AttributeError: raise RPLError("Syntax error in data: %s" % data)
			#endif
		#endif
		sstr = dstr or sstr

		add, error = None, None

		if ref: add = ("reference", ref)
		elif sstr: add = ("string", sstr)
		elif mstr:
			# Need to remove all `s and comments
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
					inc = r.split("+")
					dec = r.split("~")
					if len(bounds) == 2:
						lt, l = RPL.numOrHex(bounds[0])
						rt, r = RPL.numOrHex(bounds[1])
						numList += [(lt, l)] + map(lambda(x): ("number", x), (
							list(range(l + 1, r)) if l < r else list(range(l - 1, r, -1))
						)) + [(rt, r)]
					elif len(times) == 2:
						lt, l = RPL.numOrHex(times[0])
						rt, r = RPL.numOrHex(times[1])
						numList += map(lambda(x): (lt, x), [l] * r)
					elif len(inc) == 2:
						lt, l = RPL.numOrHex(inc[0])
						rt, r = RPL.numOrHex(inc[1])
						numList += map(lambda(x): (lt, x), list(range(l, l + r)))
					elif len(dec) == 2:
						lt, l = RPL.numOrHex(dec[0])
						rt, r = RPL.numOrHex(dec[1])
						numList += map(lambda(x): (lt, x), list(range(l, l - r, -1)))
					elif r in "abcdefghijklmnopqrstuvwxyz":
						numList.append(("literal", r))
					else: numList.append(RPL.numOrHex(r))
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
			add = ("literal", lit.strip())
		elif not pp and flow == "[":
			tmp = RPL.specification.finditer(data)
			tmp.next() # Skip the first flow
			lists = [[]]
			for token in tmp:
				token = token.groups()
				dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = token
				if flow == "[":
					ls = []
					lists[-1].append(ls)
					lists.append(ls)
				elif flow == "]":
					try: last = lists.pop()
					except IndexError: break
				elif flow == ",": pass
				else: lists[-1].append(self.parseData(token, currentStruct, currentKey, line, char, raw))
			#endfor
			add = ("list", last)
		elif pp: raise RPLError("Invalid data.")
		else: raise RPLError("Invalid data: %s" % data)

		if add:
			if raw: return add[1]
			elif pp: return add
			else: return self.parseCreate(add, currentStruct, currentKey, line, char)
		elif error: raise RPLError(error)
		elif pp: raise RPLError("Error parsing data.")
		else: raise RPLError("Error parsing data: %s" % data)
	#endif

	def load(self, struct):
		"""
		Loads includes and libs. Used by parse, probably should not need to
		use it directly. (But if you generate a ROM struct for some reason,
		this isn't called when you append it, so you can do it manually then.)
		"""
		# Load libraries (python modules defining struct and data types)
		for lib in struct["lib"].get():
			lib = lib.get()
			if lib in self.alreadyLoaded: continue
			tmp = __import__(lib, globals(), locals())
			tmp.register(self)
			self.alreadyLoaded.append(lib)
		#endfor

		if "RPL_INCLUDE_PATH" in os.environ:
			includePaths = set(["."] + os.environ["RPL_INCLUDE_PATH"].split(";"))
		else: includePaths = ["."]
		# Include other RPLs (this should inherently handle ROM structs
		# in the included files)
		for incl in struct["include"].get():
			incl = incl.get()
			if incl in self.alreadyIncluded: continue
			for path in includePaths:
				path = os.path.join(path, incl)
				tmp = None
				try: tmp = open(path, "r")
				except IOError as err:
					if err.errno == 2:
						try: tmp = open(path + os.extsep + "rpl", "r")
						except IOError as err:
							if err.errno == 2: continue
							else: raise RPLError("Could not include file %s: %s" % (path, err.strerror))
						#endtry
					else: raise RPLError("Could not include file %s: %s" % (path, err.strerror))
				if tmp:
					self.parse(tmp)
					tmp.close()
					self.alreadyIncluded.append(incl)
					break
				#endif
			#endfor
		#endfor
	#enddef

	def addDef(self, key, value):
		"""
		Add a key/value pair to the Defs struct. Used on the command line.
		Basically run time definitions, similar to the -D flag in gcc.
		"""
		if "Defs" not in self.structsByName:
			defs = self.structsByName["Defs"] = Static(self, "Defs")
		else: defs = self.structsByName["Defs"]
		defs[key] = self.parseData(value, defs, key)
	#enddef

	def addChild(self, structType, name):
		"""
		Add a new struct to the root "element"
		Note that this currently does not add things to structsByName, making
		structs only added to the root by this method unreferenceable.
		I'm not sure if this should be adjusted or not, yet.
		"""
		if structType not in self.structs:
			raise RPLError("%s isn't allowed as a substruct of root." % structType)
		#endif
		new = self.structs[structType](self, name)
		self.root[name] = new
		return new
	#enddef

	def __unicode__(self):
		"""
		Write self as an RPL file.
		Obviously this returns a string and does not actually write a file.
		"""
		# TODO: entire function
		pass
	#enddef

	def registerType(self, classRef):
		"""
		Method to register a custom type.
		"""
		self.types[classRef.typeName] = classRef
	#enddef

	def registerStruct(self, classRef):
		"""
		Method to register a custom struct as allowable in the root.
		"""
		try: classRef.typeName
		except AttributeError:
			raise RPLError(
				"You may not register a struct "
				"(%s) without a typeName." % classRef.__class__.__name__
			)
		self.structs[classRef.typeName] = classRef
	#enddef

	def template(self, structs=[]):
		"""
		Output the template. By default this is RPL and ROM.
		"""
		return (
			"# Description\n"
			"# Author: Your Name\n"
			"\n\n".join([x.template() for x in structs or self.defaultTemplateStructs])
		)
	#enddef

	def wantPort(self, x, what):
		# Runtime may request only certain executables be run. All children of
		# the given names are also executed. This recurses to find if it (x) or
		# any parent was requested.
		return x and (not what or x.name() in what or self.wantPort(x.parent(), what))
	#enddef

	def importData(self, rom, folder, what=[], nocreate=False):
		"""
		Import data from folder into the given ROM according to what.
		rom is the location of the binary ROM file.
		folder is the base folder for the project files.
		what is a list of names requested for execution.
		"""
		self.rom = rom = helper.stream(helper.FakeStream() if nocreate else rom)
		self.importing = True
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Doing this in a three step process ensures proper ordering when
		# importing shared data.

		# Do preparations
		toImport, toProcess = [], []
		for x in self.recurse():
			if isinstance(x, Serializable):
				if self.wantPort(x, what) and x["import"]:
					x.importPrepare(rom, lfolder)
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
		if not nocreate:
			for x in toImport: x.importData(rom, lfolder)
		#endif

		rom.close()
		self.importing = None
	#enddef

	def exportData(self, rom, folder, what=[], nocreate=False):
		"""
		Export data from rom into folder according to what.
		rom is the location of the binary ROM file.
		folder is the base folder for the project files.
		what is a list of names requested for execution.
		"""
		self.rom = rom = helper.stream(helper.FakeStream() if nocreate else rom)
		self.importing = False
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Exports are lazily drawn from the ROM, as there is no ordering
		# necessary since it's all based on fixed positions. Prerequisites are
		# handled properly this way, such as pulling lengths or pointers from
		# other blocks

		# Do preparations
		toExport, toProcess = [], []
		for x in self.recurse():
			if isinstance(x, Serializable):
				if self.wantPort(x, what) and x["export"]:
					x.exportPrepare(rom, lfolder)
					toExport.append(x)
			elif isinstance(x, Executable): toProcess.append(x)
			#endif
		#endfor

		# Process
		for x in toProcess: x.exportProcessing()

		# Write exports
		if not nocreate:
			for x in toExport: x.exportData(rom, lfolder)
			for x in self.sharedDataHandlers.itervalues(): x.write()
		#endif

		rom.close()
		self.importing = self.rom = None
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
		if share in self.sharedDataHandlers:
			if isinstance(create, type) and not isinstance(self.sharedDataHandlers[share], create):
				raise RPLError('Share of "%s" expected %s but was %s.' % (
					share, create.__name__, self.sharedDataHandlers[share].__class__.__name__
				))
			return self.sharedDataHandlers[share]
		else:
			tmp = create(*vargs, **kwargs)
			tmp.setup(self, share)
			if self.importing: tmp.read()
			self.sharedDataHandlers[share] = tmp
			return tmp
		#endif
	#enddef

	def child(self, name): return self.root[name]
	def __iter__(self): return self.root.itervalues()
	def recurse(self): return RecurseIter(self.root)

	def childrenByType(self, typeName):
		"""
		Return list of children that fit the given typeName
		typeName may be a string or the class that it will grab the string from
		"""
		if type(typeName) not in [str, unicode] and issubclass(typeName, RPLStruct):
			typeName = typeName.typeName
		#endif
		ret = []
		for x in self.root.itervalues():
			if x.typeName == typeName: ret.append(x)
		#endfor
		return ret
	#enddef
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
	 *        ie. Like * but unable to repeat the list.
	 * []!# - See []*#
	 * []~  - Nonnormalizing form of []*
	 * []~# - See []*#
	 * [].  - Nonnormalizing form of []!
	 * [].# - See []*#
	 * ^    - Recurse parent list at this point
	"""

	specification = re.compile(
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
				r'",)]+)\s*,?\s*)+\)'
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
		self._source = ""
		# Handle preparsed data
		if name is None and syntax is None: self._root = rplOrPreparsed
		elif name is None or syntax is None:
			raise TypeError("__init__() takes either 1 or 3 arguments (2 given)")
		# Handle unparsed data
		else: self._root = self.__parse(rplOrPreparsed, name, syntax)
	#enddef

	def __parse(self, rpl, name, syntax):
		"""
		Parses a typecheck string. See class's docstring for the specification.
		FYI: This is one of the most ridiculous looking parsers I've written.
		"""
		lastType = None
		remain = None
		parents = []
		lastWasListEnd, lastWasRep = False, False
		self._source = syntax
		for token in RPLTypeCheck.specification.finditer(syntax):
			try:
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

	def verify(self, data):
		try: return self._root.verify(data)
		except RPLError as err:
			raise RPLError(u'Verification failed ("%s" against "%s"): %s' % (
				unicode(data), self._source, err.args[0]
			))
		#endtry
	#enddef
#endclass

# RPL TypeCheck Data
class RPLTCData(object):
	"""
	Helper class for RPLTypeCheck; contains one type.
	"""
	def __init__(self, rpl, t, discrete=None):
		self._rpl, self._type, self._discrete = rpl, t, discrete
	#enddef

	# Starting to feel like I'm overdoing this class stuff. :3
	def verify(self, data, parentList=None):
		# Recursion operator check.
		if self._type == "^":
			if parentList is not None:
				return parentList.verify(data, parentList)
			else: raise RPLError(u"Attempted to recurse at top-level.")
		# If there is a discrete set of values, verify within that.
		elif self._discrete and data.get() not in self._discrete:
			raise RPLError(u'Value "%s" not allowed in discrete set: %s.' % (
				data.get(), helper.list2english(self._discrete)
			))
		# Check if the given type is valid.
		elif (self._type == "all"
			or isinstance(data, RPLRef)
			or isinstance(data, self._rpl.types[self._type])
		): return data
		# Otherwise, check if the expected type is a more specific subclass
		# of ther given type.
		elif issubclass(self._rpl.types[self._type], data.__class__):
			# Attempt to recast to subclass.
			try: return self._rpl.types[self._type](data.get())
			except RPLError as err:
				raise RPLError(u"Error when recasting subclass: %s" % err.args[0])
			#endtry
		else: raise RPLError(u"Error verifying data.")
	#enddef
#endclass

# RPL TypeCheck List
class RPLTCList(object):
	"""
	Helper class for RPLTypeCheck; contains one list.
	"""
	def __init__(self, l, r="]", num=None):
		self._list, self._repeat, self._num = l, r, num
	def rep(self, r, num): self._repeat, self._num = r, num

	def verify(self, data, parentList=None):
		# Make sure data is a list (if it is 0 or more).
		if not isinstance(data, List):
			if self._repeat in "*!~.":
				if self._num is not None:
					# Select only the given index to compare.
					if self._num >= len(self._list):
						raise RPLError(u"Index not in list.")
					#endif
					tmp = self._list[self._num].verify(data)
					if self._repeat in "*!": return List([tmp])
					else: return tmp
				#endif

				# This seems like strange form but it's the only logical form
				# in my mind. This implies [A,B]* is A|B|[A,B]+ Using * on a
				# multipart list is a little odd to begin with.
				for x in self._list:
					try:
						tmp = x.verify(data)
						if self._repeat in "*!": return List([tmp])
						else: return tmp
					except RPLError: pass
				#endfor
				raise RPLError(u"No permuation of single list data worked.")
			else: raise RPLError(u"Expected list.")
		#endif

		# Check lengths
		d = data.get()
		if self._repeat in "+*":
			if self._repeat == "+" and self._num is not None:
				# Number of non-repeating elements
				diff = len(self._list) - self._num
				if len(d) < diff or (len(d)-diff) % self._num:
					raise RPLError(u"Invalid list length.")
				#endif
				mod = (lambda(i): i if i < diff else ((i-diff) % self._num) + diff)
			elif (len(d) % len(self._list)) == 0:
				mod = (lambda(i): i % len(self._list))
			else: raise RPLError(u"Invalid list length.")
		elif len(d) == len(self._list):
			mod = (lambda(i): i)
		else: raise RPLError(u"Invalid list length.")

		# Loop through list contents to check them all
		nd = []
		for i,x in enumerate(d):
			nd.append(self._list[mod(i)].verify(d[i], self))
		#endfor

		return List(nd) if d != nd else data
	#enddef
#endclass

# RPL TypeCheck Or
class RPLTCOr(object):
	"""
	Helper class for RPLTypeCheck; contains one OR set.
	"""
	def __init__(self, orSet): self._or = orSet

	def verify(self, data, parentList=None):
		for x in self._or:
			try: return x.verify(data, parentList)
			except RPLError: pass
		#endfor
		raise RPLError(u"Matched no options.")
	#enddef
#endclass

################################################################################
################################### RPLStruct ##################################
################################################################################
class RPLStruct(object):
	"""
	Base class for a struct.
	When making your own struct type, inherit from this, or a subclass of it.
	There are more specific general structs below that will likely be more
	fitting than inheriting this directly.
	"""

	# Be sure to define typeName here in your own subclasses!

	def __init__(self, rpl, name, parent=None):
		# Be sure to call this in your own subclasses!
		self._rpl = rpl
		self._name = name
		self._parent = parent
		self._data = {}
		self._keys = odict()
		self._structs = {}
		self._children = odict()

		self._nocopy = ["_rpl", "_parent", "_keys"]
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
		return new
	#enddef

	def registerKey(self, name, typeStr, default=None):
		"""
		Register a key by name with type and default.
		"""
		check = RPLTypeCheck(self._rpl, name, typeStr)
		if default is not None:
			default = self._rpl.parseData(default)
			# Try to verify, so it can adjust typing
			try: default = check.verify(default)
			# But if it fails, we should trust the programmer knows what they want..
			except RPLError: pass
		#endif
		self._keys[name] = [check, default]
	#enddef

	def unregisterKey(self, name):
		"""
		Unregisters a key. Please, only call this in init functions!
		"""
		try: del self._keys[name]
		except KeyError: pass
	#enddef

	def registerStruct(self, classRef):
		"""
		Method to register a struct as allowable for being a substruct of this.
		"""
		try: classRef.typeName
		except AttributeError: classRef.typeName = classRef.__name__.lower()
		self._structs[classRef.typeName] = classRef
	#enddef

	def __unicode__(self):
		"""
		Write struct to RPL format.
		"""
		# TODO: Write this.
		pass
	#enddef

	def __getitem__(self, key):
		"""
		Return data for key.
		You're allowed to replace this if you require special functionality.
		Just please make sure it all functions logically.
		"""
		# I'm iffy about this, but really, it just means that virual
		# key handling needs an override.
		if key in self._data or key in self._keys:
			x = self
			while x and key not in x._data: x = x.parent()
			if x:
				# Verify that typing is the same between this ancestor and itself
				# This is just a quick check for speed.
				if (key not in self._keys or (key in x._keys and
					x._keys[key][0]._source == self._keys[key][0]._source
				)): return x._data[key]

				# Otherwise, run the verification
				return self._keys[key][0].verify(x._data[key])
			elif key in self._keys and self._keys[key][1] is not None:
				self._data[key] = self._keys[key][1]
				return self._data[key]
			#endif
		#endif
		raise RPLError('No key "%s" in "%s"' % (key, self._name))
	#enddef

	def __setitem__(self, key, value):
		"""
		Set data for key, verifying and casting as necessary.
		You're allowed to replace this if you require special functionality.
		Just please make sure it all functions logically.
		"""
		if key in self._keys:
			# Reference's types are lazily checked
			if isinstance(value, RPLRef): self._data[key] = value
			else: self._data[key] = self._keys[key][0].verify(value)
		else: raise RPLError('"%s" has no key "%s".' % (self.typeName, key))
	#enddef

	def prepareForProc(self, cloneName, cloneKey, cloneRef):
		"""
		Stub: If the struct is going to deal in cloneables, it should implement this.
		When a proc is called, this will be called on every struct telling it
		what cloneable (by name and key) it needs to make preparations for. This
		function should make those preparations.
		"""
		pass
	#enddef

	def basic(self, callers=[]):
		"""
		Stub. Return basic data (name by default).
		In your documentation, please state if this will always return the name
		by some necessity, or if in the future it may change to an actual value.
		"""
		return Literal(self._name)
	#enddef

	@classmethod
	def template(rpl=None, tabs=""):
		"""
		This tries to guess a template for the struct, but you should replace it.
		Obviously, nothing will be loaded when this is called.
		In the spirit of Python, don't worry about adding a trailing newline.
		"""
		ret = u"%s%s {\n" % (tabs, self.typeName)
		tabs += "\t"
		for x in self._keys:
			if self._keys[x][1] is None:
				ret += u"%s%s: fill this in...\n" % (tabs, x)
			else:
				ret += u"%s#%s: %s\n" % (tabs, x, unicode(self._keys[x][1]))
			#endif
		#endfor
		for x in self._structs:
			ret += self._structs[x].template(rpl, tabs) + "\n"
		#endfor
		return ret + tabs[0:-1] + "}"
	#enddef

	def name(self): return self._name
	def parent(self): return self._parent

	def __len__(self):
		"""
		Return number of children (including keys).
		"""
		return len(self._data) + len(self._children)
	#enddef

	def __nonzero__(self): return True
	def __iter__(self): return self._children.itervalues()
	def child(self, name): return self._children[name]
	def iterkeys(self): return iter(self._data)
	def recurse(self): return RecurseIter(self._children)

	def childrenByType(self, typeName):
		"""
		Return list of children that fit the given typeName
		typeName may be a string or the class that it will grab the string from
		"""
		if issubclass(typeName, RPLStruct): typeName = typeName.typeName
		ret = []
		for x in self._children.itervalues():
			if x.typeName == typeName: ret.append(x)
		#endfor
		return ret
	#enddef

	def get(self, data):
		"""
		These handle references in terms of cloneables, ensuring "this" refers
		the the appropriate instance rather than the uninstanced struct.
		"""
		if isinstance(data, RPLRef): return data.get(this=self)
		elif type(data) in [str, unicode]: return self.get(self[data])
		else: return data.get()
	#endif

	def set(self, data, val):
		"""
		These handle references in terms of cloneables, ensuring "this" refers
		the the appropriate instance rather than the uninstanced struct.
		"""
		if isinstance(data, RPLRef): return data.set(val, this=self)
		else: return data.set(val)
	#endif

	def __deepcopy__(self, memo={}):
		ret = object.__new__(self.__class__)
		for k, x in self.__dict__.iteritems():
			if k in self._nocopy or callable(x): setattr(ret, k, x)
			else: setattr(ret, k, copy.deepcopy(x))
		#endfor
		return ret
	#enddef
#endclass

# Well if that isn't a confusing name~ Sorry :(
class StructRPL(RPLStruct):
	"""
	The header, as it were, for RPL files.
	"""
	# Caps for consistency with "ROM"
	# Your own types should not have caps!
	typeName = "RPL"

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		self.registerKey("lib", "[path]*", "[]")
		self.registerKey("include", "[path]*", "[]")
		self.registerKey("help", "[string, [string, string]]+1", "[]")
	#enddef

	def __getitem__(self, key):
		# Some virtual redirects
		virtuals = {"libs": "lib", "includes": "include"}
		if key in virtuals: key = virtuals[key]
		return RPLStruct.__getitem__(self, key)
	#enddef

	def __setitem__(self, key, value):
		# Some virtual redirects
		virtuals = {"libs": "lib", "includes": "include"}
		if key in virtuals: key = virtuals[key]
		RPLStruct.__setitem__(self, key, value)
	#enddef

	@classmethod
	def template(rpl=None, tabs=""):
		if rpl is None:
			return  (
				u"%(tabs)s%(type)s {\n"
				"%(tabs)s\tlib: std\n"
				"%(tabs)s\thelp: [\n"
				'%(tabs)s\t\t"My RPL for something or other."\n'
				'%(tabs)s\t\t#[somedef, "What it does"]\n'
				"%(tabs)s\t]\n"
				"}"
			) % {
				"tabs": tabs,
				"type": self.typeName
			}
		else:
			ret = "%sRPL {\n" % tabs
			libs = rpl.alreadyLoaded[3:]
			if len(libs) > 1: ret += "%s\tlibs: [%s]\n" % (tabs, ", ".join(libs))
			elif len(libs) == 1: ret += "%s\tlib: %s\n" % (tabs, libs[0])
			if len(rpl.alreadyIncluded) > 1:
				ret += "%s\tincludes: [%s]\n" % (tabs, ", ".join(rpl.alreadyIncluded))
			elif len(rpl.alreadyIncluded) == 1:
				ret += "%s\tinclude: %s\n" % (tabs, rpl.alreadyIncluded[0])
			#endif
			return ret + "%s}" % tabs
		#endif
	#enddef
#endclass

class ROM(RPLStruct):
	"""
	Performs verifications against the file that you're modifying.
	"""

	# No other struct should have caps in their names
	# You could call this a backwards compatibility thing...
	typeName = "ROM"

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		self.registerKey("id", "[string]*", "")
		self.registerKey("name", "[string]*", "")
		self.registerKey("crc32", "hexnum|[[hexnum, hexnum|range]*0]*", "[]")
		self.registerKey("text", "[[string, hexnum]]*", "[]")

		self._id_location   = 0
		self._id_format     = {
			"length":  0,      # 0 for non-fixed length
			"padding": "\0",   # Char to pad with
			"align":   "left", # How to align the name, usually left
		}
		self._name_location = 0
		self._name_format   = {
			"length":  0,      # 0 for non-fixed length
			"padding": "\0",   # Char to pad with
			"align":   "left", # How to align the name, usually left
		}
	#enddef

	@staticmethod
	def _format(string, form):
		if form["length"] == 0: return string
		string = string[0:form["length"]]
		padding = form["padding"] * (form["length"] - len(string))
		if form["align"] == "left": return string + padding
		else: return padding + string
	#enddef

	@staticmethod
	def getCRC(stream, rang):
		"""
		Return CRC of data in stream referred to by the range of addresses.
		"""
		seek, read = None, None
		direction, crc = 0, 0
		stream.seek(0, 2)
		eof = stream.tell()
		if isinstance(rang, Number):
			# Address to EOF
			rang = list(range(rang.get(), eof))
		else:
			rang = [x.get() for x in rang.get()]
			try:
				if rang[-1] == "e":
					if rang[-2] == "b": r = list(range(0, eof))
					else: r = list(range(rang[-2], eof))
					rang = rang[0:-1] + r
				elif rang[0] == "e":
					if rang[1] == "b": r = list(range(eof, -1, -1))
					else: r = list(range(eof, rang[1] - 1, -1))
					rang = r + rang[1:]
				elif rang[-1] == "b":
					# By the time it checks b's, e will have already handled b:e and e:b
					rang = rang[0:-1] + list(range(rang[-2], -1, -1))
				elif rang[0] == "b":
					rang = list(range(0, rang[1])) + rang[1:]
				#endif
			except TypeError:
				raise RPLError("e and b must only be at the beginning or "
					"end of a CRC32 range check. Do not use other letters."
				)
			#endtry
		#endif

		# Adding "END" here is a bit of a trick to commit the crc creation on
		# the last iteration.
		for x in rang + ["END"]:
			if read:
				isPos = seek + read == x
				isNeg = seek - read == x
			#endif
			if read and ((isPos and direction != -1) or (isNeg and direction != 1)):
				read += 1
				if isPos: direction = 1
				else: direction = -1
			else:
				if read:
					if direction == -1:
						stream.seek(seek - read + 1)
						data = stream.read(read)
						data = data[::-1]
					else:
						stream.seek(seek)
						data = stream.read(read)
					#endif
					crc = crc32(data, crc) & 0xFFFFFFFF
				#endif
				if type(x) in [int, long]: seek, read = x, 1
				else: seek, read = None, None
			#endif
		#endfor
		return crc
	#enddef

	def validate(self, rom):
		"""
		Validate contents of rom file
		"""
		failed = []
		# Create all IDs and names. Grab max lengths
		ids, names, max_id_len, max_name_len = [], [], 0, 0
		for x in self["id"].get():
			ids.append(ROM._format(x.get(), self._id_format))
			max_id_len = max(len(ids[-1]), max_id_len)
		#endfor
		for x in self["name"].get():
			names.append(ROM._format(x.get(), self._name_format))
			max_name_len = max(len(names[-1]), max_name_len)
		#endfor

		# Verify ID
		if ids:
			rom.seek(self._id_location)
			tmp = rom.read(max_id_len)
			ok = False
			for x in ids:
				if tmp[0:len(x)] == x:
					ok = True
					break
				#endif
			#endfor
			if not ok: failed.append("id")
		#endif

		# Verify name
		if names:
			rom.seek(self._name_location)
			tmp = rom.read(max_name_len)
			ok = False
			for x in names:
				if tmp[0:len(x)] == x:
					ok = True
					break
				#endif
			#endfor
			if not ok: failed.append("name")
		#endif

		# Verify text
		for idx, x in enumerate(self["text"].get()):
			x = x.get()
			rom.seek(x[1].get())
			text = x[0].get()
			if rom.read(len(text)) != text:
				failed.append(("text", idx))
			#endif
		#endfor

		# Verify crc32s
		if isinstance(self["crc32"], Number):
			rom.seek(0)
			if crc32(rom.read()) & 0xFFFFFFFF != self["crc32"].get():
				failed.append(("crc32", 0))
			#endif
		else:
			for idx, x in enumerate(self["crc32"].get()):
				x = x.get()
				if getCRC(rom, x[1]) != x[0].get():
					failed.append(("crc32", idx))
				#endif
			#endfor
		#endif
		return failed
	#enddef

	@classmethod
	def template(rpl=None, tabs=""):
		return (
			"%(tabs)sROM {"
			"%(tabs)s\t# Do some verifications here\n"
			"%(tabs)s}" % {"tabs": tabs}
		)
	#enddef
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
		return new
	#enddef

#	def validate(self):
#		"""
#		Overwrite this cause Static accepts all keys.
#		"""
#		return True
#	#enddef

	def __setitem__(self, key, value):
		"""
		Overwrite this cause Static accepts all keys.
		"""
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
		self.registerKey("base", "[string:(b, s, e, begin, start, end), hexnum].", "$000000")
		self.registerKey("file", "path", "")
		self.registerKey("ext", "string", "")
		self.registerKey("export", "bool", "true")
		self.registerKey("import", "bool", "true")

		self._prepared = False
	#enddef

	def __getitem__(self, key):
		if key == "file":
			# Calculate filename
			cur = self
			filename, unk = "", ""
			while cur:
				if "file" in cur._data:
					tmpname = (
						cur._data["file"].getRaw()
						if isinstance(cur._data["file"], Path) else
						Path.convert(cur._data["file"].get())
					)
					filename = tmpname + filename
					if tmpname[0] != "/": break
				elif not (filename or cur._gennedName): unk = "/" + cur._name + unk
				cur = cur._parent
			#endwhile
			if filename: filename = Path(filename)
			else: filename = Path(unk[1:])

			if not filename.hasExt(): filename.setExt(self["ext"].get())

			return filename
		else: return RPLStruct.__getitem__(self, key)
	#enddef

	def base(self, value=None, rom=None, offset=0):
		if value is None: value = self["base"]
		if rom is None: rom = self._rpl.rom

		try: v = value.get()
		except AttributeError: v = value
		if isinstance(value, List):
			rel, base = {
				"b": 0, "begin": 0, "s": 0, "start": 0,
				#"c": 1, "cur": 1, "current": 1,
				"e": 2, "end": 2
			}[v[0].get()], v[1].get()
		elif v in ["b", "s", "begin", "start"]: rel, base = 0, 0
		#elif v in ["c", "cur", "current"]: rel, base = 1, 0
		elif v in ["e", "end"]: rel, base = 2, 0
		else: rel, base = 0, v

		if rom is False: return base, rel
		rom.seek(base + offset, rel)
		return rom.tell()
	#enddef

	def open(self, folder, ext="bin", retName=False, justOpen=False):
		"""
		Helper method for opening files.
		"""
		if not justOpen:
			path = self["file"]
			if not path.hasExt(): path.setExt(ext)
			path = path.get(folder)

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

	def importPrepare(self, rom, folder):
		"""
		Stub. Fill this in to prepare struct before executables run.
		"""
		pass
	#enddef

	def importData(self, rom, folder):
		"""
		Stub. Fill this in to import appropriately.
		"""
		pass
	#enddef

	def exportPrepare(self, rom, folder):
		"""
		Stub. Fill this in to prepare struct before executables run.
		Typically speaking you will want to lazily read from the ROM by
		adding the reads to your __getitem__ statement. This allows things
		to be pulled in in the order necessary, which may not be necessarily
		predictable.
		If the data read from the ROM should not be able to be modified by
		executables you need not worry so much about this, but you should
		still consider your keys potentially modifiable.
		This function should generally just be used for prep. If you're going
		to read anything from the ROM, be really mindful.
		"""
		pass
	#enddef

	def exportData(self, rom, folder):
		"""
		Stub. Fill this in to export appropriately.
		You will generally not need the ROM here, but in the event that you do,
		you can grab it from self._rpl.rom
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

		self._clones = []
		self._nocopy.append("_clones")
	#enddef

	def clone(self):
		new = copy.deepcopy(self)
		new._rpl, new._parent = self._rpl, self._parent
		self._clones.append(new)
		return new
	#enddef

	def __deepcopy__(self, memo={}):
		ret = RPLStruct.__deepcopy__(self)
		delattr(ret, "_clones")
		return ret
	#enddef

	def clones(self): return iter(self._clones)

	def __getitem__(self, key):
		try: self._clones
		except AttributeError: return RPLStruct.__getitem__(self, key)
		else: return List([x[key] for x in self._clones])
	#enddef
#endclass

################################################################################
#################################### RPLRef ####################################
################################################################################
class RPLRef(object):
	"""
	Manages references to other fields.
	"""

	specification = re.compile(r'@?([^.]+)(?:\.([^\[]*))?((?:\[[0-9]+\])*)')
	# Way way ... back; Great great ... grand parent
	heir = re.compile(r'^(?=.)((w*)back_?)?((g*)parent)?$')

	typeName = "reference"

	def __init__(self, rpl, container, mykey, ref, line, char):
		self._rpl = rpl
		self._container = container
		self._mykey = mykey
		self._pos = (line, char)
		self._nocopy = ["_rpl", "_container", "_pos", "_idxs"]

		self._struct, self._key, idxs = self.specification.match(ref).groups()
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
		# Traverses a list to find the requested data within.
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
		"""
		Set referenced value (these things are pointers, y'know).
		"""
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

	def resolve(self): return self.get(retCl=True)

	def proc(self, func, callers=[], clone=None):
		"""
		Used by executables. Runs a procedure over every instance of a clone.
		Or if not cloneable, it runs it over the only instance.
		"""
		point = clone or self.pointer(callers)
		if clone is None and isinstance(point, Cloneable):
			args = (point.name(), self._key, point)
			for x in self._rpl.recurse(): x.prepareForProc(*args)
			for x in point.clones(): self.proc(func, callers, x)
		else:
			# TODO: Better error wording
			if not self._key: raise RPLError("Tried to proc on basic reference.")
			# TODO: Check that I'm doing callers right here. I think it's right
			# but I don't wanna think that hard right now.
			self.getFromIndex(point[self._key], callers).proc(func, callers + [self])
		#endif
	#enddef

	def __deepcopy__(self, memo={}):
		ret = object.__new__(self.__class__)
		for k, x in self.__dict__.iteritems():
			if k in self._nocopy or callable(x): setattr(ret, k, x)
			else: setattr(ret, k, copy.deepcopy(x))
		#endfor
		return ret
	#enddef
#endclass

################################################################################
#################################### RPLData ###################################
################################################################################

class RPLData(object):
	def __init__(self, data=None):
		self._nocopy = []

		if data is not None: self.set(data)
	#enddef

	def get(self): return self._data
	def set(self, data): self._data = data

	def proc(self, func, clone=None):
		"""
		Used by executables. Mostly so that one doesn't have to check if they're
		working with a reference or not.
		"""
		self.set(func(self.get()))
	#enddef

	# You must define these in your own types.
	#def defaultSize(self)       # Returns default size for use by Data struct
	#def serialize(self, **kwargs)         # Return binary form of own data.
	#def unserialize(self, data, **kwargs) # Parse binary data and set to self.

	def __eq__(self, data):
		"""
		Compare data contained in objects.
		"""
		if not isinstance(data, RPLData): data = RPL.parseData(RPL, data)
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

	def resolve(self): return self

	def __deepcopy__(self, memo={}):
		ret = object.__new__(self.__class__)
		for k, x in self.__dict__.iteritems():
			if k in self._nocopy or callable(x): setattr(ret, k, x)
			else: setattr(ret, k, copy.deepcopy(x))
		#endfor
		return ret
	#enddef
#endclass

class String(RPLData):
	"""
	String basic type.
	"""
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
		if not rpad: return rstr
		padside = kwargs["padside"]
		if padside[-6:] == "center":
			split = (ceil if padside[0] == "r" else int)(len(rpad) / 2)
			return rpad[0:split] + rstr + rpad[split:0]
		elif padside == "right": return rstr + rpad
		else: return rpad + rstr
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
	"""
	Literal interpreted type.
	"""
	typeName = "literal"

	badchr = re.compile(r'^[ \t]|[\x00-\x08\x0a-\x1f\x7f-\xff{}\[\],\$@"#\r\n' r"']|[ \t]$")

	def __unicode__(self):
		return self.badchr.sub(String.replOut, self._data)
	#enddef
#endclass

class Path(Literal):
	"""
	Manages slash conversion for paths.
	Note, you can only use relative paths..
	If you need something in a far off directory, add that directory to
	the RPL_INCLUDE_PATH environement variable.
	That variable can have all the strange system-specific crap you want.
	The path standard for RPL is suspiciously Windows-like: you may use
	either / or \ separators, and . as the extension separator.
	If you use a system that doesn't use theses, that's fine, your system's
	will be used in the return value. But you must enter it in the above form.
	"""
	typeName = "path"

	@staticmethod
	def convert(path): return path.replace("\\", "/")

	def set(self, data):
		Literal.set(self, data)
		if not self._data:
			self._data = []
			return
		#endif
		tmp = self._data.replace("\\", "/")
		self._startingSlash = (tmp[0] == "/")
		tmp = tmp.split("/")
		if "." in tmp[-1]: tmp[-1], self._ext = tuple(tmp[-1].rsplit(".", 1))
		else: self._ext = None
		self._data = tmp
	#enddef

	def get(self, folder=[]):
		return os.path.join(*(folder + self._data)) + (os.extsep + self._ext if self._ext else "")
	#enddef

	def getRaw(self): return "/".join(self._data) + ("." + self._ext if self._ext else "")

	def hasExt(self): return bool(self._ext)
	def setExt(self, ext): self._ext = ext
#enddef

class Number(RPLData):
	"""
	Number basic type.
	"""
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
		for i in helper.range(kwargs["size"]):
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
	"""
	HexNum interpreted type.
	"""
	typeName = "hexnum"

	def __unicode__(self): return "$%x" % self._data
#endclass

class List(RPLData):
	"""
	List basic type.
	"""
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
	"""
	Range interpreted type.
	It's a list of numbers and one character literals.
	"""
	typeName = "range"

	def set(self, data):
		if type(data) is not list:
			raise TypeError('Type "%s" expects list.' % self.typeName)
		#endif
		for x in data:
			if not isinstance(x, Number) and (not isinstance(x, Literal)
				or len(x.get()) != 1
			):
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
			elif last is not None:
				lastv = last.get()
				isPos = (d - lastv == 1)
				isNeg = (lastv - d == 1)
				isSame = (lastv == d)
				if not isNeg and negseq:
					ret.append(u"%s-%s" % (negseq[0], negseq[-1]))
					negseq = []
				if not isPos and posseq:
					ret.append(u"%s-%s" % (posseq[0], posseq[-1]))
					posseq = []
				if not isSame and mul:
					ret.append(u"%s*%s" % (mul[0], len(mul)))
					mul = []
				#endif
				if isPos: apd = posseq
				elif isNeg: apd = negseq
				elif isSame: apd = mul
				else:
					ret.append(unicode(x))
					continue
				#endif
				if apd: apd.append(x)
				else: apd += [last, x]
			#endif
			last = x
		#endfor
		if negseq: ret.append(u"%i-%i" % (negseq[0], negseq[-1]))
		elif posseq: ret.append(u"%s-%s" % (posseq[0], posseq[-1]))
		elif mul: ret.append(u"%s*%s" % (mul[0], len(mul)))
		return u":".join(ret)
	#enddef
#endclass

class Enum(RPLData):
	def set(self, data):
		for x in self._enum:
			if data in x[0]:
				self._data = x[1]
				return
			#endif
		#endfor
		raise RPLError('Value %s not in expected set for "%s".'  % (data, self.typeName))
	#enddef

	def __unicode__(self):
		for x in self._enum:
			if self._data == x[1]:
				return x[0][0]
			#endif
		#endfor
		raise RPLError('IMPOSSIBLE ERROR AHHHH "%s"' % self.typeName)
	#endif
#endclass

class Bool(Enum, Literal, Number):
	typeName = "bool"

	_enum = [
		[["true", 1, "1", "on"],   True],
		[["false", 0, "0", "off"], False],
	]

	def set(self, data):
		try: data = data.lower()
		except AttributeError: pass
		Enum.set(self, data)
	#enddef

	def __unicode__(self):
		# This is just faster..and easy
		return "true" if self._data else "false"
	#enddef

	def defaultSize(self): return 1

	def serialize(self, **kwargs):
		self._data = 1 if self._data else 0
		ret = Number.serialize(self, **kwargs)
		self._data = bool(self._data)
		return ret
	#enddef

	def unserialize(self, data, **kwargs):
		# TODO: Should this only accept 0 and 1?
		Number.unserialize(self, data, **kwargs)
		self._data = bool(self._data)
	#enddef
#endclass

class Named(RPLData):
	def set(self, data, types=[]):
		if type(data) in [str, unicode]:
			data = data.lower()
			if data in self._names: self._data = self._names[data]
			else: raise RPLError('No %s name "%s"' % (self.typeName, data))
		else:
			raise RPLError('Type "%s" expects %s.' % (
				self.typeName, helper.list2english(["str", "unicode"] + types, "or")
			))
		#endif
	#enddef

	def __unicode__(self, fmt=u"%s"):
		for x in self._names:
			if self._names[x] == self._data: return unicode(x)
		#endfor
		return fmt % self._data
	#enddef
#endclass

class Size(Named, Number, Literal):
	typeName = "size"

	_names = {
		"byte":   1,
		"short":  2,
		"long":   4,
		"double": 8,
	}

	def set(self, data):
		if type(data) in [int, long]:
			if data <= 0: raise RPLError('Type "%s" expects value > 0.' % self.typeName)
			self._data = data
		else: Named.set(self, data, ["int", "long"])
	#enddef

	def serialize(self, **kwargs):
		return Number.serialize(self, **kwargs)
	#enddef

	def unserialize(self, data, **kwargs):
		Number.unserialize(self, data, **kwargs)
	#enddef
#endclass

################################################################################
##################################### Share ####################################
################################################################################

class Share(object):
	# Store the path and RPL for later, called by share function
	def setup(self, rpl, path): self._rpl, self._path = rpl, path
	# If we're importing, it should read in the file
	# Parsing and distrubution is handled after it's contained in the class
	def read(self): pass
	# Writes the data to the file, as the final stage of exporting.
	def write(self): pass
	# How the data is read in from the ROM is not relevant to this class.
	# Such things should be handled by the struct class. But this should contain
	# whatever it needs to add the data to this class. I suggest an add function
	# specific to this data type.
	#def add(self, *args): pass
	# How the data is writen into the ROM is also handled by the struct class.
	# That is done right away. As opposed to needing to be queued like writing
	# for exporting. This class contains nothing relating to this process.
#endclass
