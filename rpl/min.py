#-*- coding:utf-8 -*-

import re
import rpl, std, helper
from textwrap import dedent

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
	rpl.registerStruct(Tile)
	rpl.registerStruct(Tilemap)
	rpl.registerStruct(Tile3)
	rpl.registerStruct(Tilemap3)
	rpl.registerStruct(Sprite)
	rpl.registerStruct(Spritemap)
	rpl.registerStruct(Sprite3)
	rpl.registerStruct(Spritemap3)

	rpl.registerType(Pokestr)
	# TODO: Adjust ROM
#endclass

def printHelp(more_info=[]):
	print(
		"min is the library for Pokemon Mini ROMs.\n"
		"It offers the structs:\n"
		"  tile  tilemap  tile3  tilemap3  sprite  spritemap  sprite3  spritemap3\n\n"
		"And the types:\n"
		"  pokestr\n"
	)
	if not more_info: print "Use --help std [structs...] for more info"
	infos = {
		"tile": Tile, "tilemap": Tilemap,
		"tile3": Tile3, "tilemap3": Tilemap3,
		"sprite": Sprite, "spritemap": Spritemap,
		"sprite3": Sprite, "spritemap3": Spritemap3,
		"pokestr": Pokestr,
	}
	for x in more_info:
		if x in infos: print dedent(infos[x].__doc__)
	#endfor
#enddef

def splitBits(byte):
	return (
		(byte & 0x80) >> 7,
		(byte & 0x40) >> 6,
		(byte & 0x20) >> 5,
		(byte & 0x10) >> 4,
		(byte & 0x08) >> 3,
		(byte & 0x04) >> 2,
		(byte & 0x02) >> 1,
		(byte & 0x01),
	)
#enddef

################################################################################
#################################### Structs ###################################
################################################################################
class Tile(std.Graphic):
	"""
	Manage a single two-color tile.
	Tiles are 8x8 images of form 0bw and reading DULR.
	"""
	typeName = "tile"

	def __init__(self, _rpl, name, parent=None, tilemap=False):
		std.Graphic.__init__(self, _rpl, name, parent)

		self.registerKey("white", "color", "white")
		self.registerKey("black", "color", "black")
		self.registerKey("invert", "bool", "false")

		self._owm = self._ohm = self._wm = self._hm = 8
		self._baseOffset = None

		if not tilemap: self.unregisterKey("dimensions")
	#enddef

	def __getitem__(self, key):
		if key == "base" and "base" not in self._data and self._baseOffset is not None:
			return rpl.Number(
				self._parent.base() + self._parent.mapSize() + self._baseOffset
			)
		else: return std.Graphic.__getitem__(self, key)
	#enddef

	def getPalette(self):
		return (
			[self["black"].tuple(), self["white"].tuple()]
			if self["invert"].get() else
			[self["white"].tuple(), self["black"].tuple()]
		)
	#enddef

	def importTile(self, rom, data):
		pixel, shift, pixels = 0, 7, r""
		for i, x, y in std.ReadDir("DULR").rect(8, 8):
			pixel |= self.indexOf(data[x, y]) << shift
			if shift: shift -= 1
			else:
				pixels += chr(pixel)
				shift, pixel = 7, 0
			#endif
		#endfor
		rom.write(pixels)
	#enddef

	def importData(self, rom, folder):
		self.definePalette(self.getPalette())
		self.base(rom=rom)
		self.importTile(rom, self._image.load())
	#enddef

	@staticmethod
	def prepareTile(bytes, palette):
		pixels, x, p = [0] * 64, 56, 0
		for byte in bytes:
			p = x
			for pixel in splitBits(ord(byte)):
				pixels[p] = palette[pixel]
				p -= 8
			#endfor
			x += 1
		#endfor
		return pixels
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		self.base()
		self._image.putdata(Tile.prepareTile(self._rpl.rom.read(8), self.getPalette()))
	#enddef
#endclass

