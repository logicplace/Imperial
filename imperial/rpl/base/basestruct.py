#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
# base #
## BaseStruct ##
Base struct class for all struct types.

Typically a struct type should base off of either:

* Static
* Specialized
* Value
* Serializeable
* Stringifiable
* Fileable
"""

import copy
import time
from collections import OrderedDict

from ..makers import Basic
from ..statics import BaseStatic

from ..exceptions import errors, warnings
from .. import decorators as struct

from .metaclass import StructMetaclass
from .lazystruct import LazyStruct, unlazy

__all__ = ["BaseStruct"]

class BaseStruct(metaclass=StructMetaclass):
	"""
	Base for all struct types.

	* If data is a dict, it contains keys of possibly uninstantiated data.
	* Otherwise, data is some basic data.
	* If source is None (and data doesn't have one), it is assumed to be set by an unknown source.
		- This should only be used for testing and one-offs...
	* source: A dict containing:
		- type: One of: "rigid", "implied", "calculated", "defaulted", "inherited", "sourced", "set"
		- ...
	* name: Name provided in structural position.
	* parent: The containing struct, checks this next if a key doesn't have a value when bubbling.
	* bubble: Whether or not to bubble up when missing a key.
	"""

	nocopy = ["clones", "parent"]

	def __init__(self, data, *, name=None, parent=None, source=None, bubble=True, invisible=None, children=None):
		self.name = name
		self.parent = parent
		self.source = None
		self.set_source(source or { "type": "set" })
		self.bubbling = bubble

		# Basic caches
		self.changed = 0
		self.cached = {
			"get": (None, None),
			"number": (None, None),
			"string": (None, None),
			"list": (None, None),
		}
		self.reflects = []

		# Keys
		self.rigid = OrderedDict()
		self.sourced = {}

		self.child = OrderedDict()
		self.clones = []

		if isinstance(invisible, dict) and invisible:
			data.update(invisible)
			self.invisible = set(invisible.keys())
		else:
			self.invisible = set()
		#endif

		self.init()

		self.define(data)
		if children is not None: self.add_children(children)

		self.postinit()
	#enddef

	def init(self):
		"""
		Do initializations without affecting __init__ before data is defined.
		Use @struct.super decorator to call all parent init functions.
		"""
		pass
	#enddef

	def postinit(self):
		"""
		Do initializations without affecting __init__ after data is defined.
		Use @struct.super decorator to call all parent postinit functions.
		"""
		pass
	#enddef

	def __call__(self, data=None, *, name=None, parent=None, source=None, bubble=None, invisible=None):
		if self._basic_instantiation and data is None (self.source is None or source is None):
			# Just set to self and return.
			if name is not None: self.name = name
			if parent is not None: self.parent = parent
			if bubble is not None: self.bubbling = bubble
			self.set_source(source)

			return self
		#endif

		new = copy.deepcopy(self)

		if name is not None: new.name = name
		if parent is not None: new.parent = parent
		if bubble is not None: new.bubbling = bubble

		if data is None: data = {}

		if isinstance(invisible, dict) and invisible:
			data.update(invisible)
			new.invisible.union(invisible.keys())
		#endif

		if not isinstance(data, dict) or data:
			new.define(data)
		#endif

		new.set_source(source)

		return new
	#enddef

	def __deepcopy__(self, memo):
		ret = object.__new__(self.__class__)
		memo[id(self)] = ret
		for attr, value in self.__dict__.items():
			if attr in self.nocopy:
				setattr(ret, attr, value)
			else:
				setattr(ret, attr, copy.deepcopy(value, memo))
			#endif
		#endfor

		return ret
	#enddef

	def clone(self, **kwargs):
		# TODO:
		pass
	#enddef

	@property
	def typename_for_error(self):
		try:
			name = self.typename
		except AttributeError:
			name = None
		#endtry

		return name or self.__class__.__name__
	#enddef


	def define(self, value):
		"""
		SomeStruct.define(basic) -> SomeStruct

		Instantiate SomeStruct with this basic value.


		SomeStruct.define(OrderedMixed((key, value), child, ...)) -> SomeStruct

		Instantiate several keys in SomeStruct with their
		respective values as rigid data.


		In either case, SomeStruct's data is cleared and its
		substructs are destroyed.


		When implementing in a struct type class, expect a
		value of type base.makers.Basic or OrderedMixed and
		return an OrderedMixed containing the keys and
		substructs. Thus:

		define(Basic/OrderedMixed) -> OrderedMixed
		"""
		raise self.error(errors.MethodUnimplemented,
			"struct types must implement define")
	#enddef

	def set(self, value):
		"""
		SomeStruct.setter(basic) -> SomeStruct

		Set SomeStruct to be this basic value.


		SomeStruct.setter(key, value) -> SomeStruct

		Set this value to a key in SomeStruct.


		SomeStruct.setter({ key: value, ... }) -> SomeStruct

		Set these values to their respective several keys in SomeStruct.


		When implementing in a struct type class, expect a
		basic of type base.makers.Basic
		"""
		raise self.error(errors.NoBasicValue,
			"cannot set basic value for this struct type")
	#enddef

	def get(self):
		"""
		SomeStruct.get() -> python value

		Retrieve the basic value of SomeStruct.


		SomeStruct.get("key") -> python value

		Retrieve the basic value of this key from SomeStruct.


		SomeStruct.get(("key", ..., "final")) -> python value

		Retrieve the basic value of some key final in some ...
		from some key from SomeStruct.
		"""
		raise self.error(errors.NoBasicValue,
			"cannot get basic value for this struct type")
	#enddef

	def number(self):
		"""
		SomeStruct.number() -> int

		Retrieve the basic value of SomeStruct as a number.


		SomeStruct.number("key") -> int

		Retrieve the basic value of this key from SomeStruct as a number.


		SomeStruct.number(("key", ..., "final")) -> int

		Retrieve the basic value of some key final in some ...
		from some key from SomeStruct as a number.


		Note: This does not cast or coerce the value.
		"""
		raise self.error(errors.NoBasicValue,
			"cannot get basic value as a number for this struct type")
	#enddef

	def string(self):
		"""
		SomeStruct.string() -> str

		Retrieve the basic value of SomeStruct as a string.


		SomeStruct.string("key") -> str

		Retrieve the basic value of this key from SomeStruct as a string.


		SomeStruct.string(("key", ..., "final")) -> str

		Retrieve the basic value of some key final in some ...
		from some key from SomeStruct as a string.


		Note: This does not cast or coerce the value.
		"""
		raise self.error(errors.NoBasicValue,
			"cannot get basic value as a string for this struct type")
	#enddef

	def list(self):
		"""
		SomeStruct.list() -> list

		Retrieve the basic value of SomeStruct as a list.


		SomeStruct.list("key") -> list

		Retrieve the basic value of this key from SomeStruct as a list.


		SomeStruct.list(("key", ..., "final")) -> list

		Retrieve the basic value of some key final in some ...
		from some key from SomeStruct as a list.


		Note: This does not cast or coerce the value.
		"""
		raise self.error(errors.NoBasicValue,
			"cannot get basic value as a list for this struct type")
	#enddef

	def resolve(self):
		"""
		SomeReference.resolve() -> SomeStruct
		SomeReference.resolve("key") -> SomeStruct
		SomeReference.resolve(("key", ..., "final")) -> SomeStruct

		Retrieve the referent.


		SomeStruct.resolve() -> SomeStruct
		SomeStruct.resolve("key") -> SomeStruct
		SomeStruct.resolve(("key", ..., "final")) -> SomeStruct

		Returns itself (no reference to resolve).


		If you want to see references, use SomeStruct["key"] instead.
		"""
		return self
	#enddef

	def reference(self):
		raise self.error(NonReferenceError,
			"not a reference")
	#enddef

	def __getitem__(self, key):
		"""
		SomeStruct[key] -> {BaseStruct}

		Get the struct contained in this key.


		SomeStruct[(key1, key2, ...)] -> {BaseStruct}

		Equivalent to SomeStruct[key1][key2][...]
		"""
		if isinstance(key, (list, tuple)):
			key, *remain = key
			if remain:
				return self[key].resolve()[remain]
			#endif
		#endif

		# Return if already set.
		if key in self.rigid:
			return self.rigid[key]
		if key in self.sourced:
			return self.sourced[key]
		#endif

		# Attempt to inherit.
		if self.bubbling:
			parent = self.parent
			while parent is not None and key in self.parent.invisible:
				parent = parent.parent
			#endwhile

			if parent is not None:
				ret = self.sourced[key] = parent[key](source = { "type": "inherited" })
				return ret
			#endif
		else:
			raise self.error(errors.UndefinedKey,
				"{key} is not set in this struct", key=key)
		#endif
	#enddef

	@property
	def changed(self):
		return self._changed
	#enddef

	@changed.setter
	def changed(self, value):
		self._changed = time.time() if value is None else value
		self.invalidate()
	#enddef

	def invalidate(self):
		"""
		SomeStruct.invalidate()

		Invalidate all caches for basic values of SomeStruct.
		"""
		cached = self.cached
		for key in cached:
			cached[key] = (None, None)
		#endfor
	#enddef

	def change(self):
		self._changed = time.time()
		self.invalidate()
	#enddef


	def add_child(self, child):
		"""
		SomeStruct.add_child(child)

		Append a substruct to SomeStruct.

		This calls SomeStruct.struct(child) to determine if it's allowed.

		child may be:
		* str - Instantiate an empty version of this type.
		* BaseStruct - Instantiate an empty version of this specific type class.
		* {BaseStruct} - Add this child directly.
		"""
		if isinstance(child, str) or issubclass(child, BaseStruct):
			child = LazyStruct(child, {}, source={ "type": "set" })
		if isinstance(child, LazyStruct):
			child = child.create(self)
		elif isinstance(child, BaseStruct):
			current_class = child.__class__
			expected_class = self.struct(current_class)
			if current_class is not expected_class:
				new_child = expected_class(current_class, parent=self)
				self.warn(warnings.LibraryWarning,
					"type class replacement during add_child: {type1} -> {type2}",
					type1 = child.typename_for_error,
					type2 = new_child.typename_for_error)
				child = new_child
			#endif
		else:
			self.error(errors.ArgumentsTypeError,
				"add_child expects child to be a struct type")
		#endif

		name = child.name or len(self.child)
		self.child[name] = child
	#enddef

	def add_children(self, children):
		"""
		SomeStruct.add_child(children=[{BaseStruct}])

		Append multiple substructs to SomeStruct.
		"""
		for child in children:
			self.add_child(child)
		#endfor
	#enddef

	def children(self):
		"""
		SomeStruct.children() -> iter

		Iterate over children of SomeStruct in the order
		they were added. If a static is encountered, this
		descends into it and iterates its children in order
		and etc.
		"""
		return ChildrenIterartor(self.child.values())
	#enddef


	def set_source(self, source):
		"""
		SomeStruct.set_source(source)

		Change the source of SomeStruct.

		If there is a current source which is not the same, it will
		attempt to encapsulate the source so that both are represented.
		"""
		# TODO: if there's already a source, encapsulate
		self.source = Source(source)
	#enddef

	def valueize(self, value):
		"""
		SomeStruct.valueize(value) -> BaseValue(value)

		Return a python value cast to its corresponding basic type.
		"""
		if isinstance(value, Basic):
			value = value.value

		if isinstance(value, BaseStruct):
			return value(parent=self)
		if isinstance(value, int):
			return Number(value, parent=self)
		if isinstance(value, str):
			return String(value, parent=self)
		if isinstance(value, bytes):
			return Bin(value, parent=self)
		if isinstance(value, (list, tuple)):
			return List(value, parent=self)
		if isinstance(value, dict):
			return Static(value, parent=self)
		raise self.error(errors.TypeError,
			"valueize failed for python type {type}", type=type(value))
	#enddef


	def key(self, key):
		"""
		SomeStruct.key(key=str) -> subclass of BaseStruct

		Fetch the acceptable type of this key.


		SomeStruct.key(key=BaseStruct) -> subclass of BaseStruct

		If this type class is acceptible for this key, return it.
		Otherwise, raise an error.


		Raises:
		* MethodUnimplemented - System must implement this method.
		* TypeError - Type not allowed for this key.
		"""
		self.error(errors.MethodUnimplemented,
			"struct types must implement key")
	#enddef

	def struct(self, typename):
		"""
		SomeStruct.struct(typename=str) -> subclass of BaseStruct

		Fetch the corresponding class for the given typename that
		is acceptible for use as a substruct.


		SomeStruct.struct(BaseStruct) -> subclass of BaseStruct

		If this type class is allowed as a substruct, return it.
		Otherwise, raise an error.


		Raises:
		* TypeError - Type not allowed here.
		"""
		if self.parent is not None:
			return self.parent.struct(typename)
		else:
			raise self.error(errors.TypeError,
				"substruct type {type} does not exist", type=typename)
		#endif
	#enddef

	def type(self, typename):
		"""
		SomeStruct.type(typename=str) -> subclass of BaseStruct

		Fetch the corresponding class for the given typename that
		is acceptible for use as a value (in a key, list, etc).


		SomeStruct.type(BaseStruct) -> subclass of BaseStruct

		If this type class is allowed as a type, return it.
		Otherwise, raise an error.


		Raises:
		* TypeError - Type not allowed here.
		"""
		if self.parent is not None:
			return self.parent.type(typename)
		else:
			raise self.error(errors.TypeError,
				"type {type} does not exist", type=typename)
		#endif
	#enddef


	def as_type(self, type):
		"""
		SomeStruct.as_type(subclass of BaseStruct) -> {BaseStruct}

		Return a new struct of the given type converted from SomeStruct.

		Raises:
		* NoBasicError - Target struct type does not maintain a basic value.
		* TypeError - This conversion cannot be done.
		"""
		return type(self)
	#enddef

	def can_be(self, type):
		"""
		SomeStruct.can_be(subclass of BaseStruct) -> bool

		Return whether or not SomeStruct can be converted into
		the given type.
		"""
		try:
			self.as_type(type)
		except errors.TypeError:
			return False
		return True
	#enddef

	def as_number(self):
		"""
		SomeStruct.as_number() -> int

		Coerce SomeStruct into a number.

		Raises:
		* ValueError - if it can't be a number
		"""
		try:
			return self.number()
		except errors.TypeError:
			try:
				return int(self.string())
			except ValueError:
				raise self.error(errors.ValueError,
					"coercion from string to number failed: not a valid number")
			except errors.TypeError:
				raise self.error(errors.ValueError,
					"coercion to number failed")
			#endtry
		#endtry
	#enddef

	def as_string(self):
		"""
		SomeStruct.as_string() -> str

		Coerce SomeStruct into a string.

		Raises:
		* ValueError - if it can't be a string
		"""
		try:
			return self.string()
		except errors.TypeError:
			try:
				return str(self.number())
			except errors.TypeError:
				raise self.error(errors.ValueError,
					"coercion to string failed")
			#endtry
		#endtry
	#enddef

	def as_list(self):
		"""
		SomeStruct.as_list() -> list

		Coerce SomeStruct into a list.

		Raises:
		* ValueError - if it can't be a list
		"""
		try:
			return self.list()
		except errors.TypeError:
			raise self.error(errors.ValueError,
				"coercion to list failed")
		#endtry
	#enddef
#endclass
