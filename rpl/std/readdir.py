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

from .. import rpl, helper
from ..rpl import RPLError, RPLBadType

def register(rpl):
	rpl.registerType(ReadDir)
#enddef

class ReadDir(rpl.Literal):
	"""
	This can be almost any combination of L, R, U, and D.
	LRUD is the general reading direction: Start in upper left and read to the
	right until width, then go down a row. This is how many languages, including
	English, are read.
	RLUD is how Hebrew and Arabic are read.
	UDRL is how traditional Japanese is read.
	LRDU is how bitmap pixels are read.
	Other valid combinations: RLDU, UDLR, DULR, DURL
	One can shorten these to the first and third letters, eg. LU.
	"""
	typeName = "readdir"

	valid = [
		"LRUD", "LRDU", "RLUD", "RLDU", "UDLR", "UDRL", "DULR",
		"DURL", "LU", "LD", "RU", "RD", "UL", "UR", "DL", "DR"
	]

	def set(self, data):
		rpl.Literal.set(self, data)
		if self.data in ReadDir.valid:
			self.primary, self.secondary = (
				"LRUD".index(self.data[0]),
				"LRUD".index(self.data[1 if len(self.data) == 2 else 2])
			)
		else:
			raise RPLError("Reading direction must be one of: %s." %
				helper.list2english(ReadDir.valid, "or")
			)
		#endif
	#endif

	def ids(self): return self.primary, self.secondary

	def rect(self, width, height):
		self.index, self.width, self.height = 0, width, height
		# Inner is Vertical, Inner Range, Outer Range
		self.iv = False
		if   self.primary == 0: self.ir = helper.range(self.width,)
		elif self.primary == 1: self.ir = helper.range(self.width - 1, -1, -1)
		elif self.primary == 2: self.iv, self.ir = True, helper.range(self.height,)
		elif self.primary == 3: self.iv, self.ir = True, helper.range(self.height - 1, -1, -1)
		if   self.secondary == 0: self.ori = iter(helper.range(self.width,))
		elif self.secondary == 1: self.ori = iter(helper.range(self.width - 1, -1, -1))
		elif self.secondary == 2: self.ori = iter(helper.range(self.height,))
		elif self.secondary == 3: self.ori = iter(helper.range(self.height - 1, -1, -1))
		if self.iv: self.x = self.ori.next()
		else: self.y = self.ori.next()
		self.iri = iter(self.ir)
		return self
	#enddef

	def __iter__(self): return self

	def next(self):
		try: ii = self.iri.next()
		except StopIteration:
			# Let this raise stop iteration when it's done
			if self.iv: self.x = self.ori.next()
			else: self.y = self.ori.next()
			self.iri = iter(self.ir)
			return self.next()
		else:
			if self.iv: i, x, y = self.index, self.x, ii
			else: i, x, y = self.index, ii, self.y
			self.index += 1
			return i, x, y
		#endif
	#enddef
#endclass
