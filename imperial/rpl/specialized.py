#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
# specialized #
## Specialized ##
Subclass this for a struct which represents a key such that:

* This key represents data which would be difficult to store
  in a single basic type, but doesn't represent data which is
  exportable on its own.
* This type is only used once in the struct.
* This type is irrelevant to any other positions it could
  appear in. That is, it has no particular use being used as
  a general-purpose type.

When one of these structs is used, it can be declared in the
following ways with the following differences:

* As a nameless substruct - `special { ... }`
** Not referential as a child.
** Still accesible through @this.special
** Not visible to bubbling substructs.
* As a named substruct - `special SpecialBoi { ... }`
** Able to be referenced with:
*** @SpecialBoi (if non-conflicting)
*** @this{SpecialBoi}
** Still accesible through @this.special
** Not visible to bubbling substructs.
* As a keystruct - `special: special { ... }`
** Not referential as a child.
** Does not exist as a child.
** Accesible through @this.special
** Is visible to bubbling substructs.
"""

from .dynamic import BaseDynamic

from .exceptions import errors
from . import decorators as struct

__all__ = ["Specialized"]

class Specialized(BaseDynamic):
	# TODO ...
	pass
#endclass
