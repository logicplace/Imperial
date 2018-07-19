#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

""" lang=en_US
# registrar #
## Classes ##
### Registrar ###
Create a Registrar for managing common properties of a struct type.

### Key ###
Represents a key for use in a Registrar.
"""

from operator import itemgetter
from collections import namedtuple

from .base import BaseStruct
from .helper import mixed, frozendict

__all__ = ["Registrar", "Key"]

class Registrar(tuple):
	"""
	Registrar(keys=[...], structs=[...], types=[...])

	Manage registrations of keys, substructs, and types for a struct type.

	keys are the defined keys in a struct type. It accepts:
	* A list of rpl.rpl.registrar.Key.

	structs are the allowed substructs in a struct type. It accepts:
	* A list of structs which have *typename* defined.
	* A dict of name to struct.
	* A rpl.rpl.helper.mixed of both.
	* Where a struct is a subclass of rpl.rpl.base.BaseStruct.

	types are the additional custom types in a struct type.  
	Rather than being allowed as substructs, they can be used as keystructs or
	 referenced by constructions which refer to types by name.

	types accepts the same things as structs. 

	Raises
	* TypeError - if keys, structs, types, or an entry within them is of the wrong type.
	"""

	# Overrideable for test cases.
	base_struct = BaseStruct

	def __new__(cls, *, keys=None, structs=None, types=None):
		normal_keys = {}
		normal_structs = {}
		normal_types = {}

		if keys is None: keys = ()

		if not isinstance(keys, (list, tuple)):
			raise TypeError("keys")
		#endif

		def struct_iter(name, arg):
			if arg is None:
				return iter(())
			elif isinstance(arg, (list, tuple)):
				return enumerate(arg)
			elif isinstance(arg, dict):
				return arg.items()
			else:
				raise TypeError(name)
			#endif
		#enddef

		structs_iter = struct_iter("structs", structs)
		types_iter = struct_iter("types", types)

		tuplize = set()
		for key in keys:
			if not isinstance(key, Key):
				raise TypeError("keys")
			#endif

			key_name = key.name

			if key.contextual:
				normal_keys.setdefault(key_name, []).append(key)
				tuplize.add(key_name)
			else:
				normal_keys[key_name] = key
			#endif
		#endfor

		for key in tuplize:
			normal_keys[key] = tuple(normal_keys[key])
		#endfor

		def loop_into(name, it, normals):
			for k, s in it:
				if not isinstance(s, self.base_struct):
					raise TypeError(name)
				#endif

				if isinstance(k, int):
					k = s.typename
				#endif

				normals[k] = s
			#endfor
		#enddef

		loop_into("structs", structs_iter, normal_structs)
		loop_into("types", types_iter, normal_types)

		return tuple.__new__(cls, (
			frozendict(normal_keys),
			frozendict(normal_structs),
			frozendict(normal_types),
		))
	#enddef

	def __call__(self, *, keys=None, structs=None, types=None):
		"""
		{Registrar}(keys=[...], structs=[...], types=[...])

		Copies the registrar while adding these new keys, structs, and types.

		In order to select only a subset of keys, for instance, use this form:
		Registrar(keys = parent.keys("key1", ...) + [Key("mykey", ...)])

		If a supplied key name is already in use, it will use the new one.

		Raises:
		* TypeError - if keys, structs, types, or an entry within them is of the wrong type.
		"""
		if not isinstance(keys, (list, tuple)):
			raise TypeError("keys")
		#endif

		def combine(name, idx, arg):
			data = self[idx]
			if arg is None:
				return data
			if isinstance(arg, dict):
				data = dict(data)
				data.update(arg)
				return data
			if isinstance(arg, (list, tuple)):
				data = mixed(data)
				data.update(enumerate(arg))
				return data
			raise TypeError(name)
		#enddef

		return Registrar(
			keys = type(keys)(self[0]) + keys,
			structs = combine("structs", 1, structs),
			types = combine("types", 2, types))
	#enddef

	def __bool__(self): return True

	def __get(self, type, idx, name):
		normals = self[idx]
		if name in normals:
			return normals[name]
		else:
			raise KeyError((type, name))
		#endif
	#enddef

	def key(self, name, struct=None):
		"""
		registrar.key(name) -> rpl.rpl.registrar.Key

		Get the key definition of *name*.


		registrar.key(name, struct) -> rpl.rpl.registrar.Key

		Get the key definition of *name* for a contextually typed key.

		Raises:
		* KeyError - if name is not defined.
		* TypeError - contextual key but no valid struct provided
		"""
		key = self.__get("key", 0, name)

		if isinstance(key, tuple):
			if struct is None:
				raise TypeError("struct")
			#endif

			for test in key:
				if test.test(struct):
					return BoundKey(test, struct)
				#endif
			#endfor

			raise TypeError("struct")
		else:
			return key
		#endif
	#enddef

	def keys(self, *names):
		"""
		registrar.keys() -> [rpl.rpl.registrar.Key, ...]

		Get all key definitions.

		registrar.keys(name, ...) -> [rpl.rpl.registrar.Key, ...]

		Get the key definitions of each *name*.

		Raises:
		* KeyError - if name is not defined.
		"""
		if not names:
			return list(self[0].values())
		#endif

		return [self.key(name) for name in names]
	#enddef

	def struct(self, name):
		"""
		registrar.struct(name) -> rpl.rpl.base.BaseStruct

		Get the struct definition of *name*.

		Raises:
		* KeyError - if name is not defined.
		"""
		return self.__get("struct", 1, name)
	#enddef

	def structs(self, *names):
		"""
		registrar.structs() -> [rpl.rpl.base.BaseStruct, ...]

		Get all struct definitions.

		registrar.structs(name, ...) -> [rpl.rpl.base.BaseStruct, ...]

		Get the struct definitions of each *name*.

		Raises:
		* KeyError - if name is not defined.
		"""
		if not names:
			return list(self[1].values())
		#endif

		return [self.struct(name) for name in names]
	#enddef

	def has_struct(self, cls):
		"""
		registrar.has_struct(cls=BaseStruct) -> bool

		Return whether or not this cls is registered as a substruct.
		"""
		for x in self[1].values():
			if issubclass(cls, x): return True
		return False
	#enddef

	def type(self, name):
		"""
		registrar.type(name) -> rpl.rpl.base.BaseStruct

		Get the type definition of *name*.

		Raises:
		* KeyError - if name is not defined.
		"""
		return self.__get("type", 2, name)
	#enddef

	def types(self, *names):
		"""
		registrar.types() -> [rpl.rpl.base.BaseStruct, ...]

		Get all type definitions.

		registrar.types(name, ...) -> [rpl.rpl.base.BaseStruct, ...]

		Get the type definitions of each *name*.

		Raises:
		* KeyError - if name is not defined.
		"""
		if not names:
			return list(self[2].values())
		#endif

		return [self.type(name) for name in names]
	#enddef

	def has_type(self, cls):
		"""
		registrar.has_type(cls=BaseStruct) -> bool

		Return whether or not this cls is registered as a type.
		"""
		for x in self[2].values():
			if issubclass(cls, x): return True
		return False
	#enddef
