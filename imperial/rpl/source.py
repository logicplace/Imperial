#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
# source #
## Source ##
"""

from .dynamic import BaseDynamic
from .helper import frozendict

__all__ = ["Source"]

class Source(BaseDynamic):
	pass
#enddef

class Type(LiteralEnum):
	# Explicit
	RIGID   = 1
	IMPLIED = 2
	TYPED   = 3
	SET     = 4
	SOURCED = 5

	# Caches
	CALCULATED = 6
	DEFAULTED  = 7
	INHERITED  = 8

	value2number = frozendict({
		"rigid": RIGID,
		"implied": IMPLIED,
		"typed": TYPED,
		"set": SET,
		"sourced": SOURCED,

		"calculated": CALCULATED,
		"defaulted": DEFAULTED,
		"inherited": INHERITED,
	})

	number2value = LiteralEnum.invert(value2number)

	def is_cache(self):
		"""
		Return True if it is calculated, defaulted, or inherited.
		"""

		return self.number() in (Type.CALCULATED, Type.DEFAULTED, Type.INHERITED)
	#enddef
#endclass