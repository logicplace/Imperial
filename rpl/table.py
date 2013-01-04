import rpl, helper

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

def printHelp(moreInfo=[]):
	helper.genericHelp(globals(), moreInfo,
		"The table library aids in dealing with table or database formats that "
		"use a table head for dynamic typing and such.", "table", {
			# Structs
			"table": Table,
		}
	)
#enddef

class Table(rpl.Serializable):
	"""
	Manages dynamic typing and such.

	{/isnip}{cimp rpl.Serializable}
	index:  List of indexes that map to format.
	format: List of references to format struct.
	head:   Reference to key that contains the typing information.
	        This key is contained in a format or data struct and uses a
	        format struct as its type.
	type:   Name of key in header struct that contains the type ID.
	name:   Optional. Name of key in header struct that contains the column name.
	unique: Optional. Name or ID of column that's used as the unique index.
	"""
	typeName = "table"

	def __init__(self, top, name, parent=None):
		rpl.Serializable.__init__(self, top, name, parent)
		self.registerKey("index", "[number|string]+")
		self.registerKey("format", "[reference]+")
		self.registerKey("head", "reference")
		self.registerKey("name", "string", "")
		self.registerKey("type", "string")
		self.registerKey("unique", "number|string", "")

		self.row = []
	#enddef

	def __setitem__(self, key, value):
		if key == "format":
			for x in value.list():
				# Try to manage this
				try: x.pointer().unmanaged = False
				# Does not exist yet... will need to be set in preparation.
				except RPL.RPLError: pass
			#endfor
		#endif
		rpl.Serializable.__setitem__(self, key, value)
	#enddef

	def __getitem__(self, key):
		if key == "row": return self.row
		else: return rpl.Serializable.__getitem__(self, key)
	#enddef

	def importPrepare(self, rom, folder, filename=None, data=None, callers=[]):
		"""
		Called from DataFormat.importPrepare.
		"""

		self.row = []
		data = data.get()
		for idx, col in enumerate(self.get(self["head"])):
			typeidx = col[self.get(self["type"])]
			try: idxidx = self.get("index").index(typeidx)
			except ValueError:
				raise RPLError("Encountered unknown type %s when processing table." % typeidx)
			#endtry

			ref = self.get("format")[idxidx].pointer()
			ref.unmanaged = False
			clone = ref.clone()
			try: clone.importPrepare(rom, folder, filename, data[idx], callers + [self])
			except TypeError: clone.importPrepare(rom, folder)
			self.row.append(clone)
		#endfor
	#enddef

	def exportPrepare(self, rom, folder, callers=[]):
		"""
		Called after the clone is set up for it to grab the data from the ROM.
		"""
		if len(self.get("format")) != len(self.get("index")):
			raise RPLError("format and index must have the same number of values")
		#endif

		# Loop through each column in the head and read in the respective format
		address = self["base"].number()
		for x in self.get(self["head"]):
			typeidx = x[self.get(self["type"])]
			try: idx = self.get("index").index(typeidx)
			except ValueError:
				raise RPLError("Encountered unknown type %s when processing table." % typeidx)
			#endtry

			ref = self.get("format")[idx].pointer()
			ref.unmanaged = False
			clone = ref.clone()
			try: clone["base"] = rpl.Number(address)
			except rpl.RPLError: clone.base = rpl.Number(address)
			try: clone.exportPrepare
			except AttributeError: pass
			else:
				try: clone.exportPrepare(rom, folder, callers + [self])
				except TypeError: clone.exportPrepare(rom, folder)
			self.row.append(clone)
			address += clone.len()
		#endfor
	#enddef

	def importDataLoop(self, rom, folder, base=None, callers=[]):
		for x in self.row: x.importDataLoop(rom, folder, rom.tell(), callers + [self])
	#enddef

	def exportDataLoop(self, rom, folder, datafile=None, callers=[]):
		ret = []
		for x in self.row: ret.append(x.exportDataLoop(rom, folder, datafile))
		return rpl.List(ret)
	#enddef

	def calculateOffsets(self):
		calcedOffset = 0
		for x in self.row:
			x.base = rpl.Number(calcedOffset)
			calcedOffset += x.calculateOffsets()
		#endfor
		return calcedOffset
	#enddef

#	def countExported(self):
#		return len(self.row)
#	#enddef

#	def basic(self, callers=[]):
#		"""
#		Returns the name with a prefix, used for referencing this as a type.
#		"""
#		return rpl.Literal("Table:" + self.name)
#	#enddef

	def len(self):
		"""
		Used by DataFormat exportPrepare to determine size of struct in bytes.
		"""
		length = 0
		for x in self.row: length += x.len()
		return length
	#enddef
#endclass


# TODO: query struct
