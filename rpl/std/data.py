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

import os, re
from .. import rpl, helper
from ..rpl import RPLError, RPLBadType
from copy import deepcopy
from collections import OrderedDict as odict
try: import JSLON
except ImportError: JSLON = None

def register(rpl):
	rpl.registerStruct(Data)
	rpl.registerStruct(Format)
#enddef

class DataStatic(rpl.Static):
	def __init__(self, top, name, parent=None):
		rpl.Static.__init__(self, top, name, parent)
		self.comment = None
	#enddef

	def addChild(self, structType, name):
		"""
		Accepts only statics, and keeps lists of counted structs.
		"""
		child = DataStatic(self.rpl, name, self)
		if name in self.children: self.children[name].append(child)
		else: self.children[name] = [child]
		return child
	#enddef

	def oneUp(self):
		for k, v in self.children.iteritems():
			for x in v:
				x.oneUp()
				if len(x.data) == 0 and len(x.children) == 1:
					self.children[k] = x.children.values()[0]
				#endif
			#endfor
		#endfor
	#enddef

	@staticmethod
	def canBeList(data):
		# If this is a list, it's already in expected form.
		if type(data) is list: pass
		# If this is not a list and only has one key (no children) it's okay.
		elif len(data.data) == 1 and not data.children: return True
		# If it has no keys, check its child.
		elif len(data.data) == 0 and len(data.children) == 1: return canBeList(data.children.values()[0])
		# Was not a list and had more than one keys + children.
		else: return False

		# Check all data.
		for x in data:
			if len(x.data) + len(x.children) > 1: return False
			if x.children and not DataStatic.canBeList(x.children.values()[0]): return False
		#endfor
		return True
	#enddef

	lineEnd = re.compile(r'(?:\r?\n|\n\r?|\r)(?!\n|\r|$)')
	def __unicode__(self, pretty=True, tabs=u"", isList=False):
		if self.comment:
			ret = tabs + u"# " + DataStatic.lineEnd.sub(
				os.linesep + tabs + u"# ", self.comment
			) + os.linesep
		else: ret = u""

		# Create exported name.
		if self.gennedName: name = u""
		else: name = u" " + self.name

		# Create list of keys.
		keys = []
		for k, v in self.data.iteritems():
			v = unicode(v)
			# Check if it ends in a comment.
			parsed = [x.group(0) for x in rpl.RPL.specification.finditer(v)]
			if v.strip() and parsed[-1].lstrip()[0] == "#":
				end, hascomma = os.linesep if v[-len(os.linesep):] != os.linesep else u"", True
			else: end, hascomma = u"", parsed[-1].lstrip()[0] == ","
			if isList: keys.append((v + end, hascomma))
			else:
				next = k + u": "
				keys.append((next + DataStatic.lineEnd.sub(os.linesep + tabs + u" " * len(next), v) + end, hascomma))
			#endif
		#endfor

		# Create list of children.
		children = []
		for k, v in self.children.iteritems():
			if isList or DataStatic.canBeList(v):
				if isList: next = u""
				else: next = u"%s: " % k
				if type(v) is list: l = [x.__unicode__(pretty, tabs + u"\t", True) for x in v]
				else: l = [v.__unicode__(pretty, tabs + u"\t", True)]
				if pretty: next += u"[" + (os.linesep + tabs + u"\t").join([""] + l) + os.linesep + tabs + u"]"
				else: next += u"[" + u", ".join(l) + u"]"
				if isList: children.append(next)
				else: keys.append((next, False))
			else:
				for x in (v if type(v) is list else [v]): children.append(x.__unicode__(pretty, tabs + u"\t"))
			#endif
		#endfor

		if keys: keys[-1] = (keys[-1][0], True)

		if not keys and not children: raise RPLError("Empty...?")
		if isList: return keys[0][0] if keys else children[0]

		if pretty:
			ret += u"%sstatic%s {" % (tabs, name)
			for x, c in keys: ret += os.linesep + tabs + u"\t" + x
			return (
				ret + (os.linesep * 2 if children else u"") +
				os.linesep.join(children) + os.linesep + tabs + u"}"
			)
		else:
			ret += u"%sstatic%s {" % (tabs, name)
			last, n = "", -len(os.linesep)
			for x, c in keys:
				if os.linesep in x and last[n:] != os.linesep: ret += os.linesep
				ret += x + (u"" if c else u", ")
				last = x
			#endfor
			return (
				ret + (os.linesep if children else u"") +
				os.linesep.join(children) + u"}"
			)
		#endif
	#enddef

	def __getitem__(self, key):
		if key in self.children: return rpl.List(self.children[key])
		return self.data[key]
	#enddef

	def __contains__(self, key):
		return key in self.data or key in self.children
	#enddef
