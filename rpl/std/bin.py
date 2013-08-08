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

def register(rpl):
	rpl.registerType(Bin)
#enddef

class Bin(rpl.String):
	"""
	Manages binary data.
	Prints data in a fancy, hex editor-like way.
	"""
	typeName = "bin"

	def set(self, data):
		rpl.String.set(self, data)
		data = re.sub(r'\s', "", self.data)
		self.data = ""
		for i in helper.range(0, len(data), 2):
			self.data += chr(int(data[i:i+2], 16))
		#endfor
	#endif

	def __unicode__(self):
		tmp = self.data
		ret = u""
		lastComment = ""
		while tmp:
			l1, l2 = tmp[0:8], tmp[8:16]
			b1, b2 = Bin.line2esc(l1), Bin.line2esc(l2)[0:-1]
			ret += lastComment
			if l2:
				ret += "`%s %s`" % (b1, b2)
				pad = 23 - len(b2)
			else:
				ret += "`%s`" % b1[0:-1]
				pad = 49 - len(b1)
			#endif
			lastComment = "%s # %s" % (
				" " * pad,
				rpl.String.binchr.sub(".", l1),
			)
			if l2: lastComment += " " + rpl.String.binchr.sub(".", l2) + os.linesep
			tmp = tmp[16:]
		#endwhile
		return ret + "," + lastComment[1:]
	#enddef

	def serialize(self, **kwargs): return self.data
	def unserialize(self, data, **kwargs): self.data = data

	@staticmethod
	def line2esc(ln):
		ret = u""
		for x in ln: ret += u"%02x " % ord(x)
		return ret
	#enddef
#endclass
