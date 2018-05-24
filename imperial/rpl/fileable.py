#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
# fileable #
## Fileable ##
Subclass this for a struct which represents a particular file
format. It can then translate between itself and that format.

### keys ###
* base - Base within the containing context, typically
         a file path or tag-based selector.
* limit - Number of matches selected must fall in this range.
          Unless this is set to 1 or 1:1, it will creat clones.
          This accepts the following values:
	- number - Must match exactly this many.
	- [min, max] - Must match min <= #matches <= max
	- min~max - Same as above.
	- Default: 1

If a subclass is also Stringifiable, this may use its pretty
key for information about how to format the file.
"""

from .exportable import Exportable
from .serializable import Serializable
from .stringifiable import Stringifiable

from .exceptions import errors
from .registrar import Key
from . import decorators as struct

__all__ = ["Fileable"]

class Fileable(Exportable):
	def register(self):
		return Exportable.get_registrar(keys = [
			Key("base", String),
			Key("limit", Limit),
		])
	#enddef

	@struct.key
	def base(self):
		# TODO: calculate if end and size are defined
		pass
	#enddef

	@struct.to_file
	def to_file(self):
		"""
		SomeStruct.to_file() -> bytes

		Convert this struct to a file in the format it represents.

		Must be defined with @struct.to_file decorator.
		"""
		self.error(errors.MethodUnimplemented,
			"Fileable types must implement to_file")
	#enddef

	@struct.from_file
	def from_file(self, stream):
		"""
		SomeStruct.from_file(bytes)
		SomeStruct.from_file(stream)

		Convert this struct from a file in the format it represents.

		Must be defined with @struct.from_file decorator.
		"""
		self.error(errors.MethodUnimplemented,
			"Fileable types must implement from_file")
	#enddef
#endclass

def noop(*args, **kwargs): pass

class BinaryFile(Fileable, Serializable):
	def to_file(self):
		return self.serialize()
	#enddef

	def from_file(self, stream):
		# This assumes unserialize uses only one base.
		# It wouldn't make sense, otherwise!
		stream.rebase = noop
		self.unserialize(stream)
		return stream
	#enddef
#endclass

class TextFile(Fileable, Stringifiable):
	def register(self):
		return Fileable.get_registrar(keys = [
			Key("encoding", Encoding, "unencoded"),
		])
	#enddef

	def to_file(self):
		string = self["encoding"].encode(self.stringify())
	#enddef

	def from_file(self, stream):
		# This assumes unserialize uses only one base.
		# It wouldn't make sense, otherwise!
		stream.rebase = noop
		self.unserialize(stream)
		return stream
	#enddef
#endclass

class Encoding(Dynamic):
	@struct.define
	def define(self, value):
		# TODO:
		self.encoding = value
	#enddef

	@struct.set
	def set(self, value):
		# TODO:
		self.encoding = value
	#enddef

	@struct.get
	def get(self, value):
		# TODO:
		return self.encoding
	#enddef

	def encode(self, string):
		encoding = self.encoding.resolve()
		try:
			str_encoding = encoding.string()
		except errors.TypeError:

		if isinstance(encoding, str):
			return string.encode(encoding)
		else:
			return encoding(string).serialize()
		#endif
	#enddef

	def decode(self, encoded):
		encoding = self.encoding
		if isinstance(encoding, str):
			return encoded.decode(encoding)
		else:
			ee = encoding()
			ee.unserialize(encoded)
			return ee.string()
		#endif
	#enddef
#endclass