#endclass

class DataFile(rpl.Share):
	def add(self, key, item, to):
		"""
		Add item to data.
		"""
		if not isinstance(item, rpl.RPLData):
			raise RPLError("Tried to add non-data to data file.")
		#endif

		to[key] = item
	#enddef
#endclass

class RPLDataFile(DataFile):
	"""
	.rpl export for data structs.
	"""
	def __init__(self, pretty):
		# NOTE: that I'm making the assumption that there will be no duplicate
		# names at the base level, which is primarily because I'm making the
		# further assumption that all cloneables will be unmanaged.
		# Data files only support statics...
		self.base = rpl.RPL()
		self.base.structs = {}
		self.base.registerStruct(DataStatic)

		self.pretty = pretty
	#enddef

	def read(self):
		"""
		Read from .rpl data file.
		"""
		self.base.parse(self.path, dupNames=True)
		for child in self.base: child.oneUp()
	#enddef

	def write(self):
		"""
		Write data to a given file.
		"""
		helper.writeTo(self.path, self.base.__unicode__(self.pretty))
	#enddef

	def addStruct(self, struct, to=None):
		"""
		Add a sub/struct.
		"""
		return (to or self.base).addChild("static", struct)
	#enddef

	def __getitem__(self, key):
		return self.base.children[key]
	#enddef

	def __contains__(self, key):
		return key in self.base.data or key in self.base.children
	#enddef
#endclass

def JSONStringifyElement(v, pretty, tabs):
#	tv = type(v)
#	if   tv is dict: return JSONDict(v).stringify(pretty, tabs)
#	elif tv is list: return JSONList(v).stringify(pretty, tabs)
	try: return v.stringify(pretty, tabs)
	except AttributeError:
		# RPLData.__unicode__ may not always form valid JSON
		# so this has to reinterpret that.
		try: return JSONList(v.list()).stringify(pretty, tabs)
		except RPLBadType:
			try: return '"%s"' % v.string().replace('"', '\\"')
			except RPLBadType:
				return unicode(v.number())
			#endtry
		#endtry
	#endif
#enddef

class JSONDict(odict):
	def __init__(self, x={}):
		self.comment = None
		odict.__init__(self, x)
	#enddef

	def stringify(self, pretty, tabs=u""):
		if pretty:
			ret, end = u"{" + os.linesep, os.linesep + tabs + u"}"
			tabs += u"\t"
			if self.comment: ret += u"%s// %s" % (tabs, self.comment)
			entry, chop = tabs + u'"%s": %s,' + os.linesep, -(1 + len(os.linesep))
		else:
			ret = u"{ "
			if self.comment: ret += u"/* %s */ " % (self.comment)
			entry, end, chop = '"%s": %s, ', u" }", -2
		#endif
		for k, v in self.iteritems(): ret += entry % (k, JSONStringifyElement(v, pretty, tabs))
		return ret[:chop] + end
	#enddef
#endclass

class JSONList(list):
	def oneUp(self):
		tmp = []
		for x in self:
			if not isinstance(x, JSONDict): return self
			if len(x) != 1: return self
			tmp.append(x.values()[0])
		#endfor
		return tmp
	#enddef

	def stringify(self, pretty, tabs=u""):
		if pretty:
			ret, end = u"[" + os.linesep, os.linesep + tabs + u"]"
			tabs += u"\t"
			entry, chop = tabs + u'%s,' + os.linesep, -(1 + len(os.linesep))
		else:
			ret, entry, end, chop = u"[ ", u'%s, ', u" ]", -2
		#endif
		for v in self.oneUp(): ret += entry % (JSONStringifyElement(v, pretty, tabs))
		return ret[:chop] + end
	#enddef

	def list(self): return self
#endclass

