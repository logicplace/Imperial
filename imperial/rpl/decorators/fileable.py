#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

""" lang=en_US
## fileable ##
### to_file ###
### from_file ###
"""

from io import IOBase, BytesIO

from ..exceptions import errors

def to_file(fun):
	return fun
#enddef

def from_file(fun):
	def handler(self, stream):
		if isinstance(stream, bytes):
			stream = BytesIO(stream)
		elif not isinstance(stream, IOBase):
			raise self.error(errors.ArgumentsTypeError,
				"fromfile expects a stream or bytes")
		#endif

		return fun(stream)
	#enddef
	return handler
#enddef
