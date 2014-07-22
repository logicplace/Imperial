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

import re, codecs, os
from sys import stderr, stdout
from textwrap import dedent

class RPLInternal(Exception): pass

# So I can be lazy about writing errors
def err(msg): stderr.write(unicode(msg) + "\n")

# TODO: Define some levels
logLevel = 0
def log(level, msg):
	if level <= logLevel: print("LOG(%i): %s" % (debugLevel, unicode(msg)))
#enddef

def makeParents(path):
	path = os.path.dirname(path)
	if not path: return
	try: os.makedirs(path)
	except OSError as err:
		if err.errno == 17: pass
		else: raise RPLInternal('Could not create folders "%s" reason: %s' % (path, err.strerror))
	#endtry
#enddef

def readFrom(etc):
	"""
	Helper class to read from a file or stream
	"""
	try:
		if type(etc) in [str, unicode]:
			x = codecs.open(etc, encoding="utf-8", mode="r")
			ret = x.read()
			x.close()
			return ret
		else: return etc.read()
	except IOError as err: raise RPLInternal("Error reading file: " + err.strerror)
#enddef

def writeTo(etc, data):
	"""
	Helper class to write to a file or stream
	"""
	try:
		if type(etc) in [str, unicode]:
			makeParents(etc)
			x = codecs.open(etc, encoding="utf-8", mode="w")
			ret = x.write(data)
			x.close()
			return ret
		else: return etc.write(data)
	except IOError as err: raise RPLInternal("Error writing to file: " + err.strerror)
#enddef

def stream(etc):
	"""
	Helper class to open a file as a stream
	"""
	if type(etc) in [str, unicode]:
		makeParents(etc)
		try: etc = OverSeek(etc, "r+b")
		except IOError:
			tmp = open(etc, "w")
			tmp.close()
			etc = OverSeek(etc, "r+b")
		#endtry
	#endif
	return etc
#enddef

def oneOfIn(l1, l2):
	for x in l1:
		if x in l2: return True
	#endfor
	return False
#enddef

def allIn(l1, l2):
	for x in l1:
		if x not in l2: return False
	#endfor
	return True
#enddef

def list2english(l, conjunction=u"and"):
	if len(l) == 0: return ""
	l = map(unicode, l)
	if len(l) == 1: return l[0]
	elif len(l) == 2: return u"%s %s %s" % (l[0], conjunction, l[1])
	else: return u"%s, %s %s" % (", ".join(l[0:-1]), conjunction, l[-1])
#enddef

def linechar(string):
	lastnl = string.rfind("\n")
	if lastnl == -1: return 1, len(string)
	else: return string.count("\n"), len(string[lastnl+1:])
#enddef

def typeOrClass(cls):
	try: return cls.typeName
	except AttributeError: return cls.__name__
#enddef

doxSyntax = re.compile(r'<(/?)([a-zA-Z0-9]+)(?: +([^>]+?))? */?>|([^<]+)')

def fetchDox(struct, context, conds, key=None, ignore=None):
	"""
	Supports the markup:
	<help>Preferably one line help for conds.</help> Generated if omitted.
	<mykey>mykey: blah blah blah</mykey>
	<DevDocs hidden>Blah blah</DevDocs> All keys must be named, this can still be
	                                    shown when it's imported.
	<imp class.tagname /> class is basically the same mechanism as above, just
	                      selecting a tag as well.
	<if all>blah blah</if> "all" sent by :all
	<br/> Insert newline manually.
	<me/> Insert name of current struct.
	"""
	parents, do, dox = [[""]], 0, dedent(struct.__doc__)
	for x in doxSyntax.finditer(dox):
		end, tagname, args, text = x.groups("")
		if text.strip() == "": text = ""
		if tagname or do:
			# Command or key
			if tagname == "if":
				if end:
					if do: do -= 1
				elif do: do += 1
				else:
					tmp = args.split(" ")
					t, f = [], []
					for tp in tmp:
						if tp[0] == "!": f.append(tp[1:])
						else: t.append(tp)
					#endfor
					do = 0 if allIn(t, conds) and not oneOfIn(f, conds) else 1
				#endif
			elif do: continue
			elif end:
				if len(parents) == 1:
					raise RPLInternal("Line %i char %i: Extraneous end tag (%s) in help for %s." % (
						linechar(dox[:x.start()]) + (tagname, typeOrClass(struct))
					))
				elif tagname != parents[-1][0]:
					raise RPLInternal("Line %i char %i: Mismatched tags (%s & %s) in help for %s" % (
						linechar(dox[:x.start()]) + (parents[-1][0], tagname, typeOrClass(struct))
					))
				#endif
				if tagname == key: return parents[-1][-1]
				if ((ignore and tagname in ignore) or
					key == "help" or tagname == "help" or "hidden" in parents[-1][1]
				):
					parents.pop()
				else: parents[-2][-1] += parents.pop()[-1]
			elif tagname == "imp":
				imps = args.split()
				for imp in imps:
					if imp == "BR":
						parents[-1][-1] += "\n"
						continue
					#endif
					igs = imp.split("-")
					tmp = igs[0].split(".")
					if not key or tmp[-1] == key:
						cls = context[tmp[0]]
						for attr in tmp[1:-1]: cls = getattr(cls, attr)
						parents[-1][-1] += fetchDox(cls, context, conds, tmp[-1], igs[1:])
					#endif
				#endfor
			elif tagname == "br":
				parents[-1][-1] += "\n"
			elif tagname == "me":
				# TODO: Should refer to topmost struct.
				parents[-1][-1] += typeOrClass(struct)
			else:
				# Key
				parents.append([tagname, args.split(), ""])
		else:
			# Text
			parents[-1][-1] += text
		#endif
	#endfor
	if key: raise RPLInternal("Key %s not found in %s's help." % (key, typeOrClass(struct)))
	return parents[0][0]