class JSONFile(DataFile):
	"""
	.json/.jslon export for data structs.
	"""
	def __init__(self, pretty):
		if JSLON is None:
			raise RPLError(
				"Please install the JSLON library to export JSON files.\n"
				"Download from: https://github.com/logicplace/jslon"
			)
		#endif
		self.base = JSONDict()
		self.pretty = pretty
	#enddef

	@staticmethod
	def invalid(x):
		raise RPLError("JSON type %s is not valid as RPL Data." % type(x).__name__)
	#enddef

	def read(self):
		"""
		Read from JSON data file.
		"""
		self.base = JSLON.parse(helper.readFrom(self.path), {
			"dict": JSONDict, "list": JSONList,
			"string": rpl.String, "int": rpl.Number,
			"float": JSONFile.invalid, "regex": JSONFile.invalid,
			"undefined": JSONFile.invalid,
		})
	#enddef

	def write(self):
		"""
		Write data to a given file.
		"""
		# Needs to make the same assumption as RPLDataFile.
		for x, v in self.base.iteritems(): self.base[x] = v[0]
		helper.writeTo(self.path, self.base.stringify(self.pretty))
	#enddef

	def addStruct(self, name, to=None):
		"""
		Add a sub/struct.
		"""
		if to is None: to = self.base
		child = JSONDict()
		if name in to: to[name].append(child)
		else: to[name] = JSONList([child])
		return child
	#enddef

	def __getitem__(self, key): return self.base[key]
	def __contains__(self, key): return key in self.base
#endclass

class TextFile(DataFile):
	"""
	.txt export for data structs.
	"""
	def __init__(self, pretty):
		self.base, self.struct, self.key, self.pretty = None, None, None, pretty
	#enddef

	def read(self):
		"""
		Read from text file.
		"""
		self.base = rpl.Literal(helper.readFrom(self.path))
	#enddef

	def write(self):
		"""
		Write data to a given file.
		"""
		try: helper.writeTo(self.path, self.base.string())
		except RPLBadType: raise RPLError("Text files only accept one *string*.")
	#enddef

	def addStruct(self, name, to=None):
		"""
		Add a sub/struct.
		"""
		if to is not None:
			raise RPLError("Text files only accept *one* string.")
		#endif

		self.struct = name

		return self
	#enddef

	def add(self, key, item, to):
		if self.base is None or self.key == key:
			self.base = item
			self.key = key
		else:
			raise RPLError("Text files only accept *one* string.")
		#endif
	#enddef

	def __getitem__(self, key):
		if self.struct is None: self.struct = key
		if self.struct == key: return self

		if self.key is None: self.key = key
		if self.key == key: return self.base
		else: raise RPLError("Text files only accept *one* string.")
	#enddef

	def __contains__(self, key):
		if self.struct is None: self.struct = key
		elif self.key is None: self.key = key
		return self.struct == key or self.key == key
	#enddef
#endclass

