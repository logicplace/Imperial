#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
## makers ##
### make_define ###
Used by the metaclass to create the *define* method.

See basestruct.BaseStruct.define for documentation.

### make_set ###
Used by the metaclass to create the *set* method.

See basestruct.BaseStruct.set for documentation.

### make_get ###
Used by the metaclass to create the *get* method.

See basestruct.BaseStruct.get for documentation.

### make_resolve ###
Used by the metaclass to create the *resolve* method.

See basestruct.BaseStruct.resolve for documentation.
"""

from ..exceptions import errors

from ..makers import make_define_maker, make_set_maker, make_get, make_resolve

from ..exceptions import errors

__all__ = ["make_define", "make_set", "make_get", "make_resolve"]

def commit_define(self, defined):
	for key, value in defined.items():
		if isinstance(key, int):
			self.add_child(value)
		else:
			try:
				registered_key = self.registrar.key(key)
			except KeyError:
				self.error(errors.UndefinedKey,
					"{key} is not registered for this struct type", key=key)
			#endtry

			new_value = registered_key.type(value, source=source)
			self.rigid[key] = new_value(parent=self)
		#endif
	#endfor
#enddef

make_define = make_define_maker(commit_define)


def commit_set(error, self, key, value, source):
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
				new_value = self.set_unregistered(key, value)
				new_value.set_source(source)
			#endtry
		else:
			new_value = registered_key.type(value, source=source)
		#endtry
	else:
		new_value = setter(value, source=source)
	#endtry

	# Is the key already set?
	current_key = self.rigid.get(key, None)
	if current_key is not None:
		current_key.assertEqual(new_value)
	else:
		self.sourced[key] = new_value(parent = self)
	#endif
#enddef

make_set = make_set_maker(commit_set)
