#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
## metaclass ##
### BaseMetaclass ###
Not to be used besides in StructMetaclass and DynamicMetaclass.

Handles @struct.key definitions.

Handles nocopy.

### StructMetaclass ###
Not to be used besides in BaseStruct.

Abstracts input forms for .get and .set so that the method
which the subclass defines is the one that retrieves the
basic data for the struct only. These are static-like forms.
"""

from .makers import make_define, make_set, make_get, make_resolve

__all__ = ["BaseMetaclass", "StructMetaclass"]

class BaseMetaclass(type):
	def __new__(cls, clsname, superclasses, attributedict):
		getters = attributedict["getter"] = {}
		setters = attributedict["setter"] = {}

		# Assumes values of ..decorators.key.GETTER etc.
		xers = (getters, setters)

		# Only include requested ones, if any were.
		valid = attributedict.pop("superclass_xers", None)

		# Handle nocopy.
		nocopy = attributedict.setdefault("nocopy", [])

		# Grab from superclasses.
		for x in reversed(superclasses):
			if issubclass(type(x), BaseMetaclass):
				if valid:
					for key in valid:
						try:
							getters[key] = x.getter[key]
						except KeyError: pass
						try:
							setters[key] = x.setter[key]
						except KeyError: pass
					#endfor
				else:
					getters.update(x.getter)
					setters.update(x.setter)
				#endif

				nocopy.extend(x.nocopy)
			#endif
		#endfor

		for name, method in attributedict.items():
			if not callable(method): continue

			try:
				method.xer_type
			except AttributeError:
				continue
			else:
				xer = xers[method.xer_type]
				xer[method.name] = method
				delattr(cls, method)
			#endtry
		#endfor

		return type.__new__(cls, clsname, superclasses, attributedict)
	#enddef
#enddef

def ifdef(attributedict):
	def doer(key, method, *args):
		if key in attributedict:
			attributedict[key] = method(attributedict[key], *args)
		#endif
	#enddef
	return doer
#enddef

class StructMetaclass(BaseMetaclass):
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