class DataFormat(object):
	"""
	The mutual parent for Data and Format
	"""
	def __init__(self, top, name, parent):
		self.parentClass = rpl.Serializable if isinstance(self, rpl.Serializable) else rpl.RPLStruct
		self.parentClass.__init__(self, top, name, parent)
		self.format = odict()
		self.command = {}
		self._len = None
		self.count = None
		self.importing = False
		self.onekey = None
	#enddef

	def register(self):
		self.parentClass.register(self)
		self.registerKey("endian", "string:(little, big)", "little")
		self.registerKey("padding", "string", "\x00")
		self.registerVirtual("pad", "padding")
		self.registerKey("align", "string:(left, right, center, rcenter)", "right")
		self.registerKey("sign", "string:(unsigned, signed)", "unsigned")
		self.registerKey("type", "string:(rpl, bin, json)", "")
		self.registerKey("x", "string|[string|reference, number|string:(expand), string|math]+1", "")
		self.registerKey("comment", "string", "")
		self.registerKey("format", "[reference, string].0", "")
	#enddef

	def parseFormat(self, key):
		fmt = self.format[key]
		if fmt is None: raise RPLError("No format for key %s." % key)
		if type(fmt) is list:
			# Let's parse and cache this
			tmp = {
				"type": fmt[0],
				"size": fmt[1],
				"offset": None,
				"offsetRefs": [],
				"end": False,
			}
			if fmt[1].reference():
				refKey = self.refersToSelf(fmt[1])
				if refKey:
					if DataFormat.isCounted(tmp["type"]): self.command[refKey] = ["count", key]
					else: self.command[refKey] = ["len", key]
				#endif
			#endif
			for x in fmt[2:]:
				refKey = None
				if x.reference():
					refKey = self.refersToSelf(x)
					if refKey and self.importing:
						try: self.get(x)
						except RPLError:
							self.command[refKey] = ["offset", key]
							tmp["offsetRefs"].append(x)
							continue
						#endtry
					#endif
				#endif
				val = x.get()
				if type(val) in [int, long]:
					if refKey: self.command[refKey] = ["offset", key]
					if tmp["offset"] is None: tmp["offset"] = val
					else: tmp["offset"] += val
				# We can assume it's str, otherwise
				elif val in ["little", "le"]: tmp["endian"] = "little"
				elif val in ["big", "be"]: tmp["endian"] = "big"
				elif val in ["signed", "unsigned"]: tmp["sign"] = val
				elif val in ["left", "right", "center", "rcenter"]: tmp["align"] = val
				elif val in ["end"]: tmp["end"] = True
				elif len(val) == 1: tmp["padding"] = val
			#endfor
			if "endian"  not in tmp: tmp["endian"]  = self["endian"].string()
			if "sign"    not in tmp: tmp["sign"]    = self["sign"].string()
			if "align"   not in tmp: tmp["align"]   = self["align"].string()
			if "padding" not in tmp: tmp["padding"] = self["padding"].string()
			# If an offset wasn't specified, calculate it from the previous
			# offset plus the previous size. (If it scales from the bottom
			# it must be specified!)
			if tmp["offset"] is None:
				first = True
				for k in self.format:
					if k != key: first = False
					break
				#endfor
				if first: tmp["offset"] = 0
			#endif
			fmt = self.format[key] = tmp
		#endif
		return fmt
	#enddef

	def refersToSelf(self, ref):
		# TODO: Should this also be true if the struct name is its own name?
		# TODO: Should this support multikey or indexing?
		struct, keysets = ref.parts()
		return keysets[0][0] if struct == "this" and keysets and keysets[0][0][0] == "x" else None
	#enddef

	def prepOpts(self, opts, size=True):
		tmp = dict(opts)
		#tmp["type"] = self.get(tmp["type"])
		if size: tmp["size"] = self.get(tmp["size"])
		else: del tmp["size"]
		return tmp
	#endif

	@staticmethod
	def setBase(cls, val):
		try: cls["base"] = val
		except RPLError: cls.base = val
	#enddef

	@staticmethod
	def setLen(cls, val):
		try: cls["size"] = val
		except RPLError: cls.size = val
	#enddef

	@staticmethod
	def isCounted(ref, keylessRefOnly=False):
		return ref.reference() and ref.keyless() and (keylessRefOnly or ref.pointer().sizeFieldType != "len")
	#enddef

	def __getitem__(self, key):
		if key == "format": raise RPLError("Write-only key.", self, key)
		if key in self.data and self.data[key].struct():
			# TODO: Think this through more.
			if self.data[key].sizeFieldType == "len": return self.data[key].basic()
			else: return self.data[key]
		#endif
		try: return self.parentClass.__getitem__(self, key)
		except RPLError:
			if key[0] == "x":
				# If the key doesn't exist yet, we should attempt to retrieve it
				fmt = self.parseFormat(key)
				if self.importing:
					if key in self.command:
						com = self.command[key]
						fmtc1 = self.parseFormat(com[1])
						if com[0] == "len":
							if DataFormat.isCounted(fmt["type"], True):
								# Grab projected size of referenced struct.
								self.data[key] = rpl.Number(fmt["type"].pointer().len())
							else:
								# Grab size of serialized data.
								# TODO: Should this rather be a projected size?
								self.data[key] = rpl.Number(len(
									self[com[1]].serialize(**self.prepOpts(
										fmtc1, size=False
									))
								))
							#endif
						elif com[0] == "count":
							try:
								typeName = self.pointer(fmtc1["type"])
								self.data[key] = rpl.Number(len(self[com[1]].clones))
							except RPLBadType: raise RPLError("Tried to count basic type.")
						elif com[0] == "offset":
							return None
							#offset = self.format[com[1]]["offset"]
							#if offset is None: return None
							#self.data[key] = rpl.Number(offset)
						return self.data[key]
					#endif
					raise RPLError("Somehow have not read data for %s." % key)
				else:
					offset = self.offsetOf(key)
					address = base = self.get("base") + offset
					self.rpl.rom.seek(address)
					size, expand = self.get(fmt["size"]), False
					if size == "expand":
						if fmt["end"]:
							helper.err(RPLError(
								"expand size with end is useless. Ignoring.",
								self, key, self.data[key].pos, etype="Warning"
							))
							fmt["end"] = False
						#endif
						expand = True
						keys = self.format.keys()
						size = self.offsetOf(keys[
							keys.index(key) + 1
						]) - offset
						fmt["size"] = rpl.Number(size)
					#endif
					if DataFormat.isCounted(fmt["type"], True):
						ref = self.pointer(fmt["type"]).clone()
						def tmpfunc(address, t):
							DataFormat.setBase(t, rpl.Number(address))
							try: t.exportPrepare
							except AttributeError: pass
							else:
								try: t.exportPrepare(self.rpl.rom, [], [self])
								except TypeError: t.exportPrepare(self.rpl.rom, [])
							#endif
							return address + t.len()
						#enddef

						if ref.sizeFieldType == "len":
							# Use data until "size".
							if fmt["end"]: fmt["size"], fmt["end"] = rpl.Number(size - address, self.rpl, self, key, *fmt["size"].pos), False
							# Size is length.
							DataFormat.setLen(ref, fmt["size"])
							address = tmpfunc(address, ref)
						else:
							if fmt["end"] or expand:
								# Change this to end address to just use end's functionality
								if expand: size += base
								count = 0
								while address < size:
									address = tmpfunc(address, ref.clone())
									count += 1
								#endwhile
								if address > size:
									raise RPLError("Couldn't fit %s.%s into the available space perfectly." % (self.name, key))
								#endif
								# Adjust to the actual value..
								fmt["size"] = rpl.Number(count)
							else:
								# Size is count.
								for i in helper.range(size): address = tmpfunc(address, ref.clone())
							#endif
						#endif
						self.data[key] = ref
					else:
						if fmt["end"]:
							size, fmt["end"] = size - address, False
							fmt["size"] = rpl.Number(size, self.rpl, self, key, *fmt["size"].pos)
						#endif
						typeName = self.get(fmt["type"])
						self.data[key] = self.rpl.wrap(typeName)
						self.data[key].unserialize(
							self.rpl.rom.read(size),
							**self.prepOpts(fmt)
						)
					#endif
					return self.data[key]
				#endif
			else: raise
		#endtry
	#enddef

	def __setitem__(self, key, value):
		if key == "format":
			data = self.keys[key][0].verify(value)

			if not data.reference():
				try:
					data, prefix = tuple(data.list())
					prefix = prefix.string()
				except RPLError: prefix = ""
			else: prefix = ""

			if data.reference() and data.keyless(): struct = data.pointer()
			else: struct = self.rpl.structsByName[self.get(data)]
			try: struct.format
			except AttributeError:
				raise RPLError("Attempted to reference non-format type.", self, key, value.pos)
			else:
				# Set to managed.
				struct.unmanaged = False
				for x in struct.format:
					dest = "x" + prefix + x[1:] if prefix else x
					self.format[dest] = deepcopy(struct.format[x], {"parent": self})
					# Update the references (this relies on the above being list form..
					# that means the format should only be used in format: calls..
					for d in self.format[dest]:
						if d.reference():
							d.container = self
							d.mykey = dest
							# TODO: Don't like doing direct edits like this.
							if prefix and self.refersToSelf(d): d.keysets[0] = ("x" + prefix + d.keysets[0][0][1:], d.keysets[0][1])
						#endif
					#endfor
				#endfor
			#endtry
		# Special handling for keys starting with x
		# Note: What you set here is NOT the data, so it CANNOT be referenced
		elif key[0] == "x":
			if key not in self.format:
				self.parentClass.__setitem__(self, "x", value)
				tmp = self.data["x"]
				try: tmp = tmp.string()
				except RPLBadType: self.format[key] = tmp.get()
				else: self.format[key] = map(self.rpl.parseData, tmp.split())
				if DataFormat.isCounted(self.format[key][0], True):
					# If it's a reference, it needs to be set as managed.
					try: self.format[key][0].pointer().unmanaged = False
					# Does not exist yet... will need to be set in preparation.
					except RPLError: pass
				del self.data["x"]
			else:
				typeName = self.parseFormat(key)["type"]
				if not DataFormat.isCounted(typeName, True):
					# Recast... TODO: Should this generate a validatation or
					# is this enough?
					self.data[key] = self.rpl.wrap(self.get(typeName), value.get(), self, key, *value.pos)
				else: self.data[key] = value
			#endif
		else:
			self.parentClass.__setitem__(self, key, value)
		#endif
	#enddef

	def shareByType(self, filename, pretty):
		extype, types = self.string("type") or filename.split(os.extsep)[-1], {
			"rpl": RPLDataFile,
			"json": JSONFile,
			"jslon": JSONFile,
			"txt": TextFile,
		}
		if extype == "bin": return "bin"
		if extype not in types:
			raise RPLError(
				'Unknown export type "%s", use "type" key to explicitely define the export type.' % extype,
				self
			)
		#endif
		return self.rpl.share(filename, types[extype], pretty)
	#enddef

	def importPrepare(self, rom, folder, filename=None, data=None, callers=[]):
		self.importing = True
		if filename is None:
			# Should not initially prepare anything if Format type.
			if self.parentClass != rpl.Serializable: return
			filename = self.open(folder, "rpl", True)
		#endif

		if data is None:
			data = self.shareByType(filename, False)[self.name]
			one = False
		else: one = self.oneExport()

		keys = self.format.keys()
		for k in keys: self.parseFormat(k)

		for k in keys:
			if k in self.command: continue
			if one: use = data
			elif k not in data:
				raise RPLError(
					'Key missing from data file "%s"' % (filename),
					self.name, k
				)
			else: use = data[k]
			typeName = self.format[k]["type"]
			if DataFormat.isCounted(typeName, True):
				# If this is the only exported key, it was exported as a list
				# instead of a struct/dict.
				typeName = typeName.pointer()
				typeName.unmanaged = False
				myType = typeName.clone()
				if typeName.sizeFieldType == "len":
					DataFormat.setLen(myType, self.format[k]["size"])
					try: myType.importPrepare(rom, folder, filename, use, callers + [self])
					except TypeError as err:
						# TODO: Can Python be more precise about what's
						# raising the error than this?
						if err.args[0].find("importPrepare") == -1: raise
						myType.importPrepare(rom, folder)
					#endtry
					self[k] = myType
				else:
					for x in use.list():
						t = myType.clone()
						try: t.importPrepare(rom, folder, filename, x, callers + [self])
						except TypeError as err:
							if err.args[0].find("importPrepare") == -1: raise
							t.importPrepare(rom, folder)
						#endtry
					#endfor
					self[k] = myType
				#endif
			else: self[k] = use
		#endfor
	#enddef

	def exportPrepare(self, rom, folder, callers=[]):
		for k in self.format:
			# Set all referenced structs to managed.
			typeName = self.parseFormat(k)["type"]
			if DataFormat.isCounted(typeName, True):
				typeName.pointer().unmanaged = False
			#endif
		#endfor
	#enddef

	def importDataLoop(self, rom, folder, base=None, callers=[]):
		"""
		Initially called from Data.importData
		"""
		if base is None: base = self.get("base")

		for k in self.format:
			fmt = self.format[k]
			data = self[k]
			typeName = self.format[k]["type"]
			if k in self.command:
				com = self.command[k]
				# If this was len, it's currently the size of the serialized data.
				# However, if the key it's for is end type, it needs to be adjusted
				# to the ending address instead.
				# TODO: This currently enforces that if one needs to reference
				# something with the end tag, it needs to be done after that
				# data struct, so that that data struct will be imported first.
				# I don't like this, but moving all this to __getitem__ means
				# that the data can't be changed.. There must be a nicer way to
				# get around this but it might take severe redesigning.
				if com[0] in ["len", "count"]:
					fmtc1 = self.format[com[1]]
					if com[0] == "len" and fmtc1["end"]:
						data = rpl.Number(data.number() + fmtc1["offset"])
					elif com[0] == "count" and fmtc1["end"]:
						# This was actually a count, not a size..
						size = 0
						for x in self.pointer(com[1]).clones: size += x.len()
						data = rpl.Number(size + fmtc1["offset"])
					#endif
				#endif
			#endif
			if DataFormat.isCounted(typeName):
				for x in data.clones:
					try: x.importDataLoop
					# Handle things not specifically meant to be used as data types.
					except AttributeError: x.importData(rom, folder)
					# Handle things that are.
					else: x.importDataLoop(rom, folder, callers=callers + [self])
				#endfor
			elif DataFormat.isCounted(typeName, True):
				x = self.data[k]
				try: x.importDataLoop
				# Handle things not specifically meant to be used as data types.
				except AttributeError: x.importData(rom, folder)
				# Handle things that are.
				else: x.importDataLoop(rom, folder, callers=callers + [self])
			else:
				data = data.serialize(**self.prepOpts(fmt))
				size = self.get(fmt["size"])
				if size != "expand" and len(data) != size:
					raise RPLError("Expected size %i but size %i returned." % (
						size, len(data)
					))
				#endif
				rom.seek(base + fmt["offset"], 0)
				rom.write(data)
			#endif
		#endfor
	#enddef

	def exportDataLoop(self, rom, folder, datafile, to=None, key=None, callers=[]):
		"""
		Initially called from Data.exportData
		Returns RPLData to write to the file
		"""
		to = datafile.addStruct(key or self.name, to)
		to.comment = self.string("comment")
		# Ensures everything is loaded and tagged with commands, so nothing
		# is accidentally exported.. TODO: Not optimal I don't think?
		for k in self.format: self[k]
		for k in self.format:
			# A command implies this data is inferred from the data that's
			# being exported, so it shouldn't be exported itself.
			if k in self.command: continue
			typeName = self.format[k]["type"]
			data = self.data[k]
			if DataFormat.isCounted(typeName, True):
				try: data.exportDataLoop
				except AttributeError:
					# Handle things that aren't.
					if typeName.pointer().sizeFieldType == "len":
						data.exportData(rom, folder)
					else:
						if data.clones:
							for x in data.clones: x.exportData(rom, folder)
						else: datafile.add(k, rpl.List([]), to)
					#endif
				else:
					# Handle things that are specifically meant to be used as data types.
					if typeName.pointer().sizeFieldType == "len":
						data.exportDataLoop(rom, folder, datafile, to, k, callers + [self])
					else:
						if data.clones:
							for x in data.clones:
								x.exportDataLoop(rom, folder, datafile, to, k, callers + [self])
							#endfor
						else: datafile.add(k, rpl.List([]), to)
					#endif
				#endtry
			else: datafile.add(k, data, to)
		#endfor
	#enddef

	def calculateOffsets(self):
		base = self["base"].number()
		calcedOffset = 0
		for k in self.format:
			fmt = self.format[k]
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
				self.set(fmt["offsetRefs"][0], offset)
			elif fmt["offset"] is not None:
				# Absolute offset
				calcedOffset = offset = fmt["offset"]
			#endif
			fmt["offset"] = calcedOffset
			data = self[k]
			typeName = self.format[k]["type"]
			if DataFormat.isCounted(typeName):
				# Size is count.
				tnr = typeName.pointer()
				for x in data.clones:
					try: x.calculateOffsets
					except AttributeError:
						if fmt["end"]:
							# TODO: Next entry should have an offset
							DataFormat.setBase(x, rpl.Number(base + calcedOffset))
						else:
							# Size is count
							for c in tnr.clones:
								DataFormat.setBase(c, rpl.Number(base + calcedOffset))
								calcedOffset += c.len()
							#endfor
						#endelse
					else:
						DataFormat.setBase(x, rpl.Number(base + calcedOffset))
						calcedOffset += x.calculateOffsets()
					#endif
				#endfor
			elif DataFormat.isCounted(typeName, True):
				# Size is length.
				x = self.data[k]
				DataFormat.setBase(x, rpl.Number(base + calcedOffset))
				calcedOffset += x.len()
			else:
				size = self.get(fmt["size"])
				if size == "expand":
					# TODO: I hate this
					size = len(self[k].serialize(**self.prepOpts(
						fmt, size=False
					)))
					fmt["size"] = rpl.Number(size)
				#endif
				calcedOffset += size
			#endif
		#endfor
		return calcedOffset
	#enddef

	def offsetOf(self, key):
		fmt = self.parseFormat(key)
		if fmt["offset"] is not None: return fmt["offset"]
		keys = self.format.keys()
		idx = keys.index(key)
		if idx == 0: fmt["offset"] = self["base"].number()
		else:
			prevKey = keys[idx - 1]
			prevFmt = self.parseFormat(prevKey)
			if DataFormat.isCounted(prevFmt["type"]):
				size = 0
				for x in self[prevKey].clones: size += x.len()
			else:
				size = self.get(prevFmt["size"])
				if size == "expand":
					# TODO: Try to calc from bottom instead?
					raise RPLError("Offset of key (%s) following a key "
						"with expanding size must be known." % key
					)
				#endif
			#endif
			if prevFmt["end"]: fmt["offset"] = size
			else: fmt["offset"] = self.offsetOf(prevKey) + size
			return fmt["offset"]
		#endfor
	#enddef

	def len(self):
		if self._len is not None: return self._len
		size = 0
		for k in self.format:
			fmt = self.parseFormat(k)
			data = self[k]
			if DataFormat.isCounted(self.format[k]["type"]):
				for x in data.clones: size += x.len()
			else: size += self.number(fmt["size"])
		#endfor
		self._len = size
		return size
	#enddef

	def oneExport(self):
		"""
		If there's only one key exported, return the name. Otherwise False.
		"""
		if self.onekey is not None: return self.onekey
		count, onekey = 0, None

		# Ensure commands are set...
		for k in self.format: self.parseFormat(k)

		for k in self.format:
			if k not in self.command: count, onekey = count + 1, k
		#endfor

		if count == 1:
			self.onekey = onekey
			return onekey
		#endif

		self.onekey = False
		return False
	#enddef
