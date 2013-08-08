#-*- coding:utf-8 -*-
#
# Copyright (C) 2012-2013 Sapphire Becker (http://logicplace.com)
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

from .. import rpl, helper
from ..rpl import RPLError, RPLBadType

def register(rpl):
	rpl.registerStruct(Map)
#enddef

class Map(rpl.RPLStruct):
	"""
	Translates data. When exporting, it will look for the value in packed and
	output the corresponding value in unpacked. When importing, it does the
	reverse. un/packed keys may either both be lists or both be strings.
	String form is good for translating text between a ROM's custom encoding
	and ASCII or UTF8. Lists can translate numbers or strings. The benefit here
	being that it can translate strings longer than one character. However do
	remember that strings in RPL are UTF8 as it is. But if the custom encoding
	is multibyte, this will help.
	<packed>
	packed:   What the value should look like when packed.</packed>
	<unpacked>
	unpacked: What the value should look like when unpacked.</unpacked>
	<unmapped>
	unmapped: Method to handle data not represented in un/packed. May be:
	          except: Throw an exception.
	          add:    Write it as is.
	          drop:   Ignore it.</unmapped>
	<cast>
	cast:     Type to cast unpacked values to, if more specific than the
	          interpreted type.</cast>
	<string>
	string:   Type to cast unpacked strings to specifically, if strings and
	          numbers are both present.</string>
	<number>
	number:   Type to cast unpacked numbers to specifically, if strings and
	          numbers are both present.</number>
	<width>
	width:    Byte width for packed values. The default is some kind of voodoo.
	          If set to "dynamic" it will allow dynmically sized strings through.
	          If set to "all" then the entire data is used for the mapping.
	          If set to a number, then the data is split at the given interval.</width>
	"""
	typeName = "map"
	sizeFieldType = "len"

	def __init__(self, top, name, parent=None):
		rpl.RPLStruct.__init__(self, top, name, parent)
		self.base, self.size, self.myData = None, None, None
	#enddef

	def register(self):
		self.registerKey("packed", "string|[number|string]+")
		self.registerKey("unpacked", "string|[number|string]+")
		self.registerKey("unmapped", "string:(except, add, addstr, addstring, addnum, addnumber, drop)", "except")
		self.registerKey("cast", "string", "")
		self.registerKey("string", "string", "")
		self.registerKey("number", "string", "")
		self.registerKey("width", "number|string:(dynamic,all)", "")
	#enddef

	def serializePacked(self, options):
		packed = []
		for x in self["packed"].get():
			try: x.serialize
			except AttributeError: packed.append(rpl.String(x).serialize(**options))
			else: packed.append(x.serialize(**options))
		#endfor
		return packed
	#enddef

	def prepare(self, callers):
		# Retrieve mappings and set mode.
		try: packed, unpacked, mode, utype = self["packed"].list(), self["unpacked"].list(), 0, 0
		except rpl.RPLBadType:
			try: unpacked, mode, utype = self["unpacked"].list(), 1, 0
			except rpl.RPLBadType: unpacked, mode, utype = self["unpacked"].string(), 1, 1
		#endtry

		# Determine width.
		width = self["width"].get()
		if width == "": width = "dynamic" if mode else "all"

		# Create un/serialization options.
		options, remaining = {}, ["padside", "padchar", "endian", "sign"]
		for c in callers[::-1]:
			for o in remaining[:]:
				try:
					options[o] = c.get(o)
					remaining.remove(o)
				except RPLError: pass
			#endfor
			if not remaining: break
		#endfor
		if width == "all": options["size"] = self.size.number()
		elif width != "dynamic": options["size"] = width

		# Serialize packed values.
		packed = self.serializePacked(options)

		# If it's dynamic but all are the same size, just force a known width.
		# TODO: Should this only be when defaulting?
		if width == "dynamic":
			tmp = map(len, packed)
			if tmp.count(tmp[0]) == len(packed): width = tmp[0]
		#endif

		# Ensure lengths of packed and unpacked are the same.
		if len(packed) != len(unpacked):
			raise RPLError(
				"Packed (len: %i) and unpacked (len: %i) must be the same length."
				% (len(packed), len(unpacked))
			)
		#endif

		# Available basic types.
		if utype: types = ["string"]
		else:
			types = []
			for x in unpacked:
				try:
					x.number()
					if "number" not in types: types.append("number")
				except RPLBadType:
					if "string" not in types: types.append("string")
				#endtry
				if len(types) == 2: break
			#endfor
		#endif

		# Back these up for speed.
		return (
			options, packed, unpacked, mode, self["cast"].string(),
			self["string"].string(), self["number"].string(), width, types
		)
	#enddef

	def importPrepare(self, rom, folder, filename=None, data=None, callers=[]):
		# This can only be used as a data's type.
		if data is not None: self.myData = data
	#enddef

	def exportPrepare(self, rom, folder, callers=[]):
		# This can only be used as a data's type.
		if not callers: return

		options, packed, unpacked, mode, cast, string, number, width, types = self.prepare(callers)

		# Read data from ROM.
		self.rpl.rom.seek(self.base.number())
		bindata = self.rpl.rom.read(self.size.number())

		def tmpfunc(data, expand):
			# Loop through packed and attempt unserialize to the respective type.
			for i, p in enumerate(packed):
				if expand:
					if len(p) > len(data): continue
					d = data[:len(p)]
				else: d = data
				if p == d:
					# Match found!
					u = unpacked[i]
					try: d, t = u.number(), 0
					except rpl.RPLBadType:
						# String type.
						d, t = u.string(), 1
					except AttributeError:
						# unpacked is a unicode string
						d, t = u, 1
					#endtry

					if expand:
						# Chop off what was actually used from data.
						return d, t, data[len(p):]
					else: return d, t
				#endif
			#endfor

			# If we arrive here, no match was found.
			if expand: raise RPLError("Impossible to continue mapping dynamically sized map on bad match.")
			action = self["unmapped"].get()[0:6] # Hack for normalizing addstr/num.
			stringInterp = self.rpl.wrap("string").unserialize(data, **options).string()
			numberInterp = self.rpl.wrap("number").unserialize(data, **options).number()
			if action == "drop": return None
			elif action == "addstr": d = stringInterp
			elif action == "addnum": d = numberInterp
			elif len(types) == 1:
				# Has to be the only base type interpreted.
				d, t = (stringInterp, 1) if types[0] == "string" else (numberInterp, 0)
			elif mode == 1:
				# Has to be a string
				d, t = stringInterp, 1
			else:
				# Dunno, just print the hex.
				d = u''.join(["%02x" % ord(x) for x in data])
				if action == "add":
					raise RPLError(u"Cannot add unmapped value: %s Try using addstr or addnum instead." % unicode(d))
			#endif

			if action == "except":
				raise RPLError(u"Unmapped value: %s" % unicode(d))
			elif action[0:3] == "add": return d, t
		#enddef

		# Interpret.
		if width == "all": myData, typ = tmpfunc(bindata, False)
		elif width == "dynamic":
			# Read until exhausted. Assumes string map.
			ret = u""
			while bindata:
				tmp, typ, bindata = tmpfunc(bindata, True)
				if tmp is not None: ret += tmp
			#endwhile
			myData = ret
		else:
			# Chunk and map. Assumes string map.
			ret = u""
			for i in helper.range(0, len(bindata), width):
				tmp, typ = tmpfunc(bindata[i:i + width], False)
				if tmp is not None: ret += tmp
			#endfor
			myData = ret
		#endif
		self.myData = self.rpl.wrap((number or cast or "number") if typ == 0 else (string or cast or "string"), myData)
	#enddef

	def importDataLoop(self, rom, folder, base=None, callers=[]):
		options, packed, unpacked, mode, cast, string, number, width, types = self.prepare(callers)

		try: unpacked[0].get
		except AttributeError: unpacked = list(unpacked)
		else: unpacked = [x.get() for x in unpacked]

		def tmpfunc(data):
			try: return packed[unpacked.index(data)]
			except IndexError:
				# No match
				action = self["unmapped"].get()[0:6] # Hack for normalizing addstr/num.
				try: stringInterp = self.rpl.wrap(string or cast or "string", data)
				except RPLBadType: action = "addnum"
				try: numberInterp = self.rpl.wrap(number or cast or "number", data)
				except RPLBadType: action = "addstr"
				if action == "drop": return None
				elif action == "addstr": d = stringInterp
				elif action == "addnum": d = numberInterp
				elif len(types) == 1:
					# Has to be the only base type interpreted.
					d = stringInterp if types[0] == "string" else numberInterp
				elif mode == 1:
					# Has to be a string
					d = stringInterp
				else:
					# Dunno, just print the hex.
					d = u''.join(["%02x" % ord(x) for x in data])
					if action == "add":
						raise RPLError(u"Cannot add unmapped value: %s Try using addstr or addnum instead." % unicode(d))
					#endif
				#endif

				if action == "except":
					raise RPLError(u"Unmapped value: %s" % unicode(d))
				elif action[0:3] == "add": return d.serialize(**options)
			#endtry
		#enddef

		# Interpret.
		self.rpl.rom.seek(self.base.number())
		if width == "all":
			tmp = tmpfunc(self.myData.get())
			if tmp is not None: self.rpl.rom.write(tmp)
		else:
			# Writes until exhausted. Assumes string map.
			ret = r""
			for x in self.myData.string():
				tmp = tmpfunc(x)
				if tmp is not None: ret += tmp
			#endwhile
			self.rpl.rom.write(ret)
		#endif
	#endif

	def exportDataLoop(self, rom, folder, datafile, to, key, callers=[]):
		datafile.add(key, self.myData, to)
	#enddef

	def basic(self):
		# DataFormat.__getitem__ export branch calls this.
		return self.myData
	#enddef

	def len(self):
		return self.size.number()
	#enddef
#endclass
