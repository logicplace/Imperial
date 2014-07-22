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

import rpl, helper

def register(rpl):
	rpl.registerStruct(Echo)
#enddef

def printHelp(moreInfo=[]):
	helper.genericHelp(globals(), moreInfo,
		"The test library offers structs helpful for unittests.", "test", {
			# Structs
			"echo": Echo,
		}
	)
#enddef

class Echo(rpl.RPLStruct):
	"""
	Print data to stdout. Automatically handles wrapping and tabbing text for you.

	<width>
	width: Width of console. Default: 79.</width>
	<tabs>
	tabs: Tab character to use. Default: four spaces.</tabs>
	<line>
	line#: Where # is the line number. These are sorted at runtime, but missing
	       entries are ignored. If you want a blank line, do line#: ""
	       Numbers are interpreted as strings.</line>
	"""

	typeName = "echo"

	def register(self):
		self.registerKey("width", "number", "79")
		self.registerKey("tabs", "string", "'    '")
		self.registerKey("line", "[string|number|^]*")
	#enddef

	def wrap(self, tabs, text, chars):
		ret = ""
		while text:
			tmp = tabs + text
			ret += tmp[0:chars]
			text = tmp[chars:]
		#endwhile
		return ret
	#enddef

	def echo(self, lines=None, tabs=""):
		if lines is None:
			# Collect and sort lines...
			lines = sorted([x for x in self.iterkeys() if x.find("line") == 0],
				key = lambda x: int("0" + x[4:])
			)
		#endif

		# Print lines
		for x in lines:
			data = self[x].resolve()
			if isinstance(data, rpl.List):
				# Lists are considered to be tabbed in, with wrapping.
				for x in data.get(): self.echo(tabs + self["tabs"].get())
			else: print(self.wrap(tabs, unicode(data.get()), self["width"].get()))
		#endfor
	#enddef

	def importPrepare(self, *args): self.echo()
	def exportPrepare(self, *args): self.echo()

	def __setitem__(self, key, value):
		if key[0:4] == "line":
			rpl.RPLStruct.__setitem__(self, "line", value)
			self.data[key] = self.data["line"]
			del self.data["line"]
		else: rpl.RPLStruct.__setitem__(self, key, value)
	#enddef
#endclass