class Tilemap(Tile):
	"""
	Manages two-color tiles.
	Tiles are 8x8 images of form 0bw and reading DULR.
	Tilemaps index multiple [usually sequential] tiles.
	"""
	typeName = "tilemap"

	def __init__(self, _rpl, name, parent=None):
		Tile.__init__(self, _rpl, name, parent, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Tile)

		self._curBase, self._mapSize = None, None
	#enddef

	def addChild(self, sType, name):
		new = Tile.addChild(self, sType, name)
		new._baseOffset = (len(self._children) - 1) * 8
		return new
	#enddef

	def mapSize(self):
		highestIdx = 0
		for v in self["map"].get():
			if isinstance(v, rpl.Number): highestIdx = max(highestIdx, v.get())
		#endfor
		return 8 * (highestIdx + 1)
	#enddef

	def importData(self, rom, folder):
		tilemap, base = self["map"].get(), self.base()
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				t, x, y = t.get(), x * 8, y * 8
				self.base(offset=t * 8)
				self.importTile(rom,
					self._image.crop((x, y, x + 8, y + 8)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()

		# Loop through map and export each tile.
		self.base()
		bytes = self._rpl.rom.read(self.mapSize())
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 8, y * 8
				cut = self._image.crop((x, y, x + 8, y + 8))
				if t == "x": cut.putdata([blank] * 64)
				else:
					t *= 8
					cut.putdata(Tile.prepareTile(bytes[t:t + 8], palette))
				#endif
				self._image.paste(cut, (x, y))
			#endif
		#endfor
	#enddef
#endclass

class Tile3(Tile):
	"""
	Manage a single three-color tile.
	Tiles are two 8x8 images of form 0bw and reading DULR that are
	combined by t1 & t2 being black, t1 nor t2 being white, and
	t1 ^ t2 being gray.
	"""
	typeName = "tile3"

	def __init__(self, _rpl, name, parent=None, tilemap=False):
		Tile.__init__(self, _rpl, name, parent, tilemap)

		self.registerKey("gray", "color", "gray")
		self.registerKey("base1", self._keys["base"][0]._source, "$000000")
		self.registerKey("base2", self._keys["base"][0]._source, "$000000")

		self.unregisterKey("base")
	#enddef

	def __getitem__(self, key):
		if (key in ["base1", "base2"] and key not in self._data and
			self._baseOffset[idx] is not None
		):
			return rpl.Number(
				self._parent.base(self._parent[key]) +
				self._parent.mapSize() + self._baseOffset
			)
		elif key == "grey": return std.Graphic.__getitem__(self, "gray")
		else: return std.Graphic.__getitem__(self, key)
	#enddef

	def __setitem__(self, key, value):
		if key == "grey": std.Graphic.__setitem__(self, "gray", value)
		else: std.Graphic.__setitem__(self, key, value)
	#enddef

	def getPalette(self):
		return (
			[self["black"].tuple(), self["white"].tuple(), self["gray"].tuple()]
			if self["invert"].get() else
			[self["white"].tuple(), self["black"].tuple(), self["gray"].tuple()]
		)
	#enddef

	def importTile(self, rom, base1, base2, data):
		pixel1, pixel2, shift, pixels1, pixels2 = 0, 0, 7, r"", r""
		for i, x, y in std.ReadDir("DULR").rect(8, 8):
			tmp = self.indexOf(data[x, y])
			if tmp == 2:
				if (i + x % 2) % 2: pixel1 |= 1 << shift
				else:               pixel2 |= 1 << shift
			else:
				pixel1 |= tmp << shift
				pixel2 |= tmp << shift
			#endif

			if shift: shift -= 1
			else:
				pixels1 += chr(pixel1)
				pixels2 += chr(pixel2)
				shift, pixel1, pixel2 = 7, 0, 0
			#endif
		#endfor
		self.base(base1)
		rom.write(pixels1)
		self.base(base2)
		rom.write(pixels2)
	#enddef

	def importData(self, rom, folder):
		self.definePalette(self.getPalette())
		self.importTile(rom, self["base1"], self["base2"], self._image.load())
	#enddef

	@staticmethod
	def prepareTile(bytes1, bytes2, palette):
		pixels, x = [0] * 64, 56
		for i in helper.range(8):
			p = x
			byte1, byte2 = ord(bytes1[i]), ord(bytes2[i])
			black, gray = splitBits(byte1 & byte2), splitBits(byte1 ^ byte2)
			for pixel in helper.range(8):
				pixels[p] = palette[gray[pixel] << 1 | black[pixel]]
				p -= 8
			#endfor
			x += 1
		#endfor
		return pixels
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		self.base(self["base1"])
		data1 = self._rpl.rom.read(8)
		self.base(self["base2"])
		data2 = self._rpl.rom.read(8)
		self._image.putdata(Tile3.prepareTile(data1, data2, self.getPalette()))
	#enddef
#endclass

class Tilemap3(Tile3, Tilemap):
	"""
	Manages three-color tiles.
	Tiles are two 8x8 images of form 0bw and reading DULR that are
	combined by t1 & t2 being black, t1 nor t2 being white, and
	t1 ^ t2 being gray.
	Tilemaps index multiple [usually sequential] tiles.
	"""
	typeName = "tilemap3"

	def __init__(self, _rpl, name, parent=None):
		Tile3.__init__(self, _rpl, name, parent, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Tile3)

		self._curBase, self._mapSize = None, None
	#enddef

	def importData(self, rom, folder):
		tilemap, base1, base2 = self["map"].get(), self.base(self["base1"]), self.base(self["base2"])
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				t, x, y = t.get() * 8, x * 8, y * 8
				self.importTile(rom, base1 + t, base2 + t,
					self._image.crop((x, y, x + 8, y + 8)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()

		# Loop through map and export each tile.
		mapSize = self.mapSize()
		self.base(self["base1"])
		bytes1 = self._rpl.rom.read(mapSize)
		self.base(self["base2"])
		bytes2 = self._rpl.rom.read(mapSize)
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 8, y * 8
				cut = self._image.crop((x, y, x + 8, y + 8))
				if t == "x": cut.putdata([blank] * 64)
				else:
					t *= 8
					cut.putdata(Tile3.prepareTile(bytes1[t:t + 8], bytes2[t:t + 8], palette))
				#endif
				self._image.paste(cut, (x, y))
			#endif
		#endfor
	#enddef
#endclass

class Sprite(std.Graphic):
	"""
	Manage a single two-color sprite.
	Sprites are 16x16 images of form UL mask, BL mask, UL draw, BL draw,
	UR mask, BR mask, UR draw, BR draw.
	Mask sections are of form 0ba and reading DULR.
	Draw sections are of form 0bw and reading DULR.
	"""
	typeName = "sprite"

	def __init__(self, _rpl, name, parent=None, spritemap=False):
		std.Graphic.__init__(self, _rpl, name, parent)

		self.registerKey("white", "color", "white")
		self.registerKey("black", "color", "black")
		self.registerKey("alpha", "color", "cyan")
		self.registerKey("setalpha", "color", "magenta")
		self.registerKey("invert", "bool", "false")
		self.registerKey("inverta", "bool", "false")

		self._owm = self._ohm = self._wm = self._hm = 16
		self._baseOffset = None

		if not spritemap: self.unregisterKey("dimensions")
	#enddef

	def __getitem__(self, key):
		if key == "base" and "base" not in self._data and self._baseOffset is not None:
			return rpl.Number(
				self._parent.base() + self._parent.mapSize() + self._baseOffset
			)
		else: return std.Graphic.__getitem__(self, key)
	#enddef

	def getPalette(self):
		return (
			([self["black"].tuple(), self["white"].tuple()]
			if self["invert"].get() else
			[self["white"].tuple(), self["black"].tuple()]) +
			([self["setalpha"].tuple(), self["alpha"].tuple()]
			if self["inverta"].get() else
			[self["alpha"].tuple(), self["setalpha"].tuple()])
		)
	#enddef

	def importSprite(self, rom, data):
		pixeld, pixelm, shift = 0, 0, 7
		pixels, draw, mask = r"", r"", r""
		# UL, BL, UR, BR
		for q, qx, qy in std.ReadDir("UDLR").rect(2, 2):
			# Each quadrant is the same as a tile, but there's also a mask
			# quadrant to manage.
			qx *= 8
			qy *= 8
			for i, x, y in std.ReadDir("DULR").rect(8, 8):
				tmp = self.indexOf(data[qx + x, qy + y])
				if tmp & 0x02: pixelm |= 1 << shift
				pixeld |= (tmp & 0x01) << shift
				if shift: shift -= 1
				else:
					draw += chr(pixeld)
					mask += chr(pixelm)
					shift, pixeld, pixelm = 7, 0, 0
				#endif
			#endfor

			# After finishing a bottom quadrant, commit to pixels
			if qy == 8:
				pixels += mask + draw
				draw, mask = r"", r""
			#endif
		#endfer
		rom.write(pixels)
	#enddef

	def importData(self, rom, folder):
		self.definePalette(self.getPalette())
		self.base(rom=rom)
		self.importSprite(rom, self._image.load())
	#enddef

	@staticmethod
	def prepareSprite(bytes, palette):
		pixels = [0] * 256
		for q in helper.range(4):
			x = [112, 240, 120, 248][q]
			base = [0, 8, 32, 40][q]
			for i in helper.range(base, base + 8):
				p = x
				mask, draw = splitBits(ord(bytes[i])), splitBits(ord(bytes[i + 16]))
				for pixel in helper.range(8):
					pixels[p] = palette[mask[pixel] << 1 | draw[pixel]]
					p -= 16
				#endfor
				x += 1
			#endfor
		#endfor
		return pixels
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		self.base()
		self._image.putdata(Sprite.prepareSprite(self._rpl.rom.read(64), self.getPalette()))
	#enddef
#endclass

class Spritemap(Sprite):
	"""
	Manage multiple two-color sprites.
	Sprites are 16x16 images of form UL mask, BL mask, UL draw, BL draw,
	UR mask, BR mask, UR draw, BR draw.
	Mask sections are of form 0ba and reading DULR.
	Draw sections are of form 0bw and reading DULR.
	"""
	typeName = "spritemap"

	def __init__(self, _rpl, name, parent=None):
		Sprite.__init__(self, _rpl, name, parent, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Sprite)

		self._curBase, self._mapSize = None, None
	#enddef

	def addChild(self, sType, name):
		new = Sprite.addChild(self, sType, name)
		new._baseOffset = (len(self._children) - 1) * 8
		return new
	#enddef

	def mapSize(self):
		highestIdx = 0
		for v in self["map"].get():
			if isinstance(v, rpl.Number): highestIdx = max(highestIdx, v.get())
		#endfor
		return 64 * (highestIdx + 1)
	#enddef

	def importData(self, rom, folder):
		tilemap, base = self["map"].get(), self.base()
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				x, y = x * 16, y * 16
				self.base(offset=t.get() * 64)
				self.importSprite(rom,
					self._image.crop((x, y, x + 16, y + 16)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()
		secx = [blank] * 256

		# Loop through map and export each sprite.
		self.base()
		bytes = self._rpl.rom.read(self.mapSize())
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 16, y * 16
				cut = self._image.crop((x, y, x + 16, y + 16))
				if t == "x": cut.putdata(secx)
				else:
					t *= 64
					cut.putdata(Sprite.prepareSprite(bytes[t:t + 64], palette))
				#endif
				self._image.paste(cut, (x, y))
			#endif
		#endfor
	#enddef
#endclass

class Sprite3(Sprite):
	"""
	Manage a single three-color sprite.
	Sprites are 16x16 images of form UL mask, BL mask, UL draw, BL draw,
	UR mask, BR mask, UR draw, BR draw.
	Mask sections are of form 0ba and reading DULR.
	Draw sections are of form 0bw and reading DULR.
	"""
	typeName = "sprite3"

	def __init__(self, _rpl, name, parent=None, spritemap=False):
		Sprite.__init__(self, _rpl, name, parent, spritemap)

		self.registerKey("gray", "color", "gray")
		self.registerKey("base1", self._keys["base"][0]._source, "$000000")
		self.registerKey("base2", self._keys["base"][0]._source, "$000000")

		self.unregisterKey("base")
	#enddef

	def __getitem__(self, key):
		if (key in ["base1", "base2"] and key not in self._data and
			self._baseOffset[idx] is not None
		):
			return rpl.Number(
				self._parent.base(self._parent[key]) +
				self._parent.mapSize() + self._baseOffset
			)
		elif key == "grey": return std.Graphic.__getitem__(self, "gray")
		else: return std.Graphic.__getitem__(self, key)
	#enddef

	def __setitem__(self, key, value):
		if key == "grey": std.Graphic.__setitem__(self, "gray", value)
		else: std.Graphic.__setitem__(self, key, value)
	#enddef

	def getPalette(self):
		return (
			([self["black"].tuple(), self["white"].tuple()]
			if self["invert"].get() else
			[self["white"].tuple(), self["black"].tuple()]) +
			([self["setalpha"].tuple(), self["alpha"].tuple()]
			if self["inverta"].get() else
			[self["alpha"].tuple(), self["setalpha"].tuple()]) +
			[self["gray"].tuple()]
		)
	#enddef

	def importSprite(self, rom, base1, base2, data):
		pixelm, pixeld1, pixeld2, shift = 0, 0, 0, 7
		pixels1, pixels2, mask, draw1, draw2 = r"", r"", r"", r"", r""
		# UL, BL, UR, BR
		for q, qx, qy in std.ReadDir("UDLR").rect(2, 2):
			# Each quadrant is the same as a tile, but there's also a mask
			# quadrant to manage.
			qx *= 8
			qy *= 8
			for i, x, y in std.ReadDir("DULR").rect(8, 8):
				tmp = self.indexOf(data[qx + x, qy + y])
				if tmp == 4:
					if (i + x % 2) % 2: pixeld1 |= 1 << shift
					else:               pixeld2 |= 1 << shift
				else:
					if tmp & 0x02: pixelm |= 1 << shift
					tmp = (tmp & 0x01) << shift
					pixeld1 |= tmp
					pixeld2 |= tmp
				#endif
				if shift: shift -= 1
				else:
					mask += chr(pixelm)
					draw1 += chr(pixeld1)
					draw2 += chr(pixeld2)
					shift, pixelm, pixeld1, pixeld2 = 7, 0, 0, 0
				#endif
			#endfor

			# After finishing a bottom quadrant, commit to pixels
			if qy == 8:
				pixels1 += mask + draw1
				pixels2 += mask + draw2
				mask, draw1, draw2  = r"", r"", r""
			#endif
		#endfer
		self.base(base1)
		rom.write(pixels1)
		self.base(base2)
		rom.write(pixels2)
	#enddef

	def importData(self, rom, folder):
		self.definePalette(self.getPalette())
		self.importSprite(rom, self["base1"], self["base2"], self._image.load())
	#enddef

	@staticmethod
	def prepareSprite(bytes1, bytes2, palette):
		pixels = [0] * 256
		for q in helper.range(4):
			x = [112, 240, 120, 248][q]
			base = [0, 8, 32, 40][q]
			for i in helper.range(base, base + 8):
				p = x
				# If one mask is opaque and one is transparent, prefer opaque..
				mask = splitBits(ord(bytes1[i]) & ord(bytes2[i]))
				i = i + 16
				byte1, byte2 = ord(bytes1[i]), ord(bytes2[i])
				black, gray = splitBits(byte1 & byte2), splitBits(byte1 ^ byte2)
				for pixel in helper.range(8):
					if gray[pixel] and not mask[pixel]: pixels[p] = palette[4]
					else: pixels[p] = palette[mask[pixel] << 1 | black[pixel]]
					p -= 16
				#endfor
				x += 1
			#endfor
		#endfor
		return pixels
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		self.base(self["base1"])
		data1 = self._rpl.rom.read(64)
		self.base(self["base2"])
		data2 = self._rpl.rom.read(64)
		self._image.putdata(Sprite3.prepareSprite(data1, data2, self.getPalette()))
	#enddef
#endclass

class Spritemap3(Sprite3, Spritemap):
	"""
	Manage multiple three-color sprites.
	Sprites are 16x16 images of form UL mask, BL mask, UL draw, BL draw,
	UR mask, BR mask, UR draw, BR draw.
	Mask sections are of form 0ba and reading DULR.
	Draw sections are of form 0bw and reading DULR.
	"""
	typeName = "spritemap3"

	def __init__(self, _rpl, name, parent=None):
		Sprite3.__init__(self, _rpl, name, parent, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Sprite3)

		self._curBase, self._mapSize = None, None
	#enddef

	def importData(self, rom, folder):
		tilemap, base1, base2 = self["map"].get(), self.base(self["base1"]), self.base(self["base2"])
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				t, x, y = t.get() * 64, x * 16, y * 16
				self.importSprite(rom, base1 + t, base2 + t,
					self._image.crop((x, y, x + 16, y + 16)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()
		secx = [blank] * 256

		# Loop through map and export each sprite.
		mapSize = self.mapSize()
		self.base(self["base1"])
		bytes1 = self._rpl.rom.read(mapSize)
		self.base(self["base2"])
		bytes2 = self._rpl.rom.read(mapSize)
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 16, y * 16
				cut = self._image.crop((x, y, x + 16, y + 16))
				if t == "x": cut.putdata(secx)
				else:
					t *= 64
					cut.putdata(Sprite3.prepareSprite(bytes1[t:t + 64], bytes2[t:t + 64], palette))
				#endif
				self._image.paste(cut, (x, y))
			#endif
		#endfor
	#enddef
#endclass

################################################################################
##################################### Types ####################################
################################################################################
class Pokestr(rpl.Literal):
	"""
	Un/serializes strings between the standard PM encoding and UTF8.
	It's pretty similar to ASCII, just that the upper section is a local charset.
	Not all games use a font that implements everything.
	There are two types for those that implement Katakana:
	Type 1 implements ($7b-$7e): {:}~
	Type 2 implements ($a1-$a5): 。「」、・
	Some don't implement: [¥]^_`
	Sometimes ¥ is implemented as ⋯

	Katakan starts at $a6.
	Zany Cards DE/FR implements accented latin characters starting at $a0.
	Though it's only used once, I'm allowing this to serialize it as well since
	it is used in the same way as the regular pokestr.
	Zany Cards JP has a completely different font and I'm not going to support
	it. Editors of that game can use a map struct.
	"""
	typeName = "pokestr"

	upperSets = dict([(c, 0xa0 + i) for charset in [
		u"　。「」、・ヲァィゥェォャュョッーアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワン゛゜",
		u"ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ",
	] for i, c in enumerate(charset)], **{
		"¥": 0x5c, "…": 0x5c, "⋯": 0x5c,
	})

	raw = (
		u"".join(map(lambda x: unichr(x), helper.range(0x21))) +
		u" !\"#$%&'()*+,-./"
		u"0123456789:;<=>?"
		u"@ABCDEFGHJIKLMNO"
		u"PQRSTUVWXYZ[¥]^_"
		u"`abcdefghijklmno"
		u"pqrstuvwxyz{:}~" +
		u"".join(map(lambda x: unichr(x), helper.range(0x7f, 0xa0))) +
		u"　。「」、・ヲァィゥェォャュョッ"
		u"ーアイウエオカキクケコサシスセソ"
		u"タチツテトナニヌネノハヒフヘホマ"
		u"ミムメモヤユヨラリルレロワン゛゜" +
		u"".join(map(lambda x: unichr(x), helper.range(0xe0, 0x100)))
	)

	convUnserialize = re.compile(r'(.)([゛゜])', re.UNICODE)

	def serialize(self, **kwargs):
		new = r""
		for x in data:
			try: new += Pokestr.upperSets[x]
			except KeyError:
				if ord(x) <= 0xff: new += x
				else: raise RPLError('Unicode char "%s" not in %s ecnoding.' % (x, self.typeName))
			#endtry
		#endfor
		return new
	#enddef

	def unserialize(self, data, **kwargs):
		new = u"".join(map(lambda x: Pokestr.raw[ord(x)], data))
		self._data = convUnserialize.sub(Pokestr.joinKatakana, new)
	#enddef

	@staticmethod
	def joinKatakana(mo):
		char, voice = mo.groups()
		if voice == u"゛":
			try:
				return u"ガギグゲゴザジズゼゾダヂヅデドバビブベボヴヷヺ"[
					u"カキクケコサシスセソタチツテトハヒフヘホウワヲ".index(char)
				]
			except ValueError: return mo.group(0)
		elif voice == u"゜":
			try: return u"パピプペポ"[u"ハヒフヘホ".index(char)]
			except ValueError: return mo.group(0)
		#endif
	#enddef
#endclass
