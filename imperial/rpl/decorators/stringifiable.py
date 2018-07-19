#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" lang=en_US
## stringifiable ##
### stringify ###
### parse ###
"""

from ..exceptions import errors

def stringify(fun):
	return fun
#enddef

def parse(fun):
	def handler(string):
		if not isinstance(string, str):
			raise self.error(errors.ArgumentsTypeError,
				"parse expects a str")
		#endif

		return fun(string)
	#enddef
	return handler
#enddef