#enddef

condSyntax = re.compile(r'<if(?: +([^>]+))?>')

def fetchConds(struct):
	"""
	Just return all conditions in this helpdoc.
	"""
	# TODO: Fetch from imports?
	conds = []
	for x in condSyntax.findall(struct.__doc__):
		conds += [c for c in x.split() if c[0] != "!"]
	#endfor
	if len(conds) > 1:
		return "For more information try any of the tags: " + list2english(conds, "or")
	elif conds: return "For more information try %s:%s" % (struct.typeName, conds[0])
	else: return "No extra information for this struct."
#enddef

def genericHelp(context, moreInfo, desc, lib, defs):
	if not moreInfo:
		structs, types = [], []
		for x in defs:
			# I don't like this cause it restricts types from using a certain
			# attribute, but isinstance isn't working..
			try: x.manage
			except AttributeError: types.append(x.typeName)
			else: structs.append(x.typeName)
		#endfor
		print ("%s\n"
			"It offers the structs:\n  %s\n"
		) % (desc, "  ".join(structs))
		if types: print("And the types:\n  %s\n" % "  ".join(types))
		print("Use --help %s [structs...] for more info" % lib)
	else:
		kdefs = {}
		for x in defs: kdefs[x.typeName] = x
		for x in moreInfo:
			tmp = x.split(":")
			x = tmp[0]
			conds = tmp[1:]
			if "help" in conds:
				try: print(fetchDox(kdefs[x], context, conds, "help").strip())
				except RPLInternal: print(fetchConds(kdefs[x]))
			else: print(fetchDox(kdefs[x], context, conds).strip())
		#endfor
	#endif
#enddef

class OverSeek(file):
	def seek(self, offset, whence=0, byte="\x00"):
		if whence == 0:
			file.seek(self, offset, 0)
			if offset > 0:
				diff = self.tell() - offset
				if diff > 0: self.write(byte * diff)
			#endif
		elif whence == 1:
			start = self.tell()
			file.seek(self, offset, 1)
			if offset > 0:
				diff = self.tell() - start - offset
				if diff > 0: self.write(byte * diff)
			#endif
		elif whence == 2: file.seek(self, offset, 2)
	#enddef
#endclass

class FakeStream(object):
	def __init__(self):
		self.pos = 0
	#enddef

	def seek(self, pos, rel=0):
		if rel == 1: self.pos += pos
		else: self.pos = pos
	#enddef

	def tell(self): return self.pos

	# Maybe this should be randoms :3c
	def read(self, size): return "\0" * size

	def readline(self, size): return ""

	def readlines(self, size): return []

	def write(self, string): pass
	def write(self, seq): pass
	def close(self): pass
	def flush(self): pass
#endclass

# Python 2.7/3.x compatibility
try: range(0).next
except AttributeError:
	class rangeiter(object):
		def __init__(self, start, end, step):
			self.cur, self.start, self.end, self.step = start, start, end, step
		#enddef

		def __iter__(self): return self

		def next(self):
			if ((self.step > 0 and self.cur < self.end) or
				(self.step < 0 and self.cur > self.end)
			):
				next = self.cur
				self.cur += self.step
				return next
			else: raise StopIteration
		#enddef
	#endclass

	class range(object):
		def __init__(self, start, end=None, step=1):
			if end is None: start, end = 0, start
			if ((step > 0 and start > end) or
				(step < 0 and start < end)
			): self.invalid = True
			else: self.invalid = False
			self.start, self.end, self.step = start, end, step
		#enddef

		def __iter__(self):
			return self if self.invalid else rangeiter(self.start, self.end, self.step)
		#enddef

		def next(self): raise StopIteration
	#endclass
else: range = range

def prnt(*args): stdout.write(u" ".join([str(x) for x in args]) + u"\n")
def prntc(*args): stdout.write(u" ".join([str(x) for x in args]) + u" ")