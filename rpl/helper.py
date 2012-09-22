import codecs
from sys import stderr

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

# So I can be lazy about writing errors
def err(msg): stderr.write(unicode(msg) + "\n")

# TODO: Define some levels
logLevel = 0
def log(level, msg):
	global logLevel
	if level <= logLevel: print "LOG(%i): %s" % (debugLevel, unicode(msg))
#enddef

def readFrom(etc):
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

def writeTo(etc, data):
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

def stream(etc):
	"""
	Helper class to open a file as a stream
	"""
	if type(etc) in [str, unicode]:
		try: etc = open(etc, "r+b")
		except IOError: etc = open(etc, "a+b")
	#endif
	return etc
#enddef

def oneOfIn(l1, l2):
	for x in l1:
		if x in l2: return True
	#endfor
	return False
#enddef

def list2english(l, conjunction=u"and"):
	l = map(unicode, l)
	if len(l) == 1: return l[0]
	elif len(l) == 2: return u"%s %s %s" % (l[0], conjunction, l[1])
	else: return u"%s, %s %s" % (", ".join(l[0:-1]), conjunction, l[-1])
#enddef

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
