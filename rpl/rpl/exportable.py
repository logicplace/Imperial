#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# MIT Licensed

"""
# exportable #
## Exportable ##
Subclass this for a struct which represents sourced data.

This adds the ability to export the abstract representation
of the data this contains.

### keys ###
* name - Abstract name (and hierarchy) of this struct.
* tags - List of categories/tags this struct belongs to.
* exports - Specialized struct describing additional export info.
* source - Source information now accessible through key.
"""

from .dynamic import BaseDynamic
from .specialized import Specialized

from .exceptions import errors
from .registrar import Registrar, Key
from . import decorators as struct

__all__ = ["Exportable"]

class Exportable(BaseDynamic):
	@struct.super
	def postinit(self):
		if self.name and "name" not in self.keys:
			self.set("name", self.name, source = { "type": "implied" })
		#endif
	#enddef

	def __call__(self, data=None, *, name=None, **kwargs):
		if name is not None and (not isinstance(data, dict) or "name" not in data):
			source = self["name"].source
			if source.number("type") == source.IMPLIED:
				# If this was implied and we're changing the name, we should change this too.
				self.set("name", name, source = { "type": "implied" })
			#endif
		#endif

		return BaseDynamic.__call__(self, data, name=name, **kwargs)
	#enddef

	@struct.key
	def name(self):
		name = self["name"]
		if name.get("open"):
			return name
		elif isinstance(self.parent, Exportable):
			parent_name = self.parent.list("path")
		elif self.parent is not None and self.parent.name:
			parent_name = [self.parent.name]
		else:
			parent_name = []
		#endif

		return type(name)({
			"path": parent_name + name.list("path"),
		}, source=name.source())
	#enddef

	@struct.key
	def source(self):
		return self.source
	#enddef

	@source.setter_definer
	def source(self, value):
		self.set_source(value)
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
		return BaseDynamic.get_registrar(keys = [
			Key("name", Path),
			Key("tags", {
				"": List,
				"type": "string",
			}),
			Key("exports", Exports),
		])
	#enddef

	def export_data(self, *, keys=None, children=None):
		"""
		SomeStruct.export_data()

		Export data from all keys and children of SomeStruct.


		SomeStruct.export_data(keys=[...], children=[...])

		Export data from only the given keys and/or children.
		In this case, the missing names are going to be exported
		by other structs, necessarily. If this *must* export
		data that isn't in keys or children, it must generate a
		warning indicating which data was duplicated using:
		warnings.ExportedDuplicateData
		"""
		self.error(errors.MethodUnimplemented,
			"Exportable types must implement export_data")
	#enddef

	def import_data(self, *, keys=None, children=None):
		"""
		SomeStruct.import_data()

		Import data related to all keys and children of SomeStruct.


		SomeStruct.import_data(keys=[...], children=[...])

		Import data from only the given keys and/or children.
		In this case, the missing names were not requested. If
		something must be imported in order to properly structure
		requested data, it should generate a low-priority warning
		indicating what extra pieces were imported using:
		warnings.ImportedExtraData
		"""
		self.error(errors.MethodUnimplemented,
			"Exportable types must implement import_data")
	#enddef
#endclass

class Exports(Specialized):
	typename = "exports"
#endclass
