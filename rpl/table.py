import rpl as RPL

#
# Copyright (C) 2012 Sapphire Becker (http://logicplace.com)
#
# This file is part of Imperial Exchange.
#
# Imperial Exchange is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Imperial Exchange is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Imperial Exchange.  If not, see <http://www.gnu.org/licenses/>.
#

def register(rpl):
	rpl.registerStruct(Table)
#enddef

def printHelp(more_info=[]):
	print(
		"The table library aids in dealing with table or database formats that "
		"use a table head for dynamic typing and such.\n"
		"It offers the structs:\n"
		"  table  head\n"
	)
	if not more_info: print "Use --help table [structs...] for more info"
	infos = {
		"table": Table, "head": TableHead,
	}
	for x in more_info:
		if x in infos: print dedent(infos[x].__doc__)
	#endfor
#enddef

class Table(RPL.Cloneable):
	"""
	Manages dynamic typing and such.
	index:  List of indexes that map to format.
	format: List of references to format struct.
	head {
	    head: Reference to key that contains the typing information.
	          This key is contained in a format or data struct and uses a
	          format struct as its type.
	    type: Name of key in header struct that contains the type ID.
	    name: Optional. Name of key in header struct that contains the column name.
	    index: Optional. Name or ID of column that's used as the unique index.
	}
	"""
	typeName = "table"

	def __init__(self, rpl, name, parent=None):
		RPL.Cloneable.__init__(self, rpl, name, parent)
		self.registerKey("index", "[number|string]+")
		self.registerKey("format", "[string]+")
		self.registerStruct(TableHead)

		self._base = None
		self._head = None
		self._row = []
	#enddef

	def __getitem__(self, key):
		if key == "row": return self._row
		elif key == "head":
			if self._head is None:
				self._head = self.childrenByType(TableHead)
				if len(self._head) == 0: raise RPL.RPLError("table structs must have a head substruct.")
				self._head = self._head[0]
			#endif
			return self._head
		elif key == "base": return self._base
		else: return RPL.Cloneable.__getitem__(self, key)
	#enddef

	def importPrepare(self, folder, filename, data):
		"""
		Called from DataFormat.importPrepare.
		"""
		# This will also ensure head exists
		head = self["head"]

		self._row = []
		for idx, col in enumerate(self.get(head["head"])):
			typeidx = col[self.get(head["type"])]
			try: idxidx = self.get("index").index(typeidx)
			except ValueError:
				raise RPLError("Encountered unknown type %s when processing table." % typeidx)
			#endtry

			tmp = self.get(self.get("format")[idxidx]).split(":", 1)
			if len(tmp) == 1: struct, name = "Format", tmp[0]
			else: struct, name = tuple(tmp)
			# TODO: Verify struct somehow?

			ref = self._rpl.child(name)
			one = ref.countExported() == 1
			clone = ref.clone()
			if one: tmp = [data[idx]]
			else: tmp = data[idx].get()
			clone.importPrepare(folder, filename, tmp)
			self._row.append(clone)
		#endfor
	#enddef

	def exportPrepare(self, rom):
		"""
		Called after the clone is set up for it to grab the data from the ROM.
		"""
		if len(self.get("format")) != len(self.get("index")):
			raise RPLError("format and index must have the same number of values")
		#endif

		# This will also ensure head exists
		head = self["head"]

		# Loop through each column in the head and read in the respective format
		address = self._base.get()
		for x in self.get(head["head"]):
			typeidx = x[self.get(head["type"])]
			try: idx = self.get("index").index(typeidx)
			except ValueError:
				raise RPLError("Encountered unknown type %s when processing table." % typeidx)
			#endtry

			tmp = self.get(self.get("format")[idx]).split(":", 1)
			if len(tmp) == 1: struct, name = "Format", tmp[0]
			else: struct, name = tuple(tmp)
			# TODO: Verify struct somehow?
			clone = self._rpl.child(name).clone()
			clone._base = RPL.Number(address)
			if hasattr(clone, "exportPrepare"): clone.exportPrepare(rom)
			self._row.append(clone)
			address += clone.len()
		#endfor
	#enddef

	def importDataLoop(self, rom):
		for x in self._row: x.importDataLoop(rom)
	#enddef

	def exportDataLoop(self, datafile=None):
		ret = []
		for x in self._row: ret.append(x.exportDataLoop(datafile))
		return RPL.List(ret)
	#enddef

	def calculateOffsets(self):
		calcedOffset = 0
		for x in self._row:
			x._base = RPL.Number(calcedOffset)
			calcedOffset += x.calculateOffsets()
		#endfor
		return calcedOffset
	#enddef

	def countExported(self):
		return len(self._row)
	#enddef

	def basic(self, callers=[]):
		"""
		Returns the name with a prefix, used for referencing this as a type.
		"""
		return RPL.Literal("Table:" + self._name)
	#enddef

	def len(self):
		"""
		Used by DataFormat exportPrepare to determine size of struct in bytes.
		"""
		length = 0
		for x in self._row: length += x.len()
		return length
	#enddef
#endclass

class TableHead(RPL.RPLStruct):
	"""
	Describes the columns of a table. Only used as a substruct of table.
	This basically acts as a map from known key names to the ones in "head".
	head: Reference to the list of table rows. This should be a key in a data
	      or format struct that refers to a format struct.
	name: Key storing column name, optional.
	type: Key storing type index.
	index: Key storing unique index for the row, optional.
	"""
	typeName = "head"

	def __init__(self, rpl, name, parent=None):
		RPL.RPLStruct.__init__(self, rpl, name, parent)
		self.registerKey("head", "reference")
		self.registerKey("name", "string", "")
		self.registerKey("type", "string")
		self.registerKey("index", "number|string", "")
	#enddef
#endclass


# TODO: query struct
