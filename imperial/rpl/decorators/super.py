#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" lang=en_US
## super ##
Call the superclasses' version of this method, too.

For now, this should only be used for functions that don't
require any arguments.

It calls the superclasses' versions first, right-to-left.

* @struct.super - Call all superclasses' versions.
* @struct.super(...) - Call from only these superclasses.
"""

from ..exceptions import errors

def super(arg):
	def upper(bases):
		def middle(fun):
			def handler(self, *args, **kwargs):
				for x in reversed(bases or self.__class__.__bases__):
					if x is object: continue

					try:
						method = getattr(x, fun.__name__)
					except AttributeError:
						self.error(errors.LibraryError,
							"superclass method {} does not exist", fun.__name__)
					else:
						method(self)
					#endtry
				#endfor

				return fun(self, *args, **kwargs)
			#enddef
			return handler
		#enddef
		return middle
	#enddef


	if isinstance(arg, (list, tuple)):
		return upper(arg)
	if callable(arg):
		return upper(None)(arg)
	raise errors.ArgumentsError("@{} expects a list of classes",
		super.__qualname__)
#enddef
