#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

""" lang=en_US
## base ##
When defining the method of the same name, these decorators
handle the various argument structures possible, and the
method the library author must define is the one for the
handling the basic data for this struct type.

Use `@struct.x` for regular types and `@struct.x(struct.STATIC)`
for static struct types.

Versions for specific keys can be defines as `x_key(...)`
where x is a method from the list below and key is the name
of the key it's acting upon.

The argument structures are explained in the docstring. For set
and define, return the value that must be set to the struct
and this will handle it.

* define
* set
* get
* number
* string
* list
* resolve
"""

from ..base.lazystruct import LazyStruct

from ..exceptions import errors

NORMAL = 0
STATIC = 1

# TODO: error localization

def __unlazy(self, value):
	if isinstance(value, LazyStruct):
		return value.create(self)
	return value
#enddef

def define(arg):
	"""
	SomeStruct.define(basic) -> SomeStruct

	Instantiate SomeStruct with this basic value.


	SomeStruct.define(key, value) -> SomeStruct

	Instantiate a key in SomeStruct with this value.


	SomeStruct.define({ key: value, ... }) -> SomeStruct

	Instantiate several keys in SomeStruct with their respective values.
	"""

	def normal(error, self, key, value, source):
		if not isinstance(key, (str, int)):
			raise self.error(errors.ArgumentsTypeError,
				"define expects %s to be str, got%s {got}" % error, got=type(key))
		#endif

		# Is the key already set?
		if key in self.keys:
			# If so, check its source.
			if not self.keys[key].source["type"].is_cache():
				self.error(errors.AssertionError,
					"cannot define key {key} that was already set")
			#endif
		#endif

		try:
			definer = self.definer[key]
		except KeyError:
			try:
				registered_key = self.registrar.key(key)
			except KeyError:
				try:
					self.define_unregistered
				except AttributeError:
					self.error(errors.UndefinedKey,
						"{key} is not registered for this struct type", key=key)
				else:
					new_value = self.define_unregistered(key, value)
					new_value.set_source(source)
				#endtry
			else:
				new_value = registered_key.type(value, source=source)
			#endif
		else:
			new_value = definer(value, source=source)
		#endtry

		if new_value.parent and new_value.parent is not self:
			new_value = new_value()
		#endif
		new_value.parent = self
		self.keys[key] = new_value
	#enddef

	def static(error, self, key, value, source):
		if not isinstance(key, (str, int)):
			raise self.error(errors.ArgumentsTypeError,
				"define expects %s to be str or int, got%s {}" % error, type(key))
		#endif

		new_value = self.keys[key] = self.valueize(value)
		new_value.set_source(source)
	#enddef

	def committer(commit):
		definer = define
		def handler(fun):
			def define(self, *args, source=None):
				largs = len(args)

				if largs == 2:
					key, value = args
					commit(("key", ""), self, key, __unlazy(self, value), source=source)

					return self
				elif largs == 1:
					arg = args[0]
					if isinstance(arg, dict):
						for key, value in arg.items():
							commit(("data's keys", " a"), self, key, __unlazy(self, value), source)
						#endfor
					else:
						fun(self, __unlazy(self, arg))
						self.set_source(source)
					#endif
				else:
					raise self.error(errors.ArgumentsError,
						"define expects some data")
				#endif

				return self
			#enddef
			define.__doc__ = definer.__doc__
			return define
		#enddef
		return handler
	#enddef

	if isinstance(arg, int):
		if arg == NORMAL:
			return committer(normal)
		if arg == STATIC:
			return committer(static)
	if callable(arg):
		return committer(normal)(arg)
	raise errors.ArgumentsError("@{} expects one of: {}",
		define.__qualname__, ("NORMAL", "STATIC"))
#enddef