#endclass

class Format(DataFormat, rpl.RPLStruct):
	"""
	Represents the format of packed data.
	Same as [data] but does not import or export directly.
	<all>
	To describe the format, one must add keys prefixed with "x"
	Order is important, of course. The format for a field's description is:
	[type, size, offset?, endian?, sign?, pad char?, alignment?, end?]
	All entries with a ? are optional, and order of them doesn't matter.
	    Type: Datatype by name, for example: string, number
	          This may also be a reference to a struct.
	    Size: Size of the field in bytes or number of entries of this type.
	          The latter can only be used when referencing a struct in the type
	          field, but that struct's type can define whether it's regarded as
	          length or count. Check the type's documentation for details.
	          This may be set to "expand" to use the whole space until the next
	          entry. Because of this, the next entry will likely need an explicit
	          offset.
	    Offset: Offset from base to where this entry is. By default this is
	            calculated from the sizes, but there are times it may be
	            necessary to supply it (dynamic sizing in the middle).
	    Endian: Only relevant to numbers, can be "little" or "big"
	    Sign: Only relevant to numbers, can be "signed" or "unsigned"
	    Pad char: Only relevant to strings, it's the char to pad with.
	    Alignment: Only relevant to strings, can be "left", "right", "center",
	               or "rcenter"
	    End: Rather than size, Size is actually the address to stop reading.
	         Therefore it's exclusive. Use the literal word "end"
	<endian>
	endian:  Default endian, may be "little" or "big". Defaults to "little"</endian>
	<padding>
	padding: Default padding character, default is "$00"
	pad:     Alias of padding.</pad>
	<padside>
	align:   Default padside, may be "left", "right", "center", or "rcenter".
	         Default is "right"</padside>
	<sign>
	sign:    Default sign, may be "signed" or "unsigned". Defaults to "unsigned"</sign>
	<comment>
	comment: Comment to write to the file. Great for when sharing the file.</comment>
	<format>
	format:  Copy the x keys from given format struct *at this point* in the
	         data struct. This is a write-only key.</format></all>
	"""
	typeName = "format"

	def __init__(self, top, name, parent=None):
		DataFormat.__init__(self, top, name, parent)
		self.base = None
	#enddef

	def base(self, value=None, rom=None, offset=0):
		if rom is None: rom = self.rpl.rom
		rom.seek(self.base.get() + offset)
		return rom.tell()
	#enddef

	def __getitem__(self, key):
		if key == "base":
			return self.base
		else: return DataFormat.__getitem__(self, key)
	#enddef

	def __setitem__(self, key, value):
		if key == "base":
			self.base = value
		else: return DataFormat.__setitem__(self, key, value)
	#enddef
