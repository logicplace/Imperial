#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" lang=en_US
## key ##
Declare this method as a getter for a key.

* @struct.key - Use method name as key name.
* @struct.key(key) - Use given key name.

Must return a subclass of BaseStruct.

### setter ###
Declare this method as a setter for a key.

* @struct.key.setter - Use method name as key name.
* @struct.key.setter(key) - Use given key name.
* @key.setter - Use key name from referenced getter/definer.

### definer ###
Declare this method as a definer for a key.

* @struct.key.definer - Use method name as key name.
* @struct.key.definer(key) - Use given key name.
* @key.definer - Use key name from referenced getter/setter.
"""

from ..exceptions import errors

class key:
	GETTER = 0
	SETTER = 1
	DEFINER = 2
	SETTERDEFINER = 3

	def __new__(cls, arg):
		def namer(name):
			def handler(fun):
				def getter(self):
					return fun(self)
				#enddef
				fun.xer_type = key.GETTER
				fun.name = name
				fun.setter = key.setter(name)
				fun.definer = key.definer(name)

				return getter
			#enddef
			return handler
		#enddef

		if isinstance(arg, str):
			return namer(arg)
		if callable(arg):
			return namer(arg.__name__)(arg)
		raise errors.ArgumentsError("@{} expects a str",
			key.__qualname__)
		#enddef
	#enddef

	@staticmethod
	def setter(arg):
		def namer(name):
			def handler(fun):
				def setter(self, value, source=None):
					ret = fun(self, value)
					ret.set_source(source)
					return ret
				#enddef
				fun.xer_type = key.SETTER
				fun.name = name
				fun.definer = key.definer(name)

				return setter
			#enddef
			return handler
		#enddef

		if isinstance(arg, str):
			return namer(arg)
		if callable(arg):
			return namer(arg.__name__)(arg)
		raise errors.ArgumentsError("@{} expects a str",
			"setter")
		#enddef
	#enddef

	@staticmethod
	def definer(arg):
		def namer(name):
			def handler(fun):
				def definer(self, value, source=None):
					ret = fun(self, value)
					ret.set_source(source)
					return ret
				#enddef
				fun.xer_type = key.DEFINER
				fun.name = name
				fun.setter = key.setter(name)

				return definer
			#enddef
			return handler
		#enddef

		if isinstance(arg, str):
			return namer(arg)
		if callable(arg):
			return namer(arg.__name__)(arg)
		raise errors.ArgumentsError("@{} expects a str",
			"definer")
		#enddef
	#enddef

	@staticmethod
	def setter_definer(arg):
		def namer(name):
			def handler(fun):
				def setterdefiner(self, value, source=None):
					ret = fun(self, value)
					ret.set_source(source)
					return ret
				#enddef
				fun.xer_type = key.SETTERDEFINER
				fun.name = name

				return setterdefiner
			#enddef
			return handler
		#enddef

		if isinstance(arg, str):
			return namer(arg)
		if callable(arg):
			return namer(arg.__name__)(arg)
		raise errors.ArgumentsError("@{} expects a str",
			"setter_definer")
		#enddef
	#enddef
#enddef
