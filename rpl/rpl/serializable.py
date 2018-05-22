#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
# serializable #
## Serializable ##
Subclass this for a struct which can be un/serialized.

### keys ###
* base - Base within the containing context, typically
         as a file position. In that case it accepts:
	- number - Absolute position in context.
	- [number, relative] - Position relative to:
		+ b - Absolute position.
		+ c - Offset from end of elder sister or start of parent.
		+ e - Offset, backwards, from absolute end of context.
	- Default: [0, c]
	- Reflects: base = end - size
* size - Size of serialized data in bytes.
	- Reflects: size = end - base
* end - Specify the address one byte after the final byte
        included in the serialized data for this struct.
        Accepts the same definitions as base but has no default.
	- Reflects: end = base + size
"""

from .packable import Address, Packable
#from .lists import List, NormalizingStructuredList
#from .mixed import LiteralEnum
#from .contexts import BinaryContext

from .exceptions import errors
from .registrar import Key
from .helper import frozendict
from . import decorators as struct

__all__ = ["Serializable"]

class SerializableAddress(List, Address):
	type = NormalizingStructuredList({
		"fixed": ["number", "string"],
		"defaults": [0, "b"],
	})

	def init(self):
		self.base = 0
		self.relativiser = self.START
	#enddef

	@struct.set
	def set(self, value):
		# Accept None as "default".
		if value is None:
			value = [0, "c"]
			source = { "type": "defaulted" }
		else:
			source = None
		#endif

		self.data = self.type(value, source=source)
	#enddef

	define = set

	@struct.number
	def number(self):
		offset = self.data.number(0)
		rel = self.data.number(1)
		if rel == RelativityMarker.START:
			return offset
		elif rel == RelativityMarker.CURRENT:
			parent = self.parent
			while parent.parent:
				gparent = parent.parent
				if isinstance(gparent, BinaryContext):
					break
				#endif

				older = None

				for child in gparent.children():
					if child is parent:
						if older is None:
							# Get base of gparent or gparent's siblings etc.
							if isinstance(gparent, Serializable):
								return gparent.number("base") + offset
							else:
								parent = gparent
								break
							#endif
						else:
							return older.number("end") + offset
						#endif
					elif isinstance(child, Serializable):
						older = child
					#endif
				#endfor
			#endwhile
			return offset
		elif rel == RelativityMarker.END:
			parent = self.parent.parent
			while parent and not isinstance(parent, BinaryContext):
				parent = parent.parent
			#endwhile

			return parent.size() - offset
		#endif
	#enddef

	get = number
#enddef

class RelativityMarker(LiteralEnum):
	START = 0
	CURRENT = 1
	END = 2

	value2number = frozendict({
		"b": START,
		"c": CURRENT,
		"e": END,
	})

	number2value = LiteralEnum.invert(value2number)
#endclass

class Serializable(Packable):
	address = SerializableAddress

	def register(self):
		return Packable.get_registrar(keys = [
			# Key("base", SerializableAddress, [0, "c"]),
			Key("size", Size),
			Key("end", SerializableAddress),
		])
	#enddef

	def serializable_base(self, key, context):
		"""
		SomeSerializable.serializable_base(key=str, context={BinaryContext}) -> {SerializableAddress}

		Retrieve the base, assuming this is a serializable.
		"""
		if isinstance(context, BinaryContext):
			base = self.keys.get(key)
			if not isinstance(base, SerializableAddress):
				base = self.keys[key] = self.get_address(context)(base, parent=self)
			#endif
			return base
		#endif
	#enddef

	@struct.key
	def size(self):
		# TODO: calculate if base and end are defined
		pass
	#enddef

	@struct.key
	def end(self):
		# TODO: calculate if size and end are defined
		pass
	#enddef

	@struct.serialize
	def serialize(self, stream):
		"""
		SomeStruct.serialize() -> bytes (if only base is 'base')
		SomeStruct.serialize() -> {'base1': bytes, ...}

		Serialize this struct and return the binary.


		SomeStruct.serialize(stream)

		Serialize this struct into the given stream.
		To rebase this, call serialize.rebase(keyname)

		Must be defined with @struct.serialize decorator.
		"""
		self.error(errors.MethodUnimplemented,
			"Serializable types must implement serialize")
	#enddef

	@struct.unserialze
	def unserialize(self, stream):
		"""
		SomeStruct.unserialize(bytes)
		SomeStruct.unserialize({'base': bytes, ...})

		Retrieve data from a serialized form.


		SomeStruct.unserialize(stream)

		Retrieve serialized data from a stream.

		Must be defined with @struct.unserialize decorator.
		"""
		self.error(errors.MethodUnimplemented,
			"Serializable types must implement unserialze")
	#enddef
#endclass
