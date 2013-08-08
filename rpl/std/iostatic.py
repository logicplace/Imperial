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
	rpl.registerStruct(IOStatic)
#enddef

# Input/Output [dependent] Static
class IOStatic(rpl.Static):
	"""
	Returned data from a key depends on whether we're importing or exporting.
	Format is key: [import, export]
	"""
	typeName = "iostatic"

	def __getitem__(self, key):
		return rpl.Static.__getitem__(self, key)[0 if self.rpl.importing else 1]
	#enddef

	def __setitem__(self, key, value):
		if key not in self.data:
			# Initial set
			try:
				if len(value.list()) != 2: raise RPLBadType()
			except RPLBadType:
				raise RPLError("IOStatic requires each entry to be a list of two values.")
			#endtry
			# This is supposed to be a static! So it should be fine to .list() here.
			self.data[key] = value.list()
		else:
			# When references set it
			self.data[key][0 if self.rpl.importing else 1] = value
		#endif
	#enddef
#endclass