#endclass

# TODO: Support txt and csv exports
class Data(DataFormat, rpl.Serializable):
	"""
	Manages un/structured binary data.
	<if all><imp rpl.Serializable.all />
	</if>
	<imp Format.all />
	<pretty>
	pretty:  Pretty print data, particularly relevant to lists.</pretty>
	"""
	typeName = "data"

	def register(self):
		DataFormat.register(self)
		self.registerKey("pretty", "bool", "false")
	#enddef

	def importPrepare(self, rom, folder):
		filename = self.open(folder, "rpl", True)
		if self.shareByType(filename, False) == "bin":
			self.rpl.rom = newrom = helper.stream(filename)
			self.exportPrepare(newrom, folder)
			for k in self.format: self[k].get()
			newrom.close()
			self.rpl.rom = rom
		else: DataFormat.importPrepare(self, rom, folder, filename)
	#enddef

	def importData(self, rom, folder):
		self.calculateOffsets()
		self.importDataLoop(rom, folder)
	#enddef

	def exportData(self, rom, folder):
		filename = self.open(folder, "rpl", True)
		datafile = self.shareByType(filename, self.get("pretty"))
		if datafile == "bin":
			try: os.unlink(filename)
			except OSError as err:
				if err.errno == 2: pass
				else:
					raise RPLError(
						'Error removing bin file "%s" before exporting: %s' % (filename, err.args[1]),
						self
					)
				#endif
			#endif
			rom = helper.stream(filename)
			self.importData(rom, folder)
			rom.close()
		else: self.exportDataLoop(rom, folder, datafile)
	#enddef
#endclass

