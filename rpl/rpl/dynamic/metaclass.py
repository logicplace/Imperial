#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
## metaclass ##
### BaseMetaclass ###
### DynamicMetaclass ###
Not to be used besides in BaseDynamic.

Abstracts input forms for .get and .set so that the method
which the subclass defines is the one that retrieves the
basic data for the struct only. These are dynamic-like forms.
"""

from ..base.metaclass import BaseMetaclass, ifdef

from .makers import make_define, make_set, make_get, make_resolve

__all__ = ["DynamicMetaclass"]

class DynamicMetaclass(BaseMetaclass):
	def __new__(cls, clsname, superclasses, attributedict):
		wrap = ifdef(attributedict)

		wrap("define", make_define)
		wrap("set", make_set)
		wrap("get", make_get)
		wrap("number", make_get, "number")
		wrap("string", make_get, "string")
		wrap("list", make_get, "list")
		wrap("resolve", make_resolve)

		return BaseMetaclass.__new__(cls, clsname, superclasses, attributedict)
	#enddef
#endclass
