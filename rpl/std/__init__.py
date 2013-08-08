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

from data     import Data, Format,                 register as data_register
from map      import Map,                          register as map_register
from iostatic import IOStatic,                     register as iostatic_register
from calc     import Calc,                         register as calc_register
from graphic  import GenericGraphic, Pixel, Color, register as graphic_register
from bin      import Bin,                          register as bin_register
from readdir  import ReadDir,                      register as readdir_register

def register(rpl):
	data_register(rpl)
	map_register(rpl)
	iostatic_register(rpl)
	calc_register(rpl)
	graphic_register(rpl)
	bin_register(rpl)
	readdir_register(rpl)
#enddef

def printHelp(moreInfo=[]):
	helper.genericHelp(globals(), moreInfo,
		"std is the standard library for RPL.", "std", [
			# Structs
			Data, Format,
			Map, IOStatic,
			GenericGraphic,
			Calc,
			# Types
			Bin, Pixel,
			Color, ReadDir,
		]
	)
#enddef
