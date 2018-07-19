#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
## LazyStruct ##
## unlazy ##
Instantiate any lazy structs. No-op if not lazy.
"""

from ..exceptions import errors

__all__ = ["LazyStruct", "unlazy"]

class LazyStruct:
	def __init__(self, type, data, **kwargs):
		"""
		LazyStruct(type, data, **kwargs) -> {LazyStruct}

		Create a struct later.

		* type: If this is a subclass of BaseStruct it will be used directly.
		        If this is a string, it will ask its future parent what class to use.
		* data: Data to use for instantiation.
		* kwargs: Other keyword arguments to pass to the constructor. 
		"""
		if not (issubclass(type, BaseStruct) or isinstance(type, str)):
			raise errors.ArgumentsTypeError(
				"LazyStruct expects BaseStruct or str for type")
		#endif

		self.type = type
		self.data = data
		self.kwargs = kwargs
	#enddef

	def create(self, parent, key=None):
		"""
		{LazyStruct}.create({BaseStruct}) -> {self.type according to parent}

		Create a substruct to be added to the parent.

		{LazyStruct}.create({BaseStruct}, key) -> {self.type according to parent}

		Create a keystruct to be added to the parent.
		"""
		type = self.type

		if key is None:
			type = parent.struct(type)
		else:
			try:
				key = parent.key(key)
			except errors.MethodUnimplemented:
				key = None
			#endtry

			if key is not None and key.typename == type:
				type = key
			else:
				type = parent.type(type)
			#endif
		#endif

		return type(self.data, **self.kwargs, parent=self.parent)
	#enddef
#endclass

def unlazy(self, value):
	"""
	unlazy({LazyStruct}) -> {BaseStruct}

	Instantiate a LazyStruct


	unlazy(SomeStruct) -> SomeStruct

	Return already instantiated structs as-is.
	"""
	if isinstance(value, LazyStruct):
		return value.create(self)
	return value
#enddef
