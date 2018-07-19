#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
## BaseStatic ##
Subclass this for new statics.
"""

from ..base import BaseStruct
from ..exceptions import errors

__all__ = ["BaseStatic"]

class AnyKey(BaseStruct):
	def __new__(cls, data, **kwargs):
		if kwargs:
			return data(**kwargs)
		else:
			return data
		#endif
	#enddef
#endclass

class BaseStatic(BaseStruct):
	def key(self, key):
		if isinstance(key, str):
			return AnyKey
		elif isinstance(key, BaseStruct):
			if self.parent is None:
				return key
			else:
				return self.parent.type(key)
			#endif
		#endif
	#enddef
#endclass
