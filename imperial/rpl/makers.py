#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
## makers ##
Meant to be used by base.makers and dynamic.makers

### Basic ###
A class to obscure the use of python or RPL types.

### make_define_maker ###
Creates a make_define function.

### make_set_maker ###
Creates a make_set function.

### make_get ###
A standard make_get function.

The variable work is lifted by __getitem__

### make_resolve_maker ###
Creates a make_resolve function.
"""

import time

from .numbers import BaseNumber, Number
from .strings import BaseString, String
from .lists import BaseList, List

from .helper import OrderedMixed
from .exceptions import errors

from .base.lazystruct import unlazy

__all__ = ["Basic", "make_define_maker", "make_set_maker", "make_get", "make_resolve"]

class Basic:
	def __new__(cls, value):
		if isinstance(value, Basic):
			return value
		return object.__new__(cls, value)
	#enddef

	def __init__(self, value):
		self.value = value
	#enddef

	@property
	def value(self):
		return self._value
	#enddef

	@value.setter
	def value(self, value):
		self._value = value

		self.is_basic = True
		self.is_number = isinstance(value, (int, BaseNumber))
		self.is_string = isinstance(value, (str, BaseString))
		self.is_list = isinstance(value, (list, tuple, BaseList))

		from .base import BaseStruct

		if isinstance(value, BaseStruct):
			self.is_bare = value._basic_instantiation and value.source is None
			self.is_python = False
			self.can_be_number = self.is_number or isinstance(value, BaseStruct) and value.can_be(Number)
			self.can_be_string = self.is_string or isinstance(value, BaseStruct) and value.can_be(String)
			self.can_be_list = self.is_list or isinstance(value, BaseStruct) and value.can_be(List)
			self.is_reference = isinstance(value, BaseReference)
		else:
			self.is_bare = self.is_python = True
			self.can_be_number = self.is_number
			self.can_be_string = self.is_string
			self.can_be_list = self.is_list
			self.is_reference = False
		#endif
	#enddef
#endclass

def make_define_maker(commit):
	"""
	make_define_maker(commit) -> make_define(method)

	* commit - commit_define(self, defined)
		- Add keys and substructs from defined to self.
		  Keys' values may be python types.
		- defined - Can be:
			+ Basic - A syntactic or basic instantiation.
			+ OrderedMixed of substructs and Basics.
	* method - define(self, value)
		- This is the define method in a BaseStruct subclass.
	"""
	def make_define(method):
		def define(self, value, source=None):
			if self.clones:
				raise self.error(errors.DefineClonedError,
					"cannot redefine a struct which has been cloned")
			#endif

			# Clear data.
			self.source = None
			self.invalidate()
			self.reflects = []
			self.rigid.clear()
			self.sourced.clear()
			self.child.clear()

			if isinstance(value, dict):
				if not isinstance(value, OrderedMixed):
					# OrderedMixed allows for keys and children to be intermingled.
					# This preserves the order of specialized type keys when used correctly.
					# This right here does not, but we want a normalized type sent to method. 
					value = OrderedMixed(value)
				#endif
				value.is_basic = False
				self._basic_instantiation = False

				for k, v in value.items():
					if not isinstance(k, int):
						value[k] = Basic(v)
					#endif
				#endfor
			else:
				# Obscure python types and simplify type checking.
				value = Basic(value)
				self._basic_instantiation = True
			#endif

			defined = method(value)
			self.set_source(source)

			commit(self, defined)

			self.change()

			return self
		#enddef
		return define
	#enddef
	return make_define
#enddef

def make_set_maker(commit):
	"""
	make_set_maker(commit) -> make_set(method)

	* commit - commit_set(error, self, key, value, source)
		- Add a single key and value to self.
		- error - For error reporting. Can be:
			+ ("key", "") - When setting a single key.
			+ ("data's keys", " a") - When setting a key from a dict.
		- key - May be any python type, must error if it's invalid for
		        this struct's needs. Use ArgumentsTypeError
		- value - A Basic
		- source - Source of value, especially if it's a python type.
	* method - set(self, value)
		- This is the set method in a BaseStruct subclass.
	"""
	def make_set(method):
		def set(self, *args, source=None):
			largs = len(args)

			if largs == 2:
				key, value = args
				commit(("key", ""), self, key, Basic(unlazy(self, value)), source=source)

				return self
			elif largs == 1:
				arg = args[0]
				if isinstance(arg, dict):
					for key, value in arg.items():
						commit(("data's keys", " a"), self, key, Basic(unlazy(self, value)), source=source)
					#endfor
				else:
					method(self, Basic(unlazy(self, arg)))
					self.set_source(source)
					self.change()
				#endif
			else:
				raise self.error(errors.ArgumentsError,
					"set expects some data")
			#endif

			return self
		#enddef
		return set
	#enddef
	return make_set
#enddef

def make_get(method, type_method="get"):
	def get(self, key=None):
		if key is None:
			# Get basic value.
			cached = self.cached
			value, when = cached[type_method]

			if when:
				changed = False
				for ref in self.reflects:
					ref = ref.resolve()
					if ref.changed > when:
						changed = True
						self.invalidate()
						break
					#endif
				#endfor
			else:
				changed = True
			#endif

			if changed:
				value = cached[type_method] = (method(self), time.time())
			#endif

			return value
		#endif

		# Get value of key.
		return getattr(self[key], type_method)()
	#enddef
	return get
#enddef

def make_resolve(method):
	def resolve(self, key=None):
		if key is None:
			return method(self)
		#endif

		return self[key].resolve()
	#enddef
	return resolve
#enddef
