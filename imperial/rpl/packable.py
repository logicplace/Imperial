#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
# packable #
## Packable ##
Subclass this for a struct which can packed into a representative
format, typically, one that is specific to this struct type.

Every packable type has a key called base which represents the
means of identifying this data within the current context.

Each packable subclass has a corresponding container class which
uses its specialized functions for packing and unpacking.

```rpl
container {
	packable {
		base: ...
		# descriptors
	}
}```

container represents some raw stream of data which doesn't necessarily
have properly marked beginnings and ends. Even if sections are marked,
they may not be the boundaries of a whole piece of data.

When packing, the system works like this: The root tells container it
needs to pack itself. To do this, it may work some general purpose
magic at the container-level, but it will generally also tell its
substructs to pack themselves. The container maintains a sandboxed
packing which its substructs contribute to (that is, they do not have
direct access to root's). The packable uses the base to determine
where in the packing to place its data by indirectly asking container
to adjust for the base before it begins writing. If it makes more
sense to the context, it is also possible for it to simply return the
packed data and base(s) and let the container handle basing. Once the
substructs are packed and the container is done with any general
packing, the container then inserts its sandbox into the root by
performing a similar basing request.

When unpacking, the system works similarly but in reverse. The root asks
the container to unpack, then the container asks the root for its
reference to its data by its base. It does whatever general things it
must do, then it tells its substructs to unpack, which request basings
in the same manner. The complexity here is that there is a possibility
that the container will be unable to create a proper sandbox of the data
before the substructs are unpacked. In such a case, the container at
least knows the beginning of the context, and must ensure the substructs
do not access anything above that. Everything a substruct touches then
becomes part of the context.

Contexts *should* have some manner of allowing substructs to be defined
without bases and allow for some logical ordering. That is, the first
substruct would have the logical position of the "first" position, etc.
If this is possible, the packable should define a key, **end**, which
the base of the subsequent struct implicitely refers to when undefined.

Packables may define multiple bases (but only one end). Because of this,
the packable must be what manages knowledge of the base key.

### attributes ###
* address - Reference to the specific Address subclass this type uses.
* bases - A list of keynames which hold bases. If undefined, assumes
          ["base"]. While these should be "base1" etc, they may be
          something else, especially if the library's underlying
          language isn't English.

### keys ###
* base - Beginning of this data within the containing context.
"""

from .exportable import Exportable, StructMetaclass

from .exceptions import errors
from .registrar import Key
from . import decorators as struct

__all__ = ["Packable"]

class PackableMetaclass(StructMetaclass):
	def __new__(cls, clsname, superclasses, attributedict):
		bases = attributedict.get("bases", None)
		new_cls = StructMetaclass.__new__(cls, clsname, superclasses, attributedict)

		getters = new_cls.getter
		for x in (bases or ["base"]):
			getters[x] = create_base_getter(x)
		#endfor

		return new_cls
	#enddef
#endclass

def create_base_getter(key):
	def base(self):
		parent = self.parent
		while parent is not None:
			if isinstance(parent, BaseContext):
				break
			#endif
			parent = parent.parent
		#endwhile

		if parent is None:
			raise self.error(errors.PackingError,
				"cannot use base key when struct is not in a context")
		#endif

		if not isinstance(self, parent.packable):
			raise self.error(errors.PackingError,
				"struct cannot access base as it is not in a compatible context")
		#endif

		return self.base(key, context=parent)
	#enddef
	return base
#enddef

class Packable(Exportable, metaclass=PackableMetaclass):
	def get_address(self, context):
		# First attempt to use address as defined by the class.
		# (Note that the only time it will be a dict is in such a case.)
		# Then use the direct subclass of Packable's version.
		if not isinstance(context, type):
			context = context.__class__
		#endif

		address = self.address
		if isinstance(address, dict):
			return address[context.packable]
		else:
			try:
				return self.__class__.address
			except AttributeError:
				return context.packable.address
			#endtry
		#endif
	#enddef

	def base(self, key, context):
		"""
		SomePackable.base(key=str, context={BaseContext}) -> {Address}

		Return the base value in the proper address type for
		the given base key (often "base"). This is called by
		the getter and generally shouldn't be called by other
		things.

		The correct address subclass should be decided on by
		the type of context. Of course, if the packable subclass
		does not subclass a packable accepted by a certain
		context, there is no need to condition on that context.
		"""
		return self.get_address(context)(self[key])
	#enddef
#endclass

class Address(Value):
	typename = "address"
#enddef
