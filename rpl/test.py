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
	rpl.registerStruct(Echo)
#enddef

def printHelp(more_info=[]):
	print(
		"The test library offers structs helpful for unittests.\n"
		"It offers the structs:\n"
		"  echo\n"
	)
	if not more_info: print "Use --help test [structs...] for more info"
	infos = {
		"echo": Echo,
	}
	for x in more_info:
		if x in infos: print dedent(infos[x].__doc__)
	#endfor
#enddef

class Echo(RPL.RPLStruct):
	"""
	Print data to stdout. Automaticall handles wrapping and tabbing text for you.
	width: Width of console. Default: 79.
	tabs: Tab character to use. Default: four spaces.
	line#: Where # is the line number. These are sorted at runtime, but missing
	       entries are ignored. If you want a blank line, do line#: ""
	       Numbers are interpreted as strings.
	"""

	typeName = "echo"
	def __init__(self, rpl, name, parent=None):
		RPL.RPLStruct.__init__(self, rpl, name, parent)
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
				key = lambda(x): int("0" + x[4:])
			)
		#endif

		# Print lines
		for x in lines:
			data = self[x].resolve()
			if isinstance(data, RPL.List):
				# Lists are considered to be tabbed in, with wrapping.
				for x in data.get(): self.echo(tabs + self["tabs"].get())
			else: print self.wrap(tabs, unicode(data.get()), self["width"].get())
		#endfor
	#enddef

	def importPrepare(self, *args): self.echo()
	def exportPrepare(self, *args): self.echo()

	def __setitem__(self, key, value):
		if key[0:4] == "line":
			RPL.RPLStruct.__setitem__(self, "line", value)
			self.data[key] = self.data["line"]
			del self.data["line"]
		else: RPL.RPLStruct.__setitem__(self, key, value)
	#enddef
#endclass
