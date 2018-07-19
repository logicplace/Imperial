#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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

from ..makers import make_define_maker, make_set_maker, make_get, make_resolve

from ..exceptions import errors

__all__ = ["make_define", "make_set", "make_get", "make_resolve"]

def commit_define(self, defined):
	for key, value in defined.items():
		if isinstance(key, int):
			self.add_child(value)
		else:
			self.rigid[key] = self.valueize(value)
		#endif
	#endfor
#enddef

make_define = make_define_maker(commit_define)


def commit_set(error, self, key, value, source):
	if not isinstance(key, (str, int)):
		raise self.error(errors.ArgumentsTypeError,
			"set expects %s to be str or int, got%s {}" % error, type(key))
	#endif

	new_value = self.sourced[key] = self.valueize(value)
	new_value.set_source(source)
#enddef

make_set = make_set_maker(commit_set)
