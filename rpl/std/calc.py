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
	rpl.registerStruct(Calc)
#enddef

class Calc(rpl.Static):
	"""
	Works the same as static, but all data is of the math type.
	Allows for calculations in places where they're not directly allowed,
	for some reason.
	"""
	typeName = "calc"

	def __setitem__(self, key, value):
		try: self.data[key] = self.rpl.wrap("math", value.string(), value.container, value.mykey, *value.pos)
		except RPLBadType:
			# If .string() or wrapping fails, try it as a number.
			try: value.number()
			except RPLBadType:
				raise RPLError(
					"Entries in calc must be math.",
					value.container, value.mykey, value.pos
				)
			else: self.data[key] = value
		#endtry
	#enddef
#endclass
