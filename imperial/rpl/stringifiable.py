#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
# stringifiable #
## Stringifiable ##
Subclass this for a struct which can be stringified and parsed.

### keys ###
* base - Base within the containing context, typically
         a selector of some sort represented as a string.
* limit - Number of matches selected must fall in this range.
          Unless this is set to 1 or 1:1, it will creat clones.
          This accepts the following values:
	- number - Must match exactly this many.
	- [min, max] - Must match min <= #matches <= max
	- min~max - Same as above.
	- Default: 1:any
* pretty - Specify any pretty-printing options relevant to this.
"""

from .exportable import Exportable
from .specialized import Specialized

from .exceptions import errors
from .registrar import Key
from . import decorators as struct

__all__ = ["Stringifiable", "Pretty"]

class Stringifiable(Exportable):
	def register(self):
		return Exportable.get_registrar(keys = [
			Key("base", String),
			Key("limit", Limit),
			Key("pretty", Pretty),
		])
	#enddef

	@struct.key
	def base(self):
		# TODO: calculate if end and size are defined
		pass
	#enddef

	@struct.stringify
	def stringify(self):
		"""
		SomeStruct.stringify() -> str

		Stringify this struct and return the resulting str.

		Must be defined with @struct.stringify decorator.
		"""
		self.error(errors.MethodUnimplemented,
			"Stringifiable types must implement stringify")
	#enddef

	@struct.parse
	def parse(self, string):
		"""
		SomeStruct.parse(str)

		Retrieve stringified data from a str.

		Must be defined with @struct.parse decorator.
		"""
		self.error(errors.MethodUnimplemented,
			"Stringifiable types must implement parse")
	#enddef
#endclass

class Pretty(Specialized):
	# Register any key.
	def define_unregistered(self, key, value):
		return value
	#enddef

	def set_unregistered(self, key, value):
		return value
	#enddef
#enddef
