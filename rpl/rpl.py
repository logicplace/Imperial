#-*- coding:utf-8 -*-
#
# Copyright (C) 2012-2013 Sapphire Becker (http://logicplace.com)
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
import os, re, copy, codecs
import helper
from math import ceil
from zlib import crc32
from collections import OrderedDict as odict

################################################################################
#################################### Helpers ###################################
################################################################################

class RPLError(Exception):
	def __init__(self, error, container=None, key=None, pos=None, verb=True, etype="Error", pre=None):
		# Container can be a string or a RPLStruct.
		# So ensure that the name is used, rather than the repr.
		try: container = container.name
		except AttributeError: pass
		# This variable tells the parser that this already has position
		# information, as some errors during parsing may not add any,
		# and the user should really have some.
		self.positioned = False
		self.container, self.key, self.pos = container, key, pos
		if pre is None:
			pre = ""

			# Form pos string...
			if pos is not None:
				pl = pos[0] is not None and pos[0] != -1
				pc = pos[1] is not None and pos[1] != -1
				if pl and pc: pos = "line %i char %i" % pos
				elif pl: pos = "line %i" % pos[0]
				elif pc: pos = "char %i" % pos[1]
				else: pos = ""
			#endif

			if container:
				if verb: pre = "%s in %s" % (etype, container)
				else: pre = "%s %s" % (etype, container)
				if key is not None: pre += ".%s" % key
				if pos: pre += " (%s)" % pos
				self.positioned = True
			elif key:
				if verb: pre = "%s in key %s" % (etype, key)
				else: pre = "%s key %s" % (etype, key)
				if pos: pre += " (%s)" % pos
				self.positioned = True
			elif pos:
				if verb: pre = "%s at %s" % (etype, pos)
				else: pre = "%s %s" % (etype, pos)
				self.positioned = True
			else: pre = etype
		#endif
		self.args = (pre, error)
	#enddef

	def __unicode__(self): return ": ".join(self.args)
	def __str__(self): return str(unicode(self))
#endclass
class RPLKeyError(RPLError): pass
class RPLBadType(Exception): pass

class RecurseIter(object):
	"""
	Iterator used by both RPL and RPLStruct to recurse their children.
	"""
	def __init__(self, children, parent):
		self.children, self.iter, self.parent = children.itervalues(), None, parent
	#enddef

	def __iter__(self): return self

	def next(self):
		try:
			# This will be None at the beginning and after completing a child.
			if self.iter: return self.iter.next()
			else: raise StopIteration
		except StopIteration:
			# Raised when child has completed. Continue to next child.
			child = self.children.next() # This will raise if we're done
			# Ignore structs that are just pointed to.
			while child.parent != self.parent: child = self.children.next()
			self.iter = child.recurse()
			# This order makes it return itself before returning any of its children
			return child
		#endtry
	#enddef
#endclass

class Share(object):
	# Store the path and RPL for later, called by share function
	def setup(self, rpl, path): self.rpl, self.path = rpl, path

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

class SharedRegistry(Share):
	"""
	Shared registries are an internal system that allows for doing things like
	generating typechecks and verifying defaults only once, and having all
	instances of that class share them. This should speed things up when many
	structs of the same type are used in a RPL.

	Lib developers should never have to interact with this directly.

	Note that this does mean registered keys will not change between instances.
	However, the xkey thing in data structs are not registered keys, they are
	dynamic keys, where "x" is the registered key for it. Take a look at its
	code for more info.
	"""
	def __init__(self): self.ksv, self.new = (odict(), {}, {}), True

	def register(self, func):
		if self.new:
			func()
			self.new = False
		#endif
	#enddef
#endclass

################################################################################
##################################### Main #####################################
################################################################################

class RPLObject(object):
	"""
	Base class for RPL (file/root) and RPLStruct.
	"""
	def __init__(self, top=None, name=None, parent=None):
		"""
		top(RPL): The root, RPL instance.
		name(string): The name of this struct.
		parent(RPLObject): The direct parent of this struct.
			None is the same as the root.
		"""
		# A reference to the top-level RPL class.
		self.rpl = top = top or self
		# Ordered key-value pairs.
		self.data = odict()
		# Ordered children, indexed by struct name.
		self.children = odict()
		# Name of the struct as given by the user or system.
		self.name = name
		# If the name was generated automatically or not.
		self.gennedName = False
		# A reference to the direct parent. None is equivalent to the top level.
		self.parent = parent

		# The ? is here because most file systems don't allow them in names.
		# This may not be the best way to do this but I'd rather not make another system.
		tmp = top.share("?INTERNAL:%s" % (
			self.typeName if hasattr(self, "typeName") else "CLASS:" + self.__class__.__name__
		), SharedRegistry)
		self.keys, self.structs, self.virtuals = tmp.ksv
		tmp.register(self.register)

		# This contains names of attributes that should not be copied in a deep
		# copy. This is to prevent recursion as well as unnecessary copies.
		# You may add your own with self.nocopy.append("name") or
		# self.nocopy += ["name", ...] in the __init__
		self.nocopy = ["rpl", "parent", "keys", "structs", "virtuals"]
	#enddef

	def addChild(self, structType, name):
		"""
		Create a new struct and add it as a child of this one.
		structType(string): The type name of the desired struct to create as
			it is registered. *type* name { ... }
		name(string): The name of the child. type *name* { ... }
		"""
		# Statics are always allowed.
		if structType == "static":
			new = self.rpl.structs[structType](self.rpl, name, self)
			if self == self.rpl: self.children[name] = new
			return new
		#endif

		# But anything else must be registered.
		if structType not in self.structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				structType, "root" if self == self.rpl else self.typeName
			))
		#endif
		new = self.structs[structType](self.rpl, name, self)
		self.children[name] = new
		return new
	#enddef

	def registerStruct(self, classRef):
		"""
		Method to register a struct as allowable for being a substruct of this.
		classRef(RPLStruct): The class of the struct, such as Static.
		"""
		try: classRef.typeName
		except AttributeError:
			raise RPLError(
				"You may not register a struct (%s) without a typeName."
				% classRef.__class__.__name__
			)
		#endtry
		self.structs[classRef.typeName] = classRef
	#enddef

	def unregisterStruct(self, classRef):
		"""
		Unregisters a struct. Please, only call this in register functions!
		classRef(RPLStruct): The class of the struct, such as Static.
		"""
		try: del self.structs[name]
		except KeyError: pass
	#enddef

	def __nonzero__(self): return True
	def __iter__(self): return self.children.itervalues()
	def child(self, name): return self.children[name]
	def recurse(self): return RecurseIter(self.children, self)

	def childrenByType(self, typeName):
		"""
		Return list of children that fit the given typeName.
		typeName may be a string or the class that it will grab the string from.
		"""
		# Grab string name if this was a class.
		try: typeName = typeName.typeName
		except AttributeError: pass

		ret = []
		# Find all *immediate* children with this type.
		for x in self.children.itervalues():
			if x.typeName == typeName: ret.append(x)
		#endfor
		return ret
	#enddef

	def __deepcopy__(self, memo={}):
		# This allows for much quicker clones.
		ret = object.__new__(self.__class__)
		memo["parent"] = ret
		for k, x in self.__dict__.iteritems():
			# Point to functions and things listed in nocopy.
			if k in self.nocopy or callable(x): setattr(ret, k, x)
			# Copy everything else.
			else: setattr(ret, k, copy.deepcopy(x, memo))
		#endfor
		return ret
	#enddef
#enddef

