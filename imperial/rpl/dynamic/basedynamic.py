#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
# dynamic #
## BaseDynamic ##
Subclass this for new dynamic types (non-static).

This is mainly only useful for built-in types and bases.

Functionally, this adds a registrar to BaseStruct for
registering keys, types, and substructs.
"""

from ..base import BaseStruct
from ..statics import BaseStatic

from ..exceptions import errors

from .metaclass import DynamicMetaclass

__all__ = ["BaseDynamic"]

class BaseDynamic(BaseStruct, metaclass=DynamicMetaclass):
	registrar = None

	@struct.super
	def init(self):
		if self.registrar is None:
			self.__class__.registrar = self.registrar = self.register()
		#endif
	#enddef


	def __getitem__(self, key):
		if not isinstance(key (list, tuple)):
			getter = self.getter.get(key, None)

			if getter:
				return getter(self)
			#endif
		#endif

		try:
			return BaseStruct.__getitem__(self, key)
		except errors.UndefinedKey:
			try:
				registered_key = self.registrar.key(key)
			except KeyError:
				self.error(errors.UndefinedKey,
					"{key} is not registered for this struct type", key=key)
			#endtry

			if registered_key.has_default():
				ret = registered_key.default(self)
				self.sourced[key] = ret
				return ret
			elif self.bubbling:
				# Inheritance has already been checked, so we want to bypass
				# that by not just doing self.parent[key] and checking only
				# the registries of dynamic parents.
				parent = self.parent

				while parent is not None:
					if isinstance(parent, BaseDynamic) and key not in parent.invisible:
						try:
							parent_registered_key = parent.registrar.key(key)
						except KeyError:
							pass
						else:
							if parent_registered_key.has_default():
								ret = parent_registered_key.default(self)
								ret = registered_key.type(ret, source = { "type": "inherited" })
								self.sourced[key] = ret
								return ret
							#endif
						#endtry
						parent = parent.parent
					#endif
				#endwhile
			#endif

			raise self.error(errors.KeyRequired,
				"{key} is required in this struct", key=key)
		#endtry
	#enddef


	def register(self):
		"""
		Register keys, substructs, and types under this type.

		To retrieve a superclass's registrar, and its keys etc,
		use super_registrar = SuperClass.get_registrar()

		To use all the keys, substructs, and types of a single
		superclass, use super_registrar(...)

		To only use certain keys etc of the superclass, use
		 Registrar(keys = super_registrar.keys(...) + [...])

		Please do not override any basic types!

		This must return a Registrar.
		"""
		return Registrar(types = [
			Number, Hexnum,
			String, Literal, RefString, MultiString,
			List, Range, RangeRepeat, RangeInc, RangeDec,
			Math, Bool, Size, Path,
		])
	#enddef

	@classmethod
	def get_registrar(cls, **kwargs):
		"""
		Ensure the registrar has been created.


		Dynamic.get_registrar() -> Registrar

		Return the registrar, unchanged.


		Dynamic.get_registrar(keys = ..., ...) -> Registrar

		Return a copy of the registrar with new keys, structs,
		or types. Same as Dynamic.get_registrar()(...)
		"""
		if cls.registrar is None:
			registrar = cls({}).registrar
		else:
			registrar = cls.registrar
		#endif

		if kwargs:
			return registrar(**kwargs)
		else:
			return registrar
		#endif
	#enddef

	def key(self, key):
		try:
			return self.registrar.key(key).type
		except KeyError:
			raise self.error(errors.UndefinedKey,
				"key {key} is not registered", key=key)
		#endtry
	#enddef

	def struct(self, typename):
		try:
			if issubclass(typename, BaseStruct):
				if not self.registrar.has_struct(typename):
					raise KeyError
				#endif
				return typename
			#endif

			return self.registrar.struct(typename)
		except KeyError:
			type = BaseStruct.struct(self, typename)
			if not isinstance(type, BaseStatic):
				raise self.error(errors.TypeError,
					"{type} not an allowed substruct", type=type.typename_for_error)
			#endif
			return type
		#endtry
	#enddef

	def type(self, typename):
		try:
			return self.registrar.type(typename)
		except KeyError:
			return BaseStruct.type(self, typename)
		#endtry
	#enddef
#endclass