#endclass

class Sentinel: pass
NO_DEFAULT = Sentinel()

BaseKey = namedtuple("Key", ["name", "raw_type", "raw_default"])
class Key(BaseKey):
	"""
	Key(name, typing[, default])

	Represent a key definition for use in a struct's registrar.

	name: str. Internal name of the key, always possible in struct definition.

	typing: dict. Describe the rigid portion of a struct type.  
		Turns into the target type lazily.  
		{ "": subclass of BaseStruct, **dict to pass to it as rigid data }

	default: Any. When a default is requested, it passes this like type(default)  
		This means it's the *data* argument to a BaseStruct, whatever that entails.

	Raises:
	* TypeError - if type is not a dict or does not contain a "" key that's a BaseStruct.
	"""

	# Overrideable for test cases.
	base_struct = BaseStruct

	_cached_type = None

	def __new__(cls, name, typing, default=NO_DEFAULT, *, ancestor=None):
		contextual = False

		if isinstance(typing, dict):
			try:
				struct_type = typing.pop("")
			except KeyError:
				raise TypeError("typing")
			#endtry

			if not issubclass(struct_type, self.base_struct):
				raise TypeError("typing")
			#endif
		elif issubclass(type, self.base_struct):
			struct_type = typing
			typing = {}
		elif callable(typing):
			struct_type = typing
			typing = {}

			if not issubclass(ancestor, self.base_struct):
				raise TypeError("ancestor")
			#endif

			contextual = True
		else:
			raise TypeError("typing")
		#endif

		ret = BaseKey.__new__(
			cls,
			name = name,
			raw_type = (struct_type, frozendict(typing), ancestor),
			raw_default = default)

		ret.contextual = contextual

		return ret
	#enddef

	def __call__(self, name, default=NO_DEFAULT):
		"""
		Copy this Key with a different name and/or default.
		If nothing changes, it does not create a copy.
		"""
		if self.name is not None and self.name == name and (
			default is NO_DEFAULT or self.default == default
		):
			return self
		#endif

		return Key(
			name = name,
			type = self.type,
			default = self.default if default is NO_DEFAULT else default)
	#enddef

	# This is just an adaptor to make Registrar.__new__'s register function easier.
	typename = property(itemgetter(2))

	def test(self, struct=None):
		type, data, ancestor = self.raw_type

		if ancestor is None:
			return type, data
		else:
			if not isinstance(struct, self.base_struct):
				return False
			#endif

			parent = struct.parent
			while parent is not None:
				if isinstance(parent, ancestor):
					type = type(parent)

					if type is None:
						return False
					#endif

					return type, data
				#endif
			#endwhile

			return False
		#endif
	#enddef

	def type(self, struct=None):
		"""
		{Key}.type -> BaseStruct

		Return the BaseStruct of the type. Create it if needed.

		Raises:
		* TypeError - if this is a contextual type an no valid struct was provided
		* rpl.rpl.exceptions.TypeError - if the rigid structure is invalid.
		"""
		test = self.test(struct)

		if test is False:
			raise TypeError("struct")
		#endif

		type, data = test
		contextual = self.contextual

		if contextual:
			# TODO: Cached by type
			pass
		elif self._cached_type is not None:
			return self._cached_type
		#endif

		ret = type(data, source = { "type": "implied" })

		if contextual:
			# TODO: Cached by type
			pass
		else:
			self._cached_type = ret
		#endif

		return ret
	#enddef

	def default(self, parent, struct=None):
		"""
		{Key}.default(parent) -> BaseStruct or None

		Return None if this key has no default.  
		Return type(default) otherwise.

		Raises:
		* rpl.rpl.exceptions.RPLTypeError - if default is not valid for this type.
		"""
		if not self.has_default():
			return None
		#endif

		# Cast the default and set its source as defaulted.
		ret = self.type(struct)(self.raw_default, source = { "type": "defaulted" })
		ret.parent = parent
		return ret
	#enddef

	def has_default(self):
		"""
		{Key}.has_default() -> bool

		Return whether or not this key defines a default value.
		"""
		return not self.raw_default is NO_DEFAULT
	#enddef
#endclass

class BoundKey:
	def __init__(self, key, struct):
		self.key = key
		self.struct = struct
	#enddef

	def type(self):
		return self.key.type(self.struct)
	#enddef

	def default(self, parent):
		return self.key.default(parent, self.struct)
	#enddef

	def has_default(self):
		return self.key.has_default()
	#enddef
#endclass