class RPL(RPLObject):
	"""
	The base type for loading and interpreting RPL files.
	Also handles "execution" and what not.
	The commandline and any other programs that may use this system will
	interface with this object.
	"""

	specification = re.compile(
		# Whitespace.
		(r'\s*(?:'
		 # String: Either "etc" or 'etc' no linebreaks inside.
		 r'"([^"\r\n]*)"|'r"'([^'\r\n]*)'|"
		 # Multi-line String: Matches `etc` but multiple in a row
		 # NOTE: This picks up comments and the ` themselves so have to
		 # remove those in processing.
		 r'((?:\s*@?`[^`]*`\s*(?:#.*)?)+)|'
		 # Number or range (verify syntactically correct range later)
		 # That is, any string of numbers, -, *, :, or :c: where c is one
		 # lowercase letter.
		 r'(%(r1)s%(r2)s%(r1)s:\-*+~%(r2)s*(?=[,\]\}#\s]|$))|'
		 # Key: Lowercase letters optionally followed by numbers.
		 # Must be followed by a colon.
		 r'(%(key)s):([ \t]*)|'
		 # Flow Identifier: One of: {}[],
		 r'([{}\[\],])|'
		 # Reference: @StructName.keyname[#][#][#] keyname and indexes are
		 # optional. Indexing and keynames are infinitely contiguous.
		 r'@([^%(lit)s.@]+(?:(?:\.%(key)s)(?:\[[0-9]+\])*)*)|'
		 # Literal: Unquoted string or struct name/type.
		 r'([^%(lit)s]+)|'
		 # Comment.
		 r'#.*$)'
		) % {
			# Range part 1.
			"r1": r'(?:[0-9',
			# Between these parts, one can add more things to this set.
			# It's used above to add :\-*+~ in one portion.
			# Range part 2.
			"r2": r']|(?<!\w)[a-z](?=:[a-z$0-9])|(?<=[a-z$0-9]:)[a-z](?!\w)|\$[0-9a-fA-F]+)',
			# Invalid characters for a Literal.
			"lit": r'{}\[\],"#\r\n' r"'",
			# Valid key name.
			"key": r'[a-z]+[0-9]*'
		}
	, re.M | re.U)

	# Used to parse a multiline string token into its real data.
	multilineStr = re.compile(r'@?`([^`]*)`\s*(?:#.*)?')

	# For numbers (number and hexnum) and ranges.
	number = re.compile(
		# Must start with a number, or a single letter followed by a :
		(r'(?:%(num)s|[a-z](?=:))'
		 # Range split group.
		 r'(?:'
		 # Can match a range or times here.
		 r'(?:%(bin)s(%(num)s))?'
		 # Must match a split, can either be a number or single letter followed by a :
		 r':(?:%(num)s|[a-z](?=[: ]|$))'
		 r')*'
		 # To be sure we're able to end in a range/times.
		 r'(?:%(bin)s(?:%(num)s))?'
		) % {
			# Binary operators.
			"bin": r'[\-*+~]',
			# Valid forms for a number.
			"num": r'[0-9]+|\$[0-9a-fA-F]+'
		}
	)

	# Quick check for if a number is a range or not.
	isRange = re.compile(r'[:\-*+~]')

	def __init__(self):
		self.types = {}              # Registered data types.
		self.structsByName = {}      # All structs in the file.
		self.sharedDataHandlers = {} # Used by RPL.share.
		self.importing = None        # Used by RPL.share. NOTE: I would like to remove this..
		# Defining these here prevents them from being usable by RPL.lib
		self.alreadyLoaded   = ["helper", "__init__", "rpl"]
		self.alreadyIncluded = []    # <^ These are used by RPL.load.
		# What to include in the default template.
		self.defaultTemplateStructs = ["RPL", "ROM"]
		RPLObject.__init__(self)
		# There are no keys in the root. They are only included in RPLObject due
		# to how the shared registry works.
		del self.keys
	#enddef

	def register(self):
		# Registrations
		self.registerStruct(StructRPL)
		self.registerStruct(ROM)
		self.registerStruct(Static)

		self.registerType(String)
		self.registerType(Literal)
		self.registerType(RefString)
		self.registerType(Path)
		self.registerType(Number)
		self.registerType(HexNum)
		self.registerType(List)
		self.registerType(Range)
		self.registerType(Bool)
		self.registerType(Size)
		self.registerType(Math)
	#enddef

	def parse(self, inFile, onlyCareAboutTypes=[], **kwargs):
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
		There are more basic forms, however, they make up the syntax. Each type
		from then on is derived from one of the above three basic types. These
		are all of the types and their syntax (Name(Comment)):
		Number:                                    1234
		HexNum(Hexadecimal Number):                $12a4B0

		String:                                    "abcdef"
		                                           `abcdef`
		Literal:                                   abcdef
		RefStr(References in String):              @`abcd @Struct.key`

		List:                                      [1, "abc", etc]
		Range(List form: [1,2,3,4,5,5,x,4]):       1-4:5*2:x:4

		Reference(To basic data, or struct):       @SomeStruct
		Reference(To a key's value):               @SomeStruct.key
		Reference(To a value within a key's list): @SomeStruct.key[3][0]

		You may see tests/rpls/rpl.rpl for an example.
		"""
		if kwargs.get("string", False): raw = inFile
		else: raw = helper.readFrom(inFile) # Raw data from file.

		# Prelit allows colons to be inside literals.
		lastLit, prelit = None, "" # Helpers for literal forming.
		currentKey = None          # What key the next value is for.
		currentStruct = None       # What struct we are currently parsing.
		counts = {}                # How many of a certain struct type we've enountered.
		parents = []               # Current hierarchy of structs and lists.
		notCaring = False          # Used for onlyCaseAboutTypes.

		for token in RPL.specification.finditer(raw):
			groups = token.groups() # Used later.
			dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = groups

			sstr = dstr or sstr # Double or single quoted string.
			# (type, value) to add; error to throw; skip list childs' instantiations.
			add, error, skipSubInst = None, None, False

			# Find the position (used for ref and errors).
			pos = token.start()
			# Line and character numbers are 1-based. (Because gedit is 1-based. o/ )
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
					# Otherwise this might be a struct head.
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
							# Extract type and name.
							structType = structHead[0]
							# Keep a count per type for generated names.
							counts[structType] = counts.get(structType, -1) + 1
							if len(structHead) == 2: structName, genned = structHead[1], False
							else:
								# Form name from type + incrimenter.
								# This commented part is effectively what that loop did,
								# but I don't know why I even had it in the first place?
								#counts[structType] += len(self.structsByName)
								structName = "%s%i" % (structType, counts[structType])
								genned = True
							#endif

							if helper.oneOfIn(".@", structName):
								raise RPLError("Struct name must not contain periods or at signs.")
							#endif

							if structName in self.structsByName and not kwargs.get("dupNames", False):
								raise RPLError('Struct name "%s" is already taken.' % structName)
							else:
								# TODO: This will die on substructs.
								notCaring = onlyCareAboutTypes and structType not in onlyCareAboutTypes
								self.structsByName[structName] = currentStruct = (
									currentStruct if currentStruct else self
								).addChild(structType, structName)
								currentStruct.gennedName = genned
							#endif
						#endif
					elif flow == "}":
						# Close struct
						if currentStruct is None: raise RPLError("} without a {.")
						elif parents: raise RPLError("Unclosed list.")
						elif currentKey is not None:
							raise RPLError("Key with no value. (Above here!)")
						#endif

						if isinstance(currentStruct, StructRPL):
							self.load(currentStruct, onlyCareAboutTypes)
						#endif
						currentStruct = currentStruct.parent
					elif flow == "[":
						# Begins list
						parents.append([])
					elif flow == "]":
						# End list
						if parents:
							add = ("list", parents.pop())
							skipSubInst = True
						else: raise RPLError("] without a [.")
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

				if not lit and lastLit:
					raise RPLError("Literal with no purpose: %s" % lastLit)
				#endif

				if add:
					dtype = add[0]
					val = self.parseCreate(add, currentStruct, currentKey, line, char, skipSubInst)

					if parents:
						parents[-1].append(val)
					elif currentStruct and currentKey:
						if not notCaring: currentStruct[currentKey] = val
						currentKey = None
					else:
						error = "Unused " + dtype
					#endif
				#endif
			except RPLError as err:
				if err.positioned: raise
				raise RPLError(err.args[1], pos=(line, char))
			#endtry
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
			val = RPLRef(val, self, currentStruct, currentKey, line, char)
		elif skipSubInst: val = self.wrap(add[0], add[1], currentStruct, currentKey, line, char)
		else:
			# So I don't have to have two branches doing the same thing we
			# regard the data as a list for now, and change it back after.
			if type(val) is not list: nl, val = True, [add]
			else: nl = False
			val = [self.wrap(x[0], x[1], currentStruct, currentKey, line, char) for x in val]
			if nl: val = val[0]
			else: val = self.wrap(dtype, val, currentStruct, currentKey, line, char)
		#endif

		return val
	#enddef

	@staticmethod
	def numOrHex(num):
		# Used by range parsing to make my life easier.
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
		# pp helps decide the returned form.
		pp = type(data) is tuple
		if pp: dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = data
		else:
			if data == "":
				dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = (
					None, None, None, None, None, None, None, None, ""
				)
			else:
				try: dstr, sstr, mstr, num, key, afterkey, flow, ref, lit = RPL.specification.match(data).groups()
				except AttributeError:
					raise RPLError(
						"Syntax error in data: %s" % data,
						currentStruct, currentKey, (line, char)
					)
				#endtry
			#endif
		#endif
		sstr = dstr or sstr

		add = None

		if ref: add = ("reference", ref)
		elif sstr: add = ("string", sstr)
		elif mstr:
			# Need to remove all `s and comments
			add = ("refstr" if mstr[0] == "@" else "string", "".join(RPL.multilineStr.findall(mstr)))
		elif num:
			if not RPL.number.match(num):
				raise RPLError("Invalid range formatting.")
			elif RPL.isRange.search(num):
				# Range
				numList = []
				# Range commands are separated by colons.
				ranges = num.split(":")

				for r in ranges:
					bounds = r.split("-") # Inclusive range.
					times = r.split("*")  # Repetition.
					inc = r.split("+")    # So many forward.
					dec = r.split("~")    # So many backward.
					if len(bounds) == 2:
						# Left Type, Left...etc.
						lt, l = RPL.numOrHex(bounds[0])
						rt, r = RPL.numOrHex(bounds[1])
						numList += [(lt, l)] + [("number", x) for x in (
							list(range(l + 1, r)) if l < r else list(range(l - 1, r, -1))
						)] + [(rt, r)]
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
					# Single character literal. Sometimes called a token.
					elif r in "abcdefghijklmnopqrstuvwxyz":
						numList.append(("literal", r))
					# Otherwise it has to be a number.
					else: numList.append(RPL.numOrHex(r))
				#endfor

				add = ("range", numList)
			elif num[0] == "$":
				# Hexadecimal number.
				add = ("hexnum", int(num[1:], 16))
			else:
				# Number.
				add = ("number", int(num))
			#endif
		elif lit is not None:
			add = ("literal", lit.strip())
		elif not pp and flow == "[":
			# Only parse lists when a string is passed.
			# (Otherwise it's just the one token..)
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
		elif pp: raise RPLError("Invalid data.", currentStruct, currentKey, (line, char))
		else: raise RPLError("Invalid data: %s" % data, currentStruct, currentKey, (line, char))

		if add:
			if raw: return add[1]
			elif pp: return add
			else: return self.parseCreate(add, currentStruct, currentKey, line, char)
		elif pp: raise RPLError("Error parsing data.", currentStruct, currentKey, (line, char))
		else: raise RPLError("Error parsing data: %s" % data, currentStruct, currentKey, (line, char))
	#endif

	def load(self, struct, libsOnly=False):
		"""
		Loads includes and libs. Used by parse, probably should not need to
		use it directly. (But if you generate a RPL struct for some reason,
		this isn't called when you append it, so you can do it manually then.)
		struct(StructRPL): The struct to act from.
		libOnly(bool): Only import libs, do not do includes.
		"""
		# Load libraries (python modules defining struct and data types).
		for lib in struct["lib"].list():
			lib = lib.string()
			if lib in self.alreadyLoaded: continue
			tmp = __import__(lib, globals(), locals())
			tmp.register(self)
			self.alreadyLoaded.append(lib)
		#endfor

		if libsOnly: return

		if "RPL_INCLUDE_PATH" in os.environ:
			includePaths = set(["."] + os.environ["RPL_INCLUDE_PATH"].split(";"))
		else: includePaths = ["."]

		# Include other RPLs (this should inherently handle RPL structs
		# in the included files).
		for incl in struct["include"].list():
			incl = incl.string()
			if incl in self.alreadyIncluded: continue
			for path in includePaths:
				path = os.path.join(path, incl)
				tmp = None
				try: tmp = codecs.open(path, encoding="utf-8", mode="r")
				except IOError as err:
					if err.errno == 2:
						# File not found. Attempt with .rpl extension...
						try: tmp = codecs.open(path + os.extsep + "rpl", encoding="utf-8", mode="r")
						except IOError as err:
							# File not found. We'll check another include path...
							if err.errno == 2: continue
							else: raise RPLError("Could not include file %s: %s" % (path, err.strerror))
						#endtry
					else: raise RPLError("Could not include file %s: %s" % (path, err.strerror))
				#endtry

				if tmp:
					# Do this first so it can't include itself recursively.
					self.alreadyIncluded.append(incl)
					self.parse(tmp)
					tmp.close()
					break
				#endif
			#endfor
			if tmp is None: raise RPLError("Could not find file %s" % path)
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

	def __unicode__(self, pretty=True):
		"""
		Write self as an RPL file.
		Obviously this returns a string and does not actually write a file.
		"""
		ret = u""
		n = u"\n\n" if pretty else u""
		for child in self: ret += child.__unicode__(pretty) + n
		return ret
	#enddef

	def registerType(self, classRef):
		"""
		Method to register a custom type.
		"""
		self.types[classRef.typeName] = classRef
	#enddef

	def template(self, structs=[]):
		"""
		Output the template. By default this is RPL and ROM.
		"""
		return (
			"# Description\n"
			"# Author: Your Name\n"
			"\n\n".join([x.template(self) for x in structs or self.defaultTemplateStructs])
		)
	#enddef

	def wantPort(self, x, what):
		# Runtime may request only certain structs be used. All children of
		# the given names are also used. This recurses to find if it (x) or
		# any parent was requested.
		return x and (not what or x.name in what or self.wantPort(x.parent, what))
	#enddef

	def importData(self, rom, folder, what=[], nocreate=False):
		"""
		Import data from folder into the given ROM according to what.
		rom      is the location of the binary ROM file.
		folder   is the base folder for the project files.
		what     is a list of names requested for use.
		nocreate prevents the rom from being written to or created.
		"""
		self.rom = rom = helper.stream(helper.FakeStream() if nocreate else rom)
		self.importing = True
		self.requested = what
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Doing this in a two step process ensures proper ordering when
		# importing shared data.

		# Do preparations.
		toImport = []
		for x in self.recurse():
			if x.manage(what):
				try: x.importPrepare
				except AttributeError: pass
				else: x.importPrepare(rom, lfolder)
				toImport.append(x)
			#endif
		#endfor

		# Now that everything is suspended in python, we can commit imports.
		if not nocreate:
			for x in toImport:
				try: x.importData
				except AttributeError: pass
				else: x.importData(rom, lfolder)
			#endfor
		#endif

		rom.close()
		# Reset this to none, because python might still be running.
		self.importing = self.rom = None
		del self.requested
	#enddef

	def exportData(self, rom, folder, what=[], nocreate=False):
		"""
		Export data from rom into folder according to what.
		rom      is the location of the binary ROM file.
		folder   is the base folder for the project files.
		what     is a list of names requested for execution.
		nocreate prevents the rom from being written to or created.
		"""
		self.rom = rom = helper.stream(helper.FakeStream() if nocreate else rom)
		self.importing = False
		self.requested = what
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Exports are lazily drawn from the ROM, as there is no ordering
		# necessary since it's all based on fixed positions. Prerequisites are
		# handled properly this way, such as pulling lengths or pointers from
		# other blocks.

		# Do preparations.
		toExport = []
		for x in self.recurse():
			if x.manage(what):
				try: x.exportPrepare
				except AttributeError: pass
				else: x.exportPrepare(rom, lfolder)
				toExport.append(x)
			#endif
		#endfor

		# Now that everything is suspended in python, we can write exports.
		if not nocreate:
			for x in toExport:
				try: x.exportData
				except AttributeError: pass
				else: x.exportData(rom, lfolder)
			for x in self.sharedDataHandlers.itervalues(): x.write()
		#endif

		rom.close()
		# Reset this to none, because python might still be running.
		self.importing = self.rom = None
		del self.requested
	#enddef

	def run(self, folder, what=[]):
		"""
		Running is the idea of working on files alone, without a rom.
		Therefore, it basically works like this:
		[v Pyt] <-- [Reso-]
		[> hon] --> [urces]
		by calling importPrepare then exportData.
		folder   is the base folder for the project files.
		what     is a list of names requested for execution.
		"""
		# ROM is never used.
		self.rom = rom = helper.FakeStream()
		self.importing = True
		self.requested = what
		lfolder = list(os.path.split(os.path.normpath(folder)))

		# Do preparations.
		toExport = []
		for x in self.recurse():
			if x.manage(what):
				try: x.importPrepare
				except AttributeError: pass
				else: x.importPrepare(rom, lfolder)
				toExport.append(x)
			#endif
		#endfor

		self.importing = False
		# Now that everything is suspended in python, we can write exports.
		for x in toExport:
			try: x.exportData
			except AttributeError: pass
			else: x.exportData(rom, lfolder)
		for x in self.sharedDataHandlers.itervalues(): x.write()

		rom.close()
		# Reset this to none, because python might still be running.
		self.importing = self.rom = None
		del self.requested
	#enddef

	def wrap(self, typeName, value=None, container=None, key=None, line=None, char=None):
		"""
		Wrap a value in its respective RPLData class by type name.
		typeName:  string of the name of a datatype
		value:     value to set
		container: instance of the container for what struct this value was
		           created in.
		key:       key that it was created for.
		line:      line number that the declaration took place on.
		char:      character index that the declatation took place at.
		"""
		if typeName in self.types:
			return self.types[typeName](value, self, container, key, line, char)
		raise RPLError('No type "%s" defined' % typeName)
	#enddef

	def share(self, share, create, *vargs, **kwargs):
		"""
		Return the handle by key (typically filename) of the shared data.
		Instantiates handle if it doesn't exist.
		Structs that point to the same data should modify the same data, in the
		order that they're listed in the RPL.
		This allows multiple structs to address different portions of the same
		tilemap, for example.
		share:   index for the shared data file.
		create:  class used to instantiate the share, if not already created.
		vargs & kwargs: arguments to pass for instantiation.
		"""
		# If it has already been created.
		if share in self.sharedDataHandlers:
			# The type for a class is "type".
			if isinstance(create, type) and not isinstance(self.sharedDataHandlers[share], create):
				raise RPLError('Share of "%s" expected %s but was %s.' % (
					share, create.__name__, self.sharedDataHandlers[share].__class__.__name__
				))
			#endif
			return self.sharedDataHandlers[share]
		# Else we need to create it.
		else:
			tmp = create(*vargs, **kwargs)
			tmp.setup(self, share)
			if self.importing: tmp.read()
			self.sharedDataHandlers[share] = tmp
			return tmp
		#endif
	#enddef

	@staticmethod
	def updateROM(idloc=None, idform=None, nameloc=None, nameform=None, idtype=None, nametype=None):
		"""
		For console libraries, they will want to adjust the offsets for IDs and Names
		in the ROM struct. This makes for some simple verification for RPL authors.
		Call this function to do so.
		idloc:    static address of the ID.
		idform:   format of the ID:
		    length:  static length of the ID.
		    padding: what byte to use for padding.
		    align:   how to align the name, ie. align left will pad the right side.
		nameloc:  static address of the name.
		nameform: same as idform, but for name.
		    length:  default for both is 0
		             0 is unfixed length
		    padding: default for both is $00
		    align:   default for both is left
		idtype:   typecheck string for ID field.
		nametype: typecheck string for name field.
		"""
		if idloc is not None: ROM.id_location = idloc
		if idform is not None:
			for x in idform: ROM.id_format[x] = idform[x]
		#endif

		if nameloc is not None: ROM.name_location = nameloc
		if nameloc is not None:
			for x in nameform: ROM.name_format[x] = nameform[x]
		#endif

		# These are actually applied later.
		if idtype is not None: ROM.id_type = idtype
		if nametype is not None: ROM.name_type = nametype
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
	 * all  - Any type allowed.
	 * [type, ...] - List containing specific types.
	 * |    - Boolean or.
	 * []*  - Can either be just the contents, or a list containing multiple
	          of that content. Multipart lists treat commas like | when
	          checking against just the contents.
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
	 * ^    - Recurse parent list at this point.
	"""

	specification = re.compile(
		# Whitespace.
		r'\s+|'
		# List forms.
		r'([\[\]*+!~.|,])(?:(?<=[*!~.+])([0-9]+))?|'
		r'(?:'
			# Type (or all)
			r'([^\s\[\]*+!~.|,^:]+)'
			# Allowed types (optional).
			r'('
				r':\((?:(?:"[^"]+"|'
				r"'[^']'|[^'"
				r'",)]+)\s*,?\s*)+\)'
			r')?|'
			# Recursion operator.
			r'(\^)'
		r')'
	)

	def __init__(self, rplOrPreparsed, name=None, syntax=None):
		"""
		You can either pass preparsed data or a string that needs to be parsed.
		The former is just for testing, really.
		Form 1:
		    rplOrPreparsed: reference to top level RPL instance.
		    name:           (key) name to use for reporting errors.
		    syntax:         the typecheck syntax to parse.
		Form 2:
		    rplOrPreparsed: parsed tokens as instances of RPLTC*
		"""
		self.source = ""
		# Handle preparsed data
		if name is None and syntax is None: self.root = rplOrPreparsed
		elif name is None or syntax is None:
			raise TypeError("__init__() takes either 1 or 3 arguments (2 given)")
		# Handle unparsed data
		else: self.root = self.__parse(rplOrPreparsed, name, syntax)
	#enddef

	def __parse(self, rpl, name, syntax):
		"""
		Parses a typecheck string. See class's docstring for the specification.
		This function is only meant to be used by RPLTypeCheck itself.
		rpl:    reference to the top level RPL instance.
		name:   (key) name to use for reporting errors.
		syntax: the typecheck syntax to parse.
		"""
		# FYI: This is one of the most ridiculous looking parsers I've written.
		lastType = None
		remain = None
		parents = []
		lastWasListEnd, lastWasRep = False, False
		self.source = syntax
		for token in RPLTypeCheck.specification.finditer(syntax):
			try:
				flow, num, tName, discrete, recurse = token.groups()
				if num: num = int(num)

				if recurse: tName = recurse
				# Tranform into a list form and prase entirely.
				# This allows for using commas in quoted strings.
				if discrete: discrete = rpl.parseData("[" + discrete[2:-1] + "]", raw=True)

				if tName: lastType = RPLTCData(rpl, tName, discrete)
				elif flow == "[":
					if lastType is None:
						# New list, append to list/parents
						tmp = ["list", []]
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
							# The `.pop()` here executes before the `[-1] =`
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
						tmp = ["or", [remain]]
						if not len(parents): parents.append(tmp)
						elif parents[-1][0] == "list":
							parents[-1][1][-1] = tmp
							parents.append(tmp)
						#endif
					elif len(parents) and parents[-1][0] == "or":
						parents[-1][1].append(lastType)
					else:
						# New OR, append to list/parents
						tmp = ["or", [lastType]]
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
							# The `.pop()` here executes before the `[-1] =`
							parents[-1][1][-1] = RPLTCOr(parents.pop()[1])
						#endif
					except IndexError:
						raise RPLError("Comma only allowed in lists")
					#endtry
				#endif

				if flow != "]": lastWasListEnd = False
				if not flow or flow not in "*+!~.": lastWasRep = False
			except RPLError as err:
				raise RPLError(err.args[1], key=name, pos=(None, token.start()))
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
		try: return self.root.verify(data)
		except RPLError as err:
			raise RPLError(
				err.args[1], err.container, err.key, err.pos,
				etype='Verification failed ("%s" against "%s")' % (unicode(data), self.source)
			)
		#endtry
	#enddef
#endclass

# RPL TypeCheck Data
class RPLTCData(object):
	"""
	Helper class for RPLTypeCheck; contains one type.
	"""
	def __init__(self, rpl, t, discrete=None):
		self.rpl, self.type, self.discrete = rpl, t, discrete
	#enddef

	def verify(self, data, parentList=None):
		# Recursion operator check.
		if self.type == "^":
			if parentList is not None:
				return parentList.verify(data, parentList)
			else: raise RPLError(u"Attempted to recurse at top-level.")
		# References are lazily verified.
		elif data.reference(): return data
		# If it's a struct, we can only return the struct if it's of type reference.
		# Otherwise we should check its basic data.
		elif data.struct():
			if self.type == "reference": return data
			else: data = data.basic()
		# If there is a discrete set of values, verify within that.
		elif self.discrete and data.get() not in self.discrete:
			raise RPLError(u'Value "%s" not allowed in discrete set: %s.' % (
				data.get(), helper.list2english(self.discrete)
			), data.container, data.mykey, data.pos)
		# Check if the given data is always valid.
		elif self.type == "all": return data
		# Otherwise, check the type
		else:
			# If it's a basic type and we want the most basic type, return as is.
			if (data.typeName in ["string", "literal", "refstr"] and self.type == "string"
				or data.typeName in ["number", "hexnum"] and self.type == "number"
				or data.typeName in ["list", "range"] and self.type == "list"
			): return data

			# Otherwise, attempt to convert to the desired type.
			try: return self.rpl.wrap(self.type, data.get())
			except RPLError as err:
				raise RPLError(
					u"Error when recasting subclass: %s" % err.args[1],
					data.container, data.mykey, data.pos
				)
			#endtry
		#endif
	#enddef
#endclass

# RPL TypeCheck List
class RPLTCList(object):
	"""
	Helper class for RPLTypeCheck; contains one list.
	"""
	def __init__(self, l, r="]", num=None):
		self.list, self.repeat, self.num = l, r, num
	def rep(self, r, num): self.repeat, self.num = r, num

	def verify(self, data, parentList=None):
		# Make sure data is a list (if it is 0 or more).
		try: data.list()
		except RPLBadType:
			if self.repeat in "*!~.":
				if self.num is not None:
					# Select only the given index to compare.
					if self.num >= len(self.list):
						raise RPLError(u"Index not in list.")
					#endif
					tmp = self.list[self.num].verify(data)
					if self.repeat in "*!": return List([tmp])
					else: return tmp
				#endif

				# This seems like strange form but it's the only logical form
				# in my mind. This implies [A,B]* is A|B|[A,B]+
				# Using * on a multipart list is a little odd to begin with.
				for x in self.list:
					try:
						tmp = x.verify(data)
						if self.repeat in "*!": return List([tmp])
						else: return tmp
					except RPLError: pass
				#endfor
				raise RPLError(
					u"No permuation of single list data worked.",
					data.container, data.mykey, data.pos
				)
			else: raise RPLError(u"Expected list.", data.container, data.mykey, data.pos)
		#endif

		# Check lengths
		d = data.get()
		if self.repeat in "+*":
			if self.repeat == "+" and self.num is not None:
				# Number of non-repeating elements
				diff = len(self.list) - self.num
				if len(d) < diff or (len(d)-diff) % self.num:
					raise RPLError(
						u"Invalid list length.",
						data.container, data.mykey, data.pos
					)
				#endif
				mod = (lambda(i): i if i < diff else ((i-diff) % self.num) + diff)
			elif (len(d) % len(self.list)) == 0:
				mod = (lambda(i): i % len(self.list))
			else:
				raise RPLError(
					u"Invalid list length.",
					data.container, data.mykey, data.pos
				)
			#endif
		elif len(d) == len(self.list):
			mod = (lambda(i): i)
		else:
			raise RPLError(
				u"Invalid list length.",
				data.container, data.mykey, data.pos
			)
		#endif

		# Loop through list contents to check them all
		nd = []
		for i, x in enumerate(d):
			nd.append(self.list[mod(i)].verify(d[i], self))
		#endfor

		return List(nd) if d != nd else data
	#enddef
#endclass

# RPL TypeCheck Or
class RPLTCOr(object):
	"""
	Helper class for RPLTypeCheck; contains one OR set.
	"""
	def __init__(self, orSet): self.orSet = orSet

	def verify(self, data, parentList=None):
		for x in self.orSet:
			try: return x.verify(data, parentList)
			except RPLError: pass
		#endfor
		raise RPLError(
			u"Matched no options.",
			data.container, data.mykey, data.pos
		)
	#enddef
#endclass

################################################################################
################################### RPLStruct ##################################
################################################################################
class RPLStruct(RPLObject):
	"""
	Base class for a struct.
	When making your own struct type, inherit from this, or a subclass of it.
	There are more specific general structs below that will likely be more
	fitting than inheriting this directly.
	"""

	# Be sure to define typeName here in your own subclasses!
	sizeFieldType = "count" # Can be count or len, used for data structs' size field.

	def __init__(self, rpl, name, parent=None):
		# Be sure to call this in your own subclasses!
		RPLObject.__init__(self, rpl, name, parent)
		self.clones = []
		self.nocopy += ["clones"]
		# data and format structs set this value to false if they are going to
		# manage it. This prevents the system from calling functions that will
		# be called manually by those classes.
		self.unmanaged = True
	#enddef

	def manage(self, requested):
		"""
		The system calls this to see whether or not it should consider this
		struct for processing.
		This can use any manner of heuristics to do so. For most structs, it
		will just need this basic form, of ensuring it is managed by the system
		and also that it was requested by the user.
		requested: a list of names that were requested for inclusion.
		"""
		return self.unmanaged and (not requested or self.rpl.wantPort(self, requested))
	#enddef

	def register(self):
		"""
		Fill this in with key and substruct un/registrations.
		Call the parent struct's register function to use its registrations.
		"""
		pass
	#enddef

	def registerKey(self, name, typeStr, default=None):
		"""
		Register a key by name with type and default.
		name:    name of key.
		typeStr: syntax for typechecking.
		default: default value to use if one is not set. If this is None (omitted),
		         then the key is required. This is a string that will be parsed
		         as RPLData.
		"""
		check = RPLTypeCheck(self.rpl, name, typeStr)
		if default is not None:
			default = self.rpl.parseData(default)
			# Try to verify, so it can adjust typing
			try: default = check.verify(default)
			# But if it fails, we should trust the programmer knows what they want..
			except RPLError: pass
		#endif
		self.keys[name] = [check, default]
	#enddef

	def unregisterKey(self, name):
		"""
		Unregisters a key. Please, only call this in register functions!
		"""
		try: del self.keys[name]
		except KeyError: pass

		try: del self.virtuals[name]
		except KeyError: pass
	#enddef

	def registerVirtual(self, virtualName, realName):
		"""
		Register an alias for the given key.
		"""
		self.virtuals[virtualName] = realName
	#enddef

	def __unicode__(self, pretty=True, tabs=u""):
		"""
		Write struct to RPL format.
		"""
		if not pretty: tabs = u""
		n = u"\n" if pretty else u""
		nc = u"\n" if pretty else u","
		sp = u" " if pretty else u""
		ret = u"%s%s %s%s{%s" % (tabs, self.typeName, self.name, sp, n)
		if pretty: tabs += u"\t"
		for key, val in self.data.iteritems():
			ret += u"%s%s:%s%s" % (tabs, key, sp, unicode(val))
			# Only add a comma if one isn't there already.
			if pretty or ret[-1] != ",": ret += nc
		#endfor

		for child in self: ret += n + child.__unicode__(pretty, tabs) + n
		return ret + "}"
	#enddef

	def __getitem__(self, key):
		"""
		Return data for key.
		You're allowed to replace this if you require special functionality.
		Just please make sure it all functions logically.
		"""
		if self.clones: return List([x[key] for x in self.clones])

		# We only want to check virtuals if we have to.
		if key not in self.data and key not in self.keys and key in self.virtuals: key = self.virtuals[key]
		if key in self.data or key in self.keys:
			if key in self.data: data = self.data[key]
			else:
				x, data = self.parent, None
				while x and x != self.rpl:
					try:
						data = x[key]
						break
					except RPLKeyError as err: x = x.parent
				#endwhile
			#endif

			if data is not None:
				# Verify that typing is the same between this ancestor and itself
				# This is just a quick check for speed.
				if (key not in self.keys or (data.container is not None and
					key in data.container.keys and
					data.container.keys[key][0].source == self.keys[key][0].source
				)): return data

				# Otherwise, run the verification
				return self.keys[key][0].verify(data)
			elif key in self.keys and self.keys[key][1] is not None:
				self.data[key] = copy.deepcopy(self.keys[key][1], {"parent": self})
				return self.data[key]
			#endif
		#endif
		raise RPLKeyError('No key "%s" in "%s"' % (key, self.name))
	#enddef

	def __setitem__(self, key, value):
		"""
		Set data for key, verifying and casting as necessary.
		You're allowed to replace this if you require special functionality.
		Just please make sure it all functions logically.
		"""
		if key in self.virtuals: key = self.virtuals[key]
		if key in self.keys:
			# Reference's types are lazily checked
			if value.reference(): self.data[key] = value
			else: self.data[key] = self.keys[key][0].verify(value)
		else: raise RPLKeyError('"%s" has no key "%s".' % (self.typeName, key))
	#enddef

	def basic(self, callers=[]):
		"""
		Stub. Return basic data (name by default).
		In your documentation, please state if this will always return the name
		by some necessity, or if in the future it may change to an actual value.
		"""
		return Literal(self.name)
	#enddef

	@classmethod
	def template(rpl=None, tabs=""):
		"""
		This tries to guess a template for the struct, but you should replace it.
		Obviously, nothing will be loaded when this is called.
		In the spirit of Python, don't worry about adding a trailing newline.
		rpl:   reference to top level RPL instance.
		tabs:  current tab string. Initial call shouldn't pass this.
		"""
		# Head.
		ret = u"%s%s {\n" % (tabs, self.typeName)
		tabs += "\t"

		# Keys.
		for x in self.keys:
			if self.keys[x][1] is None:
				# Required key with no example data.
				ret += u"%s%s: fill this in...\n" % (tabs, x)
			else:
				# Add commented out default. Allows reader to see what the
				# default is quickly, and if he needs to change it.
				ret += u"%s#%s: %s\n" % (tabs, x, unicode(self.keys[x][1]))
			#endif
		#endfor

		# Include substruct templates.
		for x in self.structs:
			ret += self.structs[x].template(rpl, tabs) + "\n"
		#endfor
		return ret + tabs[0:-1] + "}"
	#enddef

	def __len__(self):
		"""
		Return number of contents (keys + substructs).
		Mostly for testing purposes.
		"""
		return len(self.data) + len(self.children)
	#enddef

	def iterkeys(self): return iter(self.data)

	def get(self, data=None):
		"""
		Retrieves Python data from RPLData with no regard to basic type.
		If data is None or omitted, the struct's basic data is returned.

		Most importantly, struct.get("key") looks nicer to me than struct["key"].get()!
		"""
		# Handle in terms of basic data.
		if data is None: return self.basic().get()

		# Retrieve reference to RPLData from key.
		key = "???"
		if type(data) in [str, unicode]:
			key = data
			data = self[data]
		#endif

		try: data.get
		except AttributeError: raise RPLError("Failed retrieval of %s in %s." % (key, self.name))
		else: return data.get()
	#endif

	def set(self, data, val):
		"""
		Set data to a key or RPLData.
		The typing is either:
		  struct.set(RPLData, Python data)
		  struct.set("key", RPLData)
		"""
		# Set data by key form.
		if type(data) in [str, unicode]:
			if isinstance(val, RPLData): self[data] = val
			else: raise RPLError("Cannot set Python data to a key in this form: %s.%s." % (self.name, data))
		#endif

		# Set data.
		try: data.set
		except AttributeError: raise RPLError("Failed setting data in %s." % (self.name))
		else: return data.set(val)
	#endif

	def resolve(self, data=None):
		"""
		Resolves a reference to the RPLData it points to.
		If data is not a reference, it returns itself.
		This is essentially how .get() works, except that it returns the RPLData
		instead of the Python data.
		If data is None or omitted, the RPLData of this struct's basic data is
		returned.
		"""
		# Handle in terms of basic data.
		if data is None: return self.basic().resolve()

		# As docstring says..
		key = "???"
		if type(data) in [str, unicode]:
			key = data
			data = self[data]
		#endif


		try: data.resolve
		except AttributeError: raise RPLError("Failed resolution of %s in %s." % (key, self.name))
		else: return data.resolve()
	#endif

	def string(self, data=None):
		"""
		Retrieves Python data from RPLData as a string type.
		If data is None or omitted, the struct's basic data is returned as a string.
		"""
		# Handle in terms of basic data.
		if data is None: return self.basic().string()

		# As docstring says..
		key = "???"
		if type(data) in [str, unicode]:
			key = data
			data = self[data]
		#endif

		try: data.string
		except AttributeError: raise RPLError("Failed string retrieval of %s in %s." % (key, self.name))
		else: return data.string()
	#endif

	def number(self, data=None):
		"""
		Retrieves Python data from RPLData as a number type.
		If data is None or omitted, the struct's basic data is returned as a number.
		"""
		# Handle in terms of basic data.
		if data is None: return self.basic().number()

		# As docstring says..
		key = "???"
		if type(data) in [str, unicode]:
			key = data
			data = self[data]
		#endif

		try: data.number
		except AttributeError: raise RPLError("Failed numerical retrieval of %s in %s." % (key, self.name))
		else: return data.number()
	#endif

	def list(self, data=None, of=None):
		"""
		Retrieves Python data from RPLData as a list type.
		If data is None or omitted, the struct's basic data is returned as a list.
		"""
		# Handle in terms of basic data.
		if data is None: return self.basic().list(of)

		# As docstring says..
		key = "???"
		if type(data) in [str, unicode]:
			key = data
			data = self[data]
		#endif

		try: data.list
		except AttributeError: raise RPLError("Failed list retrieval of %s in %s." % (key, self.name))
		else: return data.list(of)
	#endif

	def pointer(self, data):
		"""
		Returns the RPLStruct pointed to be a reference.
		"""
		# As docstring says..
		if type(data) in [str, unicode]: data = self[data]
		if data.struct(): return data
		try: return data.pointer()
		except AttributeError: raise RPLBadType("Can only use pointer on references.")
	#endif

	def reference(self): return False
	def struct(self): return True

	def clone(self):
		new = copy.deepcopy(self)
		new.donor = self
		# Needs its own clones.
		new.clones = []
		self.clones.append(new)
		return new
	#enddef

	def __deepcopy__(self, memo={}):
		ret = RPLObject.__deepcopy__(self, memo)
		return ret
	#enddef
#endclass

# Well if that isn't a confusing name~ Sorry! :(
class StructRPL(RPLStruct):
	"""
	The header, as it were, for RPL files.
	<all><lib>
	lib: Optional. Import a library for use, such as std. May pass a name or list of names.</lib>
	<libs>
	libs: Alias of lib.</libs>
	<include>
	include: Optional. Statically import .rpl files by name or list of names.</include>
	<includes>
	includes: Alias of include.</includes>
	<helpkey>
	help: Optional though strongly suggested. Help contents for this .rpl of form:
	     [ "My help string"
	     	["adef", "adef's description"]
	     ]</helpkey></all>
	"""
	# Caps for consistency with "ROM"
	# Your own types should not have caps!
	typeName = "RPL"

	def register(self):
		self.registerKey("lib", "[path]*", "[]")
		self.registerVirtual("libs", "lib")
		self.registerKey("include", "[path]*", "[]")
		self.registerVirtual("includes", "include")
		self.registerKey("help", "[string]!|[string, [string, string]]+1", "[]")
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
	<all><id>
	id: Verify by ID as defined by certain libs.</id>
	<name>
	name: Verify by name as defined by certain libs.</name>
	<crc32>
	crc32: Verify file or section of file against a checksum.
	       [Checksum, Address as range]
	       Address range may be anchored to the  beginning or end of the file by 
	       using b or e at the start or end of the range.</crc32>
	<text>
	text: Verify text or raw data at a given address. Entry or list of entries of form:
	      [String, Address]</text></all>
	"""

	# No other struct should have caps in their names.
	# You could call this a backwards compatibility thing...
	typeName = "ROM"

	# Default settings for id and name keys:
	id_type = "string"
	id_location   = 0
	id_format     = {
		"length":  0,      # 0 for non-fixed length
		"padding": "\0",   # Char to pad with
		"align":   "left", # How to align the name, usually left
	}
	name_type = "string"
	name_location = 0
	name_format   = {
		"length":  0,      # 0 for non-fixed length
		"padding": "\0",   # Char to pad with
		"align":   "left", # How to align the name, usually left
	}

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)

		# Make these settings specific to the instantiation.
		self.id_location   = self.id_location
		self.id_format     = copy.copy(self.id_format)
		self.name_location = self.name_location
		self.name_format   = copy.copy(self.name_format)

		# Adjust keys...
		if self.id_type != "string":
			self.keys["id"][0] = RPLTypeCheck(self.rpl, "id", "[%s]*" % self.id_type)
		#endif

		if self.name_type != "string":
			self.keys["name"][0] = RPLTypeCheck(self.rpl, "name", "[%s]*" % self.name_type)
		#endif
	#enddef

	def register(self):
		self.registerKey("id", "[string]*", "[]")
		self.registerKey("name", "[string]*", "[]")
		self.registerKey("crc32", "hexnum|[[hexnum, hexnum|range]*0]*", "[]")
		self.registerKey("text", "[[string, hexnum]]*", "[]")
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
		try:
			# Address to EOF.
			rang = list(range(rang.number(), eof))
		except RPLBadType:
			# Not all were numbers.
			rang = rang.list("get")
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
		#endtry

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
		Validate contents of ROM file.
		"""
		failed = []
		# Create all IDs and names. Grab max lengths
		ids, names, max_id_len, max_name_len = [], [], 0, 0
		for x in self["id"].list():
			ids.append(x.serialize(self.id_format))
			max_id_len = max(len(ids[-1]), max_id_len)
		#endfor
		for x in self["name"].list():
			names.append(x.serialize(self.name_format))
			max_name_len = max(len(names[-1]), max_name_len)
		#endfor

		# Verify ID
		if ids:
			rom.seek(self.id_location)
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
			rom.seek(self.name_location)
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
			rom.seek(x[1].number())
			text = x[0].string()
			if rom.read(len(text)) != text:
				failed.append(("text", idx))
			#endif
		#endfor

		# Verify crc32s
		try:
			crc32 = self["crc32"].number()
			rom.seek(0)
			if crc32(rom.read()) & 0xFFFFFFFF != crc32:
				failed.append(("crc32", 0))
			#endif
		except RPLBadType:
			for idx, x in enumerate(self["crc32"].list()):
				x = x.list()
				if getCRC(rom, x[1]) != x[0].number():
					failed.append(("crc32", idx))
				#endif
			#endfor
		#endtry
		return failed
	#enddef

	@classmethod
	def template(rpl=None, tabs=""):
		return (
			"%(tabs)sROM {\n"
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

	def manage(self, requested):
		"""
		Overwrite this cause Static should always be managed by the system.
		"""
		return True
	#enddef

	def addChild(self, structType, name):
		"""
		Overwrite this cause Static accepts all root children UNLESS it is
		a child itself.
		"""
		# If this has a parent, then this can only accept the children that
		# parent can.

		# Retrieve the first non-static parent.
		if self.parent:
			parent = self.parent
			while parent and parent != self.rpl and parent.typeName == "static": parent = parent.parent
		else:
			parent = self.rpl
		#endif

		if structType not in parent.structs:
			raise RPLError("%s isn't allowed as a substruct of %s." % (
				structType, "root" if parent == self.rpl else parent.typeName
			))
		#endif
		new = parent.structs[structType](self.rpl, name, self)
		self.children[name] = new
		# Add a copy to the parent, too, so lib writers don't have to
		# think about static children.
		parent.children[name] = new
		return new
	#enddef

	def __setitem__(self, key, value):
		"""
		Overwrite this cause Static accepts all keys.
		"""
		self.data[key] = value
	#enddef
#endclass

class Serializable(RPLStruct):
	"""
	Inherit this class for data that can be imported and/or exported.
	This will handle several common keys for you.
	<all><base>
	base:   Optional. Base address of structure in the binary.
	        This may be a relative address using the form by having a prefix:
	          b, s, begin, start: Relative to beginning of file.
	          c, cur, current: Relative to end of preceding structure.
	          e, end: Relative to end of file. (eg. e:$10 is $10 before the end.)
	        Relative addressing is entered as a list, but range form is accepted
	        by use of the single-character forms. (Default c:$000000)</base>
	<file>
	file:   Optional. Name of file to export to/import from, relative to current
	        directory. Default value uses the struct name and hierarchy so that
	        each grandparent is a folder and this struct is the filename.</file>
	<ext>
	ext:    Optional. If defined, it will use this as the extension when defaulting
	        file or such. Default is defined by the structure.</ext>
	<import>
	import: Optional. When to import this struct. Options are:
	         true:      If nothing was requested, or this was requested. (Default)
	         false:     Never import.
	         always:    Always import, regardless of requests.
	         requested: Only import if requested.</import>
	<export>
	export: Optional. When to export this struct. See import for options.</export></all>
	"""

	# NOTE: There is no typeName because this is not meant to be used directly.

	def __init__(self, rpl, name, parent=None):
		RPLStruct.__init__(self, rpl, name, parent)
		self.prepared = False
	#enddef

	def register(self):
		self.registerKey("base", "[string:(b, s, c, e, begin, cur, current, start, end), math].", "c:$000000")
		self.registerKey("file", "path", "")
		self.registerKey("ext", "string", "")
		self.registerKey("export", "bool|string:(always, requested)", "true")
		self.registerKey("import", "bool|string:(always, requested)", "true")
	#enddef

	def manage(self, requested):
		"""
		See RPLStruct.manage
		Serializables also regard its import and export keys.
		"""
		if not self.unmanaged: return False
		port = self["import" if self.rpl.importing else "export"].string()
		# If nothing was requested, or if it was part of what was requested.
		if port == "true": return not requested or self.rpl.wantPort(self, requested)
		# Never port in this direction.
		if port == "false": return False
		# Always port in this direction, regardless of requests.
		if port == "always": return True
		# Only port if requested specifically.
		if port == "requested": return self.rpl.wantPort(self, requested)
	#enddef

	def __getitem__(self, key):
		if key == "file":
			# Calculate filename
			cur, first = self, None
			filename, unk = "", ""
			# This form allows inheriting the filename and structure while
			# defaulting to using the names, if explicitely given.
			while cur and cur != self.rpl:
				if "file" in cur.data:
					if first is None: first = cur.data["file"]
					# Note that this normalizes slashes to /
					tmpname = (
						cur.data["file"].getRaw()
						if isinstance(cur.data["file"], Path) else
						Path.convert(cur.data["file"].get())
					)
					filename = tmpname + filename
					# When the file tage is prefixed by a / or \
					# it inherits its parent's filename.
					if tmpname[0] != "/": break
				# Same as if not filename and not cur.gennedName
				elif not (filename or cur.gennedName):
					unk = "/" + cur.name + unk
				#endif
				cur = cur.parent
			#endwhile
			if filename: filename = Path(filename, first.rpl, first.container, first.mykey, *first.pos)
			elif unk: filename = Path(unk[1:], self.rpl, self)
			else: raise RPLError("No filename could be made.", self)

			if not filename.hasExt(): filename.setExt(self["ext"].get())

			return filename
		elif key == "base":
			# Handles all the inheritance and defaulting and such.
			value = RPLStruct.__getitem__(self, "base")
			rom = self.rpl.rom

			try:
				v = value.list()
				rel, base = {
					"b": 0, "begin": 0, "s": 0, "start": 0,
					"c": 1, "cur": 1, "current": 1,
					"e": 2, "end": 2
				}[v[0].string()], v[1].number()
			except (RPLBadType, AttributeError):
				# Check if it's a RPLData, more or less.
				try: value.get
				except AttributeError: pass
				else: v = value.get()
				if v in ["b", "s", "begin", "start"]: rel, base = 0, 0
				elif v in ["c", "cur", "current"]: rel, base = 1, 0
				elif v in ["e", "end"]: rel, base = 2, 0
				else: return value
			#endtry

			# Retrieve relative to current.
			if rel == 1:
				parent = self.parent
				try:
					index = parent.children.values().index(self)
					base = None
				# If it's not in its parent's children, it must be a clone.
				except ValueError:
					index = parent.children.values().index(self.donor)
					# Quickly check if the preceding clone can tell it where it is.
					# Well it should be able to!
					cloneIndex = self.donor.clones.index(self)
					if cloneIndex > 0:
						try:
							clone = self.donor.clones[cloneIndex - 1]
							base = clone["base"].number() + clone.len()
							# If this works, set parent to None to skip the loop.
							parent = None
						except (TypeError, RPLError, AttributeError): pass
					#endif
					# Otherwise we can just let the loop run.
				#endtry
				# Backs up through all structs in a linear fashion
				while parent:
					# For each child in this structure
					while index > 0:
						index -= 1
						previousSibling = parent.children.values()[index]

						# If this sibling has children, start at its last child first.
						while len(previousSibling.children):
							index = len(previousSibling.children) - 1
							parent = previousSibling
							previousSibling = parent.children.values()[index]
						#endif

						# This is not relevant to the structure if system isn't managing it.
						if not previousSibling.manage(self.rpl.requested): continue

						# If this is a cloned struct, check the last clone only.
						if previousSibling.clones:
							try:
								# Try to grab the base and offset it by the length...
								# If this fails, that struct isn't meant to be serialized.
								clone = previousSibling.clones[-1]
								base = clone["base"].number() + clone.len()
								break
							except (TypeError, RPLError, AttributeError): pass
						# Otherwise, just check this struct.
						else:
							try:
								base = previousSibling["base"].number() + previousSibling.len()
								break
							except (TypeError, RPLError, AttributeError): pass
						#endif
					#endwhile
					if base is not None: break
					if parent.parent: index = parent.parent.children.values().index(parent)
					parent = parent.parent
					if parent and parent != self.parent:
						# Check the parent, too. Don't check own parent though,
						# since it doesn't finish before this struct.
						try:
							base = parent["base"].get() + parent.len()
							break
						except (TypeError, RPLError, AttributeError): pass
					#endif
				#endwhile
				if base is None: base = 0
			# Retrieve relative to end.
			elif rel == 2:
				try: base = rom.length - base
				except AttributeError:
					current = rom.tell()
					rom.seek(0, 2)
					base = rom.length = rom.tell()
					rom.seek(current, 0)
				#endtry
			#endif
			tmp = Number(base)
			self["base"] = tmp
			return tmp
		else: return RPLStruct.__getitem__(self, key)
	#enddef

	def open(self, folder, ext="bin", retName=False, justOpen=False):
		"""
		Helper method for opening files.
		"""
		if not justOpen:
			path = self["file"]
			if not path.hasExt(): path.setExt(ext)
			path = path.get(folder)

			# Return requested thing (path or handle).
			if retName: return path
		else: path = folder
		return self.rpl.share(path, codecs.open, x, encoding="utf-8", mode="r+")
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
		Stub. Fill this in to prepare the struct for import.

		                 v This stage.
		[Bin] <-- [Pyt] <-- [Reso-]
		[ary] --> [hon] --> [urces]
		"""
		pass
	#enddef

	def importData(self, rom, folder):
		"""
		Stub. Fill this in to import appropriately.

		       v This stage.
		[Bin] <-- [Pyt] <-- [Reso-]
		[ary] --> [hon] --> [urces]
		"""
		pass
	#enddef

	def exportPrepare(self, rom, folder):
		"""
		Stub. Fill this in to prepare the struct.
		Typically speaking you will want to lazily read from the ROM by
		adding the reads to your __getitem__ statement. This allows things
		to be pulled in in the order necessary, which may not be necessarily
		predictable.
		This function should generally just be used for prep. If you're going
		to read anything from the ROM, be really mindful.

		[Bin] <-- [Pyt] <-- [Reso-]
		[ary] --> [hon] --> [urces]
		       ^ This stage.
		"""
		pass
	#enddef

	def exportData(self, rom, folder):
		"""
		Stub. Fill this in to export appropriately.
		You will generally not need the ROM here, but it is included in the event
		that you do.

		[Bin] <-- [Pyt] <-- [Reso-]
		[ary] --> [hon] --> [urces]
		                 ^ This stage.
		"""
		pass
	#enddef

	def len(self):
		"""
		Stub. You must fill this in, as it allows structs to use relative bases.
		Not implementing this will make your struct not officially be serializable
		and the data handled by it will be overwritten by the following struct in
		an import if it uses relative basing. In an export, it will simply use
		the same data as this struct does for exporting. Needless to say, both
		are bad scenarios!
		"""
		raise RPLError("Serializables must implement len.", self.__class__.__name__, "len")
	#enddef
#endclass

################################################################################
#################################### RPLRef ####################################
################################################################################
class RPLRef(object):
	"""
	Manages references to other fields.
	"""

	keyspec = re.compile(r'([a-z]+[0-9]*)((?:\[[0-9]+\])*)')
	# Way way ... back; Great great ... grand parent
	heir = re.compile(r'^(?=.)((w*)back_?)?((g*)parent)?$')

	typeName = "reference"

	def __init__(self, ref, rpl, container, mykey, line, char):
		self.rpl = rpl
		self.container = container
		self.mykey = mykey
		self.pos = (line, char)
		self.nocopy = ["rpl", "container", "pos", "idxs"]

		tmp = ref.split(".")
		self.refstruct, self.keysets = tmp[0], []

		for x in tmp[1:]:
			keyset = self.keyspec.match(x).groups("")
			self.keysets.append((keyset[0], [int(y) for y in keyset[1][1:-1].split("][")] if keyset[1] else []))
		#endfor
	#enddef

	def __unicode__(self):
		"""
		Output ref to RPL format.
		"""
		ret = "@%s" % self.refstruct
		for x in self.keysets:
			ret += "." + x[0]
			if x[1]: ret += "[%s]" % "][".join(x[1])
		#endfor
		return ret
	#enddef

	def parts(self): return self.refstruct, self.keysets

	def pointer(self, callers=[]):
		# When a reference is made, this function should know what struct made
		# the reference ("this", ie. self.container) BUT also the chain of
		# references up to this point..
		# First check if we're referring to self or referrer and/or parents.
		heir = RPLRef.heir.match(self.refstruct)
		if self.refstruct == "this" or heir:
			if self.container is None or self.mykey is None:
				raise RPLError("Cannot use relative references in data form.")
			#endif
			# Referrer history. TODO: This is shoddy at best.
			if heir and heir.group(1):
				try: ret = callers[-1 - len(heir.group(2))]
				except IndexError: raise RPLError("No %s." % self.refstruct)
			# "this" or parents only.
			else: ret = self.container
			# "parent"
			if heir and heir.group(3):
				ret = ret.parent
				# The gs (great/grand) in g*parent.
				for g in heir.group(4):
					try: ret = ret.parent
					except Exception as x:
						if ret is not None: raise x
					#endtry
					if ret is None: raise RPLError("No %s." % self.struct)
				#endfor
			#endif
		else:
			try: ret = self.rpl.structsByName[self.refstruct]
			except KeyError: raise RPLError("Struct %s not found." % self.refstruct)
		return ret
	#enddef

	def get(self, callers=[], retCl=False):
		"""
		Return referenced value.
		"""
		ret = self.pointer(callers)
		ti = 0 # Total Index
		callersAndSelf = callers + [self]
		for idx, ks in enumerate(self.keysets):
			# Retrieve key.
			if ks[0]:
				if ret.struct(): ret = ret[ks[0]]
				else:
					raise RPLError(
						"Attempted to address key outside of a struct."
						" Failed on %ith key." % idx,
						self.container, self.key, self.pos
					)
					#ret = ret.list()[ks[0]]
				#endif
			# Retrieve indexes.
			for i, x in enumerate(ks[1]):
				try:
					if ret.reference(): ret = ret.get(callersAndSelf)[x]
					else: ret = ret.list()[x]
				except IndexError:
					raise RPLError(
						"List not deep enough. Failed on %ith index." % ti,
						self.container, self.key, self.pos
					)
				except RPLBadType:
					raise RPLError(
						"Attempted to index nonlist. Failed on %ith index." % ti,
						self.container, self.key, self.pos
					)
				#endtry
				ti += 1
			#endfor
			if ret.reference(): ret = ret.get(callersAndSelf, True)
		#endfor

		# Verify type
		if (self.container is not None and self.mykey is not None
		and self.mykey in self.container.keys):
			ret = self.container.keys[self.mykey][0].verify(ret)
		#endif

		if retCl: return ret   # Return class instance.
		else: return ret.get() # Return Python data.
		#endif
	#endif

	def set(self, data, callers=[], retCl=False):
		"""
		Set referenced value (these things are pointers, y'know).
		"""
		ret = self.pointer(callers)

		ti = 0
		lks = len(self.keysets) - 1 # Last Key Set
		callersAndSelf = callers + [self]
		for ki, ks in enumerate(self.keysets):
			# If this is the last keyset and there's no indexes...
			if ki == lks and not ks[1]:
				# ...set this to the final key value.
				key = ks[0]
				break
			#endif
			ret = ret[ks[0]]
			lksi = len(ks[1]) - 1
			for i, x in enumerate(ks[1]):
				# If this is the last index on the last set of indexes...
				if ki == lks and i == lksi:
					# ...set this to the final key value.
					key = x
					break
				#endif

				try:
					if ret.reference(): ret = ret.get(callersAndSelf)[x]
					else: ret = ret.list()[x]
				except IndexError:
					raise RPLError("List not deep enough. Failed on %ith index." % ti)
				except RPLBadType:
					raise RPLError("Attempted to index nonlist. Failed on %ith index." % ti)
				#endtry
				ti += 1
			#endfor
		#endfor

		# Needs to wrap data
		datatype = {
			str: "string", unicode:"string", int: "number", long:"number",
			list: "list"
		}[type(data)]

		# Verification is done by __setitem__
		ret[key] = self.rpl.parseCreate(
			(datatype, data), None, None, *self.pos,
			skipSubInst = (datatype == "list" and isinstance(data[0], RPLData))
		)
		return True
	#enddef

	def resolve(self): return self.get(retCl=True)
	def string(self): return self.get(retCl=True).string()
	def number(self): return self.get(retCl=True).number()
	def list(self, of=None): return self.get(retCl=True).list(of=of)
	def reference(self): return True
	def struct(self): return False
	def keyless(self): return not bool(self.keysets)

	def __deepcopy__(self, memo={}):
		ret = object.__new__(self.__class__)
		for k, x in self.__dict__.iteritems():
			if k in self.nocopy or callable(x): setattr(ret, k, x)
			else: setattr(ret, k, copy.deepcopy(x, memo))
		#endfor
		# Allows clones to have the correct @this.
		ret.container = memo["parent"]
		return ret
	#enddef
#endclass

################################################################################
#################################### RPLData ###################################
################################################################################

class RPLData(object):
	def __init__(self, data=None, top=None, container=None, mykey=None, line=None, char=None):
		self.rpl, self.container, self.mykey, self.pos = top, container, mykey, (line, char)
		self.nocopy = ["rpl", "container"]

		if data is not None: self.set(data)
	#enddef

	def get(self): return self.data
	def set(self, data): self.data = data
	def resolve(self): return self
	def string(self): raise RPLBadType("%s cannot be interpreted as a string." % self.typeName)
	def number(self): raise RPLBadType("%s cannot be interpreted as a number." % self.typeName)
	def list(self, of=None): raise RPLBadType("%s cannot be interpreted as a list." % self.typeName)
	def reference(self): return False
	def struct(self): return False

	# You must define these in your own types.
	def defaultSize(self):
		"""
		Returns default size for use by Data struct.
		"""
		raise RPLError("Must define defaultSize.", self.__class__.__name__, "defaultSize")
	#enddef

	def serialize(self, **kwargs):
		"""
		Return binary form of own data.
		"""
		raise RPLError("Must define serialize.", self.__class__.__name__, "serialize")
	#enddef

	def unserialize(self, data, **kwargs):
		"""
		Parse binary data and set to self.
		"""
		raise RPLError("Must define unserialize.", self.__class__.__name__, "unserialize")
	#enddef

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

	def __deepcopy__(self, memo={}):
		ret = object.__new__(self.__class__)
		for k, x in self.__dict__.iteritems():
			if k in self.nocopy or callable(x): setattr(ret, k, x)
			else: setattr(ret, k, copy.deepcopy(x, memo))
		#endfor
		# Something for clones in references, I suppose adding it here is just completist.
		ret.container = memo["parent"]
		return ret
	#enddef
#endclass

class String(RPLData):
	"""
	String basic type.
	"""
	typeName = "string"

	escape = re.compile(r'\$(\$|[0-9a-fA-F]{2})')
	binchr = re.compile(r'[\x00-\x08\x0a-\x1f\x7f-\xff$]')
	def set(self, data):
		if type(data) is str: data = unicode(data)
		elif type(data) is not unicode:
			raise RPLError(
				'Type "%s" expects unicode or str. Got "%s"' % (
					self.typeName, type(data).__name__
				), self.container, self.mykey, self.pos
			)
		#endif
		self.data = String.escape.sub(String.replIn, data)
	#enddef

	def string(self): return self.get()

	def escaped(self):
		return String.binchr.sub(String.replOut, self.string())
	#enddef

	def __unicode__(self):
		return '"' + String.binchr.sub(String.replOut, self.string()) + '"'
	#enddef

	def serialize(self, **kwargs):
		if "string" in kwargs: rstr = kwargs["string"]
		else:
			rstr = self.string().encode("utf8")
			if "size" not in kwargs or not kwargs["size"]: return rstr
			rstr = rstr[0:kwargs["size"]]
			while True:
				try:
					rstr.decode("utf8")
					break
				except UnicodeDecodeError: rstr = rstr[0:-1]
			#endwhile
		#endif

		if kwargs["size"] == 0: return rstr
		rpad = kwargs["padding"] * (kwargs["size"] - len(rstr))
		if not rpad: return rstr
		align = kwargs["align"]
		if align[-6:] == "center":
			split = (ceil if padside[0] == "r" else int)(len(rpad) / 2)
			return rpad[0:split] + rstr + rpad[split:0]
		elif align == "right": return rpad + rstr
		else: return rstr + rpad
	#enddef

	def unserialize(self, data, **kwargs): self.set(data.decode("utf8"))

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

	def set(self, data):
		if type(data) is str: self.data = unicode(data)
		elif type(data) is unicode: self.data = data
		else:
			raise RPLError(
				'Type "%s" expects unicode or str. Got "%s"' % (
					self.typeName, type(data).__name__
				), self.container, self.mykey, self.pos
			)
		#endif
	#enddef

	def __unicode__(self):
		return self.badchr.sub(String.replOut, self.data)
	#enddef
#endclass

class RefString(String):
	"""
	String that contains references, replaced when requested.
	"""

	typeName = "refstr"

	def set(self, data):
		if type(data) is str: data = unicode(data)
		elif type(data) is not unicode:
			raise RPLError(
				'Type "%s" expects unicode or str. Got "%s"' % (
					self.typeName, type(data).__name__
				), self.container, self.mykey, self.pos
			)
		#endif

		# Split up references.
		pieces, pos = [], 0
		next = data.find("@")
		while next != -1:
			space = data.find(" ", next)
			if space == -1: space = len(data)
			# Do escape sequence replacements on string data only.
			pieces.append(String.escape.sub(String.replIn, data[0:next]))

			# Make a reference. TODO: This could be better.. should I care?
			# TODO: self.rpl may not always be set.
			pieces.append(RPLRef(
				data[next + 1:space], self.rpl, self.container, self.mykey,
				self.pos[0], self.pos[1] + pos + next if self.pos[1] is not None else None
			))
			data = data[space:]
			pos += space
			next = data.find("@")
		#endwhile
		if data: pieces.append(String.escape.sub(String.replIn, data))

		self.data = pieces
	#enddef

	def get(self):
		ret = u""
		for i, x in enumerate(self.data):
			if i % 2 == 0: ret += x
			else:
				try: ret += x.string()
				except RPLBadType:
					try: ret += unicode(x.number())
					except RPLBadType:
						raise RPLError(
							"Cannot use list type in %s" % refstr,
							self.container, self.mykey, x.pos
						)
					#endtry
				#endtry
			#endif
		#endfor
		return ret
	#enddef

	def __unicode__(self):
		return '@`' + String.binchr.sub(String.replOut, self.string()) + '`,'
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
		if not self.data:
			self.data = []
			return
		#endif
		tmp = self.data.replace("\\", "/")
		self.startingSlash = (tmp[0] == "/")
		tmp = tmp.split("/")
		if "." in tmp[-1]: tmp[-1], self.ext = tuple(tmp[-1].rsplit(".", 1))
		else: self.ext = None
		self.data = tmp
	#enddef

	def get(self, folder=[]):
		return os.path.join(*(folder + self.data)) + (os.extsep + self.ext if self.ext else "")
	#enddef

	def getRaw(self): return "/".join(self.data) + ("." + self.ext if self.ext else "")

	def hasExt(self): return bool(self.ext)
	def setExt(self, ext): self.ext = ext
#enddef

class Number(RPLData):
	"""
	Number basic type.
	"""
	typeName = "number"

	def set(self, data):
		if type(data) not in [int, long]:
			raise RPLError(
				'Type "%s" expects int or long.'  % self.typeName,
				self.container, self.mykey, self.pos
			)
		#endif
		self.data = data
	#enddef

	def number(self): return self.data

	def __unicode__(self): return str(self.data)

	def defaultSize(self): return 4

	def serialize(self, **kwargs):
		big, ander, ret = (kwargs["endian"] == "big"), 0xff, r''
		for i in helper.range(kwargs["size"]):
			c = chr((self.data & ander) >> (i*8))
			if big: ret = c + ret
			else: ret += c
			ander <<= 8
		#endfor
		return ret
	#enddef

	def unserialize(self, data, **kwargs):
		big = (kwargs["endian"] == "big")
		size = len(data)
		self.data = 0
		for i,x in enumerate(data):
			if big: shift = size-i-1
			else: shift = i
			self.data |= ord(x) << (shift*8)
		#endfor
	#enddef
#endclass

class HexNum(Number):
	"""
	HexNum interpreted type.
	"""
	typeName = "hexnum"

	def __unicode__(self): return "$%x" % self.data
#endclass

class List(RPLData):
	"""
	List basic type.
	"""
	typeName = "list"

	def set(self, data):
		if type(data) is not list:
			raise RPLError(
				'Type "%s" expects list.' % self.typeName,
				self.container, self.mykey, self.pos
			)
		#endif
		self.data = data
	#enddef

	@staticmethod
	def listOr(data, of):
		# Try it without an of so that RPLBadType isn't raised for any of the
		# type assertions on contents, only the list itself.
		try: data.list()
		except RPLBadType:
			if   of == "get":    return data.get()
			elif of == "number": return data.number()
			elif of == "string": return data.string()
			else: return getattr(data, of)()
		else: return data.list(of)
	#enddef

	def list(self, of=None):
		if of is None: return self.data
		return [List.listOr(x, of) for x in self.data]
	#endif

	def __unicode__(self):
		return "[ " + ", ".join(map(unicode, self.data)) + " ]"
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
			raise RPLError(
				'Type "%s" expects list.' % self.typeName,
				self.container, self.mykey, self.pos
			)
		#endif
		for x in data:
			try: x.number()
			except RPLBadType:
				try:
					if len(x.string()) != 1: raise RPLBadType()
				except RPLBadType:
					raise RPLError(
						'Types in a "%s" must be a number or one character literal' % self.typeName,
						self.container, self.mykey, self.pos
					)
				#endtry
			#endtry
		#endfor
		self.data = data
	#enddef

	def __unicode__(self):
		ret, posseq, negseq, mul, last = [], [], [], [], None
		for x in self.data:
			# Try to add single-character literal.
			try:
				x = x.string()
				# A literal should obviously
				if negseq:
					ret.append(u"%s-%s" % (negseq[0], negseq[-1]))
					negseq = []
				if posseq:
					ret.append(u"%s-%s" % (posseq[0], posseq[-1]))
					posseq = []
				if mul:
					ret.append(u"%s*%s" % (mul[0], len(mul)))
					mul = []
				#endif
				ret.append(x)
				last = None
			# Otherwise, we try to form a range command.
			except RPLBadType:
				if last is not None:
					d = x.number()
					lastv = last.number()
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
			#endtry
			last = x
		#endfor
		# If there are any left over...
		if negseq: ret.append(u"%s-%s" % (negseq[0], negseq[-1]))
		elif posseq: ret.append(u"%s-%s" % (posseq[0], posseq[-1]))
		elif mul: ret.append(u"%s*%s" % (mul[0], len(mul)))
		return u":".join(ret)
	#enddef
#endclass

class Enum(RPLData):
	def set(self, data):
		for x in self.enum:
			if data in x[0]:
				self.data = x[1]
				return
			#endif
		#endfor
		raise RPLError(
			'Value %s not in expected set for "%s".'  % (data, self.typeName),
			self.container, self.mykey, self.pos
		)
	#enddef

#	def getType(self, types, errFunc):
#		if type(self.data) in types: return self.data
#		for x in self.enum:
#			if x[1] == self.data:
#				for x in x[0]:
#					if type(x) in types: return x
#				#endfor
#				errFunc(self)
#			#endif
#		#endfor
#		errFunc(self)
#	#enddef

#	def string(self): self.getType([str, unicode], RPLData.string)
#	def number(self): self.getType([int, long], RPLData.number)
#	def list(self): self.getType([list], RPLData.list)

	def __unicode__(self):
		for x in self.enum:
			if self.data == x[1]:
				return x[0][0]
			#endif
		#endfor
		raise RPLError(
			'IMPOSSIBLE ERROR AHHHH "%s"' % self.typeName,
			self.container, self.mykey, self.pos
		)
	#endif
#endclass

class Bool(Enum, Number):
	typeName = "bool"

	enum = [
		[["true", 1, "1", "on"],   True],
		[["false", 0, "0", "off"], False],
	]

	def set(self, data):
		try: data = data.lower()
		except AttributeError: pass
		Enum.set(self, data)
	#enddef

	def string(self): return "true" if self.data else "false"
	def number(self): return 1 if self.data else 0

	def __unicode__(self):
		# This is just faster..and easy
		return "true" if self.data else "false"
	#enddef

	def defaultSize(self): return 1

	def serialize(self, **kwargs):
		self.data = 1 if self.data else 0
		ret = Number.serialize(self, **kwargs)
		self.data = bool(self.data)
		return ret
	#enddef

	def unserialize(self, data, **kwargs):
		# TODO: Should this only accept 0 and 1?
		Number.unserialize(self, data, **kwargs)
		self.data = bool(self.data)
	#enddef
#endclass

class Named(RPLData):
	def set(self, data, types=[]):
		if type(data) in [str, unicode]:
			data = data.lower()
			if data in self.names: self.data = self.names[data]
			else: raise RPLError(
				'No %s name "%s"' % (self.typeName, data),
				self.container, self.mykey, self.pos
			)
		else:
			raise RPLError(
				'Type "%s" expects %s.' % (
					self.typeName, helper.list2english(["str", "unicode"] + types, "or")
				), self.container, self.mykey, self.pos
			)
		#endif
	#enddef

	def __unicode__(self, fmt=u"%s"):
		for k, v in self.names.iteritems():
			if v == self.data: return unicode(k)
		#endfor
		return fmt % self.data
	#enddef
#endclass

class Size(Named, Number):
	"""
	Named size types. Very basic naming:
	byte:   1
	short:  2
	long:   4
	double: 8
	"""
	typeName = "size"

	names = {
		"byte":   1,
		"short":  2,
		"long":   4,
		"double": 8,
	}

	def set(self, data):
		if type(data) in [int, long]:
			if data <= 0: raise RPLError(
				'Type "%s" expects value > 0.' % self.typeName,
				self.container, self.mykey, self.pos
			)
			self.data = data
		else: Named.set(self, data, ["int", "long"])
	#enddef

	def number(self): return self.data

	def serialize(self, **kwargs):
		return Number.serialize(self, **kwargs)
	#enddef

	def unserialize(self, data, **kwargs):
		Number.unserialize(self, data, **kwargs)
	#enddef
#endclass

class Math(Literal, Number):
	"""
	Handles mathematics.
	Order of Operations:
	 ()
	 **
	 * / %
	 + -
	 << >>
	 &
	 ^
	 |
	Division is integer. ** is power of.
	Variables may be passed, see respective key for details.
	You may use references as expected and may also alter the base of a number:
	 Hex: $$
	      Note this is two because one would write a hex char into the string.
	      Two may be used to escape the $, and therefor leave it to
	      interpretation by the math type.
	 Hex: 0x
	 Octal: 0
	 Octal: 0o
	 Binary: %
	         This works like a unary operator.
	 Binary: 0b
	 General: number_base
	          For example 11_5 would be "11 in base 5" which is 6 in decimal.
	"""
	typeName = "math"

	specification = re.compile(r'(\*\*|<<|>>|[()*/%+\-&^|])')

	def set(self, data):
		if type(data) in [int, long]: data = str(data)
		Literal.set(self, data)
		tokens = [x for x in Math.specification.split(self.data.replace(" ", "")) if x != ""]

		# Order tokens...
		def setPAndRet(cur, p, i):
			p[0] = i
			return cur
		#enddef

		def groupRight(idx, level):
			cur = None
			i = idx[0]
			while i < len(tokens):
				x = tokens[i]
				p = [i+1]
				try:
					# Number, variable, reference, or error to be reported later.
					if x not in ["(",")","**","*","/","%","+","-","<<",">>","&","^","|"]:
						if cur is not None:
							raise RPLError(
								"Number with no operation.",
								self.container, self.mykey, self.pos # TODO: Adjust pos
							)
						#endif
						cur = x
					elif level < 1: return setPAndRet(cur)
					# Binary marker.
					elif x == "%" and i == idx[0]: cur = "%" + groupRight(p, 0)[1]
					# Grouping.
					elif x == "(": cur = groupRight(p, 9)
					elif x == ")":
						if level > 9:
							raise RPLError(
								"Unmatched parenthesis in expression.",
								self.container, self.mykey,
								(self.pos[0], self.pos[1] + data.find(")") if self.pos[1] is not None else data.find(")"))
							)
						elif level == 9: return setPAndRet(cur, idx, i + 1)
						else: return setPAndRet(cur, idx, i)
					#elif level < 2: return setPAndRet(cur)
					# Unary operations
					elif x == "+" and i == idx[0]: cur = (0, groupRight(p, 2))
					elif x == "-" and i == idx[0]: cur = (1, groupRight(p, 2))
					elif level < 3: return setPAndRet(cur, idx, i)
					# Binary operations.
					elif cur is None:
						raise RPLError(
							"Expected lvalue.",
							self.container, self.mykey, self.pos # TODO: Adjust pos
						)
					elif x == "**": cur = (2, cur, groupRight(p, 2))
					elif level < 4: return setPAndRet(cur, idx, i)
					elif x == "*": cur = (3, cur, groupRight(p, 3))
					elif x == "/": cur = (4, cur, groupRight(p, 3))
					elif x == "%": cur = (5, cur, groupRight(p, 3))
					elif level < 5: return setPAndRet(cur, idx, i)
					elif x == "+": cur = (6, cur, groupRight(p, 4))
					elif x == "-": cur = (7, cur, groupRight(p, 4))
					elif level < 6: return setPAndRet(cur, idx, i)
					elif x == "<<": cur = (8, cur, groupRight(p, 5))
					elif x == ">>": cur = (9, cur, groupRight(p, 5))
					elif level < 7: return setPAndRet(cur, idx, i)
					elif x == "&": cur = (10, cur, groupRight(p, 6))
					elif level < 8: return setPAndRet(cur, idx, i)
					elif x == "^": cur = (11, cur, groupRight(p, 7))
					elif level < 9: return setPAndRet(cur, idx, i)
					elif x == "|": cur = (12, cur, groupRight(p, 8))
				except IndexError:
					raise RPLError(
						"Invalid binary operation, no lvalue.",
						self.container, self.mykey, self.pos # TODO: Adjust pos
					)
				#endtry
				i = p[0]
			#endfor
			if level == 9:
				raise RPLError(
					"Unended parenthesis in expression.",
					self.container, self.mykey, self.pos # TODO: Adjust pos
				)
			#endif

			if cur is None:
				raise RPLError(
					"Expected rvalue.",
					self.container, self.mykey, self.pos # TODO: Adjust pos
				)
			#endif

			# 0 is effectively a nop.
			if type(cur) is not tuple: cur = (0, cur)
			return setPAndRet(cur, idx, i)
		#enddef
		idx = [0]
		self.data = groupRight(idx, 10)
	#enddef

	def eval(self, op, var):
		# Statics.
		if type(op) in [int, long, float]: return op
		elif type(op) is not tuple:
			if op[0] == "@": return RPLRef(op[1:], self.rpl, self.container, self.mykey, *self.pos).number()
			try:
				if op[0] == "$": return int(op[1:], 16)
				elif op[0:2].lower() == "0x": return int(op[2:], 16)
				elif op[0:2].lower() == "0o": return int(op[2:], 8)
				elif op[0] == "%": return int(op[1:], 2)
				elif op[0:2].lower() == "0b": return int(op[2:], 2)
				elif op[0] == "0": return int(op, 8)
			except ValueError as err:
				raise RPLError(
					'Erroneous alternate base sequence "%s"' % op,
					self.container, self.mykey, self.pos
				)
			try:
				num, base = tuple(op.split("_"))
				return int(num, int(base))
			except ValueError:
				try: return int(op)
				except ValueError:
					if op in var: return var[op]
					raise RPLError(
						'Erroneous value in expression "%s"' % op,
						self.container, self.mykey, self.pos
					)
				#endtry
			#endtry
		#endif

		# Unary ops.
		if op[0] in [0, 1]:
			cmd, val = op
			val = self.eval(val, var)
			if cmd == 0: return +val
			elif cmd == 1: return -val
		# Binary ops.
		else:
			cmd, lval, rval = op
			lval = self.eval(lval, var)
			rval = self.eval(rval, var)
			if cmd ==  2: return lval ** rval
			if cmd ==  3: return lval * rval
			if cmd ==  4: return int(lval // rval)
			if cmd ==  5: return lval % rval
			if cmd ==  6: return lval + rval
			if cmd ==  7: return lval - rval
			if cmd ==  8: return lval << rval
			if cmd ==  9: return lval >> rval
			if cmd == 10: return lval & rval
			if cmd == 11: return lval ^ rval
			if cmd == 12: return lval | rval
			# Internal operators.
			if cmd == 30: return float(lval) / rval
		#endif

		raise RPLError("Impossibility in equasion.", self.container, self.mykey, self.pos)
	#enddef

	def warnfloat(self, x, var={}):
		x = self.eval(x, var)
		if type(x) is float and int(x) != x:
			helper.err(RPLError(
				"Resultant value was a float.",
				self.container, self.mykey, self.pos, etype="Warning"
			))
		#endif
		return int(x)
	#enddef

	def solveForX(self, eq, var={}, solveFor=None):
		# Find reference with no value.
		def dive(me, parents):
			for i, x in enumerate(me[1:]):
				i += 1
				ppme = parents + [i]
				if type(x) is tuple:
					t = dive(x, ppme)
					if t: return t
				elif solveFor:
					if x == solveFor: return ppme, x
				elif x[0] == "@":
					ref = RPLRef(x[1:], self.rpl, self.container, self.mykey, *self.pos)
					try: ref.number()
					except RPLKeyError: return ppme, ref
				#endif
			#endfor
		#enddef
		path, ref = dive(self.data, [])

		if not path: return # Nothing to do

		# Make new equasion.
		cur = self.data
		for idx in path:
			op = cur[0]

			if op == 1: eq = (1, eq)
			elif op in [5, 10, 12]:
				raise RPLError(
					"Needed to solve %s but impossible to invert." % {
						5: "%", 10: "&", 12: "|"
					}[cur[0]], self.container, self.mykey, self.pos
				)
			# x somewhere in lvalue.
			elif idx == 1:
				if op in [8, 9]:
					helper.err(RPLError("Inverting %s may be lossy." % (
						"<<" if op == 8 else ">>"
					), self.container, self.mykey, self.pos, etype="Warning"))
				#endif

				if   op == 2: eq = (2, eq, (30, 1, cur[2]))
				elif op != 0:
					eq = ({
						3: 30, 4: 3, 6: 7, 7: 6, 8: 9, 9: 8, 11: 11, 30: 3
					}[op], eq, cur[2])
				#endif
			# x somewhere in rvalue.
			else:
				if   op == 2:
					raise RPLError(
						"Needed to solve y^x but inversion is not supported.",
						self.container, self.mykey, self.pos
					)
				elif op in [8, 9]:
					raise RPLError(
						"Needed to solve y %s x but impossible to invert." % (
							"<<" if op == 8 else ">>"
						), self.container, self.mykey, self.pos
					)
				elif op != 0:
					eq = ({
						3: 30, 4: 3, 6: 7, 7: 6, 11: 11, 30: 3
					}[op], eq, cur[1])
				#endif
			#endif
			cur = cur[idx]
		#endfor

		# Set value.
		value = self.warnfloat(eq, var)
		if solveFor: var[solveFor] = value
		else: ref.set(value)
		return value
	#enddef

	def get(self, var={}): return self.warnfloat(self.data, var)
	def number(self, var={}): return self.warnfloat(self.data, var)
	def string(self): RPLData.string(self)

	def __unicode__(self, x=None):
		if x is None: wasnone, x = True, self.data
		else: wasnone = False
		if type(x) is tuple:
			if x[0] in [0,1]: ret = [u"", u"-"][x[0]] + self.__unicode__(x[1])
			else:
				# TODO: Putting parens here like this is pretty lazy.
				ret = u"(" + self.__unicode__(x[1]) + u" " + [
					u"**", u"*", u"/", u"%", u"+", u"-",
					u"<<", u">>", u"&", u"^", u"|"
				][x[0] - 2] + u" " + self.__unicode__(x[2]) + u")"
			#endif
		else: ret = x
		if wasnone: return '"' + ret + '"'
		else: return ret
	#enddef
#endclass
