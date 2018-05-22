#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

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