def set(arg):
	"""
	SomeStruct.setter(basic) -> SomeStruct

	Set SomeStruct to be this basic value.


	SomeStruct.setter(key, value) -> SomeStruct

	Set this value to a key in SomeStruct.


	SomeStruct.setter({ key: value, ... }) -> SomeStruct

	Set these values to their respective several keys in SomeStruct.
	"""

	def normal(error, self, key, value, source):
		if not isinstance(key, (str, int)):
			raise self.error(errors.ArgumentsTypeError,
				"set expects %s to be str, got%s {got}" % error, got=type(key))
		#endif

		try:
			setter = self.setter[key]
		except KeyError:
			try:
				registered_key = self.registrar.key(key)
			except KeyError:
				try:
					self.set_unregistered
				except AttributeError:
					self.error(errors.UndefinedKey,
						"{key} is not registered for this struct type", key=key)
				else:
					new_value = self.set_unregistered(value)
					new_value.set_source(source)
				#endtry
			else:
				new_value = registered_key.type(value, source=source)
			#endif
		else:
			new_value = setter(value, source=source)
		#endtry

		# Is the key already set?
		current_key = self.keys.get(key, None)
		if current_key is not None:
			# If so, check its source.
			if current_key.source["type"].is_cache():
				if new_value.parent and new_value.parent is not self:
					new_value = new_value()
				#endif
				new_value.parent = self
				self.keys[key] = new_value
			else:
				current_key.assertEqual(new_value)
			#endif
		#endif
	#enddef

	def static(error, self, key, value, source):
		if not isinstance(key, (str, int)):
			raise self.error(errors.ArgumentsTypeError,
				"set expects %s to be str or int, got%s {}" % error, type(key))
		#endif

		new_value = self.keys[key] = self.valueize(value)
		new_value.set_source(source)
	#enddef

	def committer(commit):
		setter = set
		def handler(fun):
			def set(self, *args, source=None):
				largs = len(args)

				if largs == 2:
					key, value = args
					commit(("key", ""), self, key, __unlazy(self, value), source=source)

					return self
				elif largs == 1:
					arg = args[0]
					if isinstance(arg, dict):
						for key, value in arg.items():
							commit(("data's keys", " a"), self, key, __unlazy(self, value), source=source)
						#endfor
					else:
						fun(self, __unlazy(self, arg))
						self.set_source(source)
					#endif
				else:
					raise self.error(errors.ArgumentsError,
						"set expects some data")
				#endif

				return self
			#enddef
			set.__doc__ = setter.__doc__
			return set
		#enddef
		return handler
	#enddef

	if isinstance(arg, int):
		if arg == NORMAL:
			return committer(normal)
		if arg == STATIC:
			return committer(static)
	if callable(arg):
		return committer(normal)(arg)
	raise errors.ArgumentsError("@{} expects one of: {}",
		set.__qualname__, ("NORMAL", "STATIC"))
#enddef


def __get(method):
	def upper(arg):
		def normal(struct, key):
			getter = struct.getter.get(key, None)

			if getter:
				ret = getter(self)
			else:
				ret = struct.keys.get(key, None)
			#endif

			if ret is None:
				registered_key = struct.registrar.key(key)

				if struct.bubbling:
					parent = struct.parent
					while parent is not None and key in struct.parent.invisible:
						parent = parent.parent
					#endwhile

					if parent is not None:
						ret = getattr(parent, method)(key)

						if ret.source.number("type") == ret.source.DEFAULTED:
							# If this defaulted, see if this has a default first.
							if registered_key.has_default():
								ret = registered_key.default(struct)
							#endif
						else:
							# TODO: cast as inherited
							pass
						#endif

						struct.keys[key] = ret
						return ret
					#endif
				elif registered_key.has_default():
					ret = registered_key.default(struct)
					struct.keys[key] = ret
					return ret
				#endif

				raise self.error(errors.UndefinedKey,
					"{key} is not set in this struct", key=key)
			else:
				return getattr(ret, method)()
			#endif
		#enddef

		def static(struct, key):
			ret = self.keys.get(key, None)

			if ret is None:
				if self.bubbling:
					parent = self.parent
					while parent is not None and key in self.parent.invisible:
						parent = parent.parent
					#endwhile

					if parent is not None:
						ret = getattr(parent, method)(key)
						# TODO: cast as inherited
						return ret
					#endif
				else:
					raise self.error(errors.UndefinedKey,
						"{key} is not set in this struct", key=key)
				#endif
			else:
				return getattr(ret, method)()
			#endif
		#enddef

		def committer(commit):
			getter = get
			def handler(fun):
				def get(self, key=None):
					if key is None:
						return fun(self)
					if isinstance(key, (list, tuple)):
						target = self
						for x in key[:-1]:
							target = target[x]
						#endfor

						return commit(target, key[-1])
					return commit(self, key)
				#enddef
				return get
			#enddef
			return handler
		#enddef

		if isinstance(arg, int):
			if arg == NORMAL:
				return committer(normal)
			if arg == STATIC:
				return committer(static)
		if callable(arg):
			return committer(normal)(arg)
		raise errors.ArgumentsError("@{} expects one of: {}",
			method, ("NORMAL", "STATIC"))
	#enddef
#enddef
