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

import re
import rpl, std, helper

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
#enddef

def printHelp(moreInfo=[]):
	helper.genericHelp(globals(), moreInfo,
		"min is the library for Pokemon Mini ROMs.", "min", {
			# Structs
			"tile": Tile, "tilemap": Tilemap,
			"tile3": Tile3, "tilemap3": Tilemap3,
			"sprite": Sprite, "spritemap": Spritemap,
			"sprite3": Sprite, "spritemap3": Spritemap3,
		}, {
			# Types
			"pokestr": Pokestr,
		}
	)
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
	{/isnip}
	{cimp std.Graphic}
	white:  Optional. Set color for white pixel. (Default: white)
	        See [std.color] for details.
	black:  Optional. Set color for black pixel. (Default: black)
	        See [std.color] for details.
	invert: Optional. Invert pixels. Simpler than setting them to opposites.
	        (Default: false)
	"""
	typeName = "tile"

	def __init__(self, top, name, parent=None):
		std.Graphic.__init__(self, top, name, parent)

		self.owm = self.ohm = self.wm = self.hm = 8
		self.baseOffset = None
	#enddef

	def register(self, tilemap=False):
		std.Graphic.register(self)
		self.registerKey("white", "color", "white")
		self.registerKey("black", "color", "black")
		self.registerKey("invert", "bool", "false")

		if not tilemap: self.unregisterKey("dimensions")
	#enddef

	def __getitem__(self, key):
		if key == "base" and "base" not in self.data and self.baseOffset is not None:
			return rpl.Number(
				self.parent["base"].number() + self.parent.mapSize() + self.baseOffset
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
		rom.seek(self["base"].number())
		self.importTile(rom, self.image.load())
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
		self.rpl.rom.seek(self["base"].number())
		self.image.putdata(Tile.prepareTile(self.rpl.rom.read(8), self.getPalette()))
	#enddef
#endclass

class Tilemap(Tile):
	"""
	Manages two-color tiles.
	Tiles are 8x8 images of form 0bw and reading DULR.
	Tilemaps index multiple [usually sequential] tiles.

	{imp Tile}
	map:    Map of tile indexes. If not used, use Tile substructs instead.
	dir:    Optional. Reading direction of the tilemap. See [std.readdir]
	        (Default: LRUD)
	"""
	typeName = "tilemap"

	def __init__(self, top, name, parent=None):
		Tile.__init__(self, top, name, parent)
		self.curBase = None
	#enddef

	def register(self):
		Tile.register(self, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Tile)
	#enddef

	def addChild(self, sType, name):
		new = Tile.addChild(self, sType, name)
		new.baseOffset = (len(self.children) - 1) * 8
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
		tilemap, base = self["map"].get(), self["base"].number()
		#rom.seek(base)
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				t, x, y = t.get(), x * 8, y * 8
				rom.seek(base + t * 8)
				self.importTile(rom,
					self.image.crop((x, y, x + 8, y + 8)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()

		# Loop through map and export each tile.
		self.rpl.rom.seek(self["base"].number())
		bytes = self.rpl.rom.read(self.mapSize())
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 8, y * 8
				cut = self.image.crop((x, y, x + 8, y + 8))
				if t == "x": cut.putdata([blank] * 64)
				else:
					t *= 8
					cut.putdata(Tile.prepareTile(bytes[t:t + 8], palette))
				#endif
				self.image.paste(cut, (x, y))
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

	def __init__(self, top, name, parent=None):
		Tile.__init__(self, top, name, parent)
	#enddef

	def register(self, tilemap=False):
		Tile.register(self, tilemap)
		self.registerKey("gray", "color", "gray")
		self.registerKey("base1", self.keys["base"][0].source, "$000000")
		self.registerKey("base2", self.keys["base"][0].source, "$000000")
		self.unregisterKey("base")
	#enddef

	def __getitem__(self, key):
		if (key in ["base1", "base2"] and key not in self.data and
			self.baseOffset[idx] is not None
		):
			return rpl.Number(
				self.parent[key] +
				self.parent.mapSize() + self.baseOffset
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
		rom.seek(base1)
		rom.write(pixels1)
		rom.seek(base2)
		rom.write(pixels2)
	#enddef

	def importData(self, rom, folder):
		self.definePalette(self.getPalette())
		self.importTile(rom, self["base1"].number(), self["base2"].number(), self.image.load())
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
		self.rpl.rom.seek(self["base1"].number())
		data1 = self.rpl.rom.read(8)
		self.rpl.rom.seek(self["base2"].number())
		data2 = self.rpl.rom.read(8)
		self.image.putdata(Tile3.prepareTile(data1, data2, self.getPalette()))
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

	def __init__(self, top, name, parent=None):
		Tile3.__init__(self, top, name, parent)
		self.curBase = None
	#enddef

	def register(self):
		Tile3.register(self, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Tile3)
	#enddef

	def importData(self, rom, folder):
		tilemap, base1, base2 = self["map"].get(), self["base1"].number(), self["base2"].number()
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			if i >= len(tilemap): break
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				t, x, y = t.get() * 8, x * 8, y * 8
				self.importTile(rom, base1 + t, base2 + t,
					self.image.crop((x, y, x + 8, y + 8)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()

		# Loop through map and export each tile.
		mapSize = self.mapSize()
		self.rpl.rom.seek(self["base1"].number())
		bytes1 = self.rpl.rom.read(mapSize)
		self.rpl.rom.seek(self["base2"].number())
		bytes2 = self.rpl.rom.read(mapSize)
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 8, y * 8
				cut = self.image.crop((x, y, x + 8, y + 8))
				if t == "x": cut.putdata([blank] * 64)
				else:
					t *= 8
					cut.putdata(Tile3.prepareTile(bytes1[t:t + 8], bytes2[t:t + 8], palette))
				#endif
				self.image.paste(cut, (x, y))
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

	def __init__(self, top, name, parent=None):
		std.Graphic.__init__(self, top, name, parent)
		self.owm = self.ohm = self.wm = self.hm = 16
		self.baseOffset = None
	#enddef

	def register(self, spritemap=False):
		std.Graphic.register(self)
		self.registerKey("white", "color", "white")
		self.registerKey("black", "color", "black")
		self.registerKey("alpha", "color", "cyan")
		self.registerKey("setalpha", "color", "magenta")
		self.registerKey("invert", "bool", "false")
		self.registerKey("inverta", "bool", "false")
		if not spritemap: self.unregisterKey("dimensions")
	#enddef

	def __getitem__(self, key):
		if key == "base" and "base" not in self.data and self.baseOffset is not None:
			return rpl.Number(
				self.parent["base"].number() + self.parent.mapSize() + self.baseOffset
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
		rom.seek(self["base"].number())
		self.importSprite(rom, self.image.load())
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
		self.rpl.rom.seek(self["base"].number())
		self.image.putdata(Sprite.prepareSprite(self.rpl.rom.read(64), self.getPalette()))
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

	def __init__(self, top, name, parent=None):
		Sprite.__init__(self, top, name, parent)
		self.curBase = None
	#enddef

	def register(self):
		Sprite.register(self, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Sprite)
	#enddef

	def addChild(self, sType, name):
		new = Sprite.addChild(self, sType, name)
		new.baseOffset = (len(self.children) - 1) * 8
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
		tilemap, base = self["map"].get(), self["base"].number()
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				x, y = x * 16, y * 16
				rom.seek(base + t.get() * 64)
				self.importSprite(rom,
					self.image.crop((x, y, x + 16, y + 16)).load()
				)
			#endif
		#endfor
	#enddef

	def prepareImage(self):
		std.Graphic.prepareImage(self)
		tilemap, blank = self["map"].get(), self["blank"].tuple()
		secx = [blank] * 256

		# Loop through map and export each sprite.
		self.rpl.rom.seek(self["base"].number())
		bytes = self.rpl.rom.read(self.mapSize())
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 16, y * 16
				cut = self.image.crop((x, y, x + 16, y + 16))
				if t == "x": cut.putdata(secx)
				else:
					t *= 64
					cut.putdata(Sprite.prepareSprite(bytes[t:t + 64], palette))
				#endif
				self.image.paste(cut, (x, y))
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

	def __init__(self, top, name, parent=None):
		Sprite.__init__(self, top, name, parent)
	#enddef

	def register(self, spritemap=False):
		Sprite.register(self, spritemap)
		self.registerKey("gray", "color", "gray")
		self.registerKey("base1", self.keys["base"][0].source, "$000000")
		self.registerKey("base2", self.keys["base"][0].source, "$000000")
		self.unregisterKey("base")
	#enddef

	def __getitem__(self, key):
		if (key in ["base1", "base2"] and key not in self.data and
			self.baseOffset[idx] is not None
		):
			return rpl.Number(
				self.parent[key] +
				self.parent.mapSize() + self.baseOffset
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
		rom.seek(base1)
		rom.write(pixels1)
		rom.seek(base2)
		rom.write(pixels2)
	#enddef

	def importData(self, rom, folder):
		self.definePalette(self.getPalette())
		self.importSprite(rom, self["base1"].number(), self["base2"].number(), self.image.load())
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
		self.rpl.rom.seek(self["base1"].number())
		data1 = self.rpl.rom.read(64)
		self.rpl.rom.seek(self["base2"].number())
		data2 = self.rpl.rom.read(64)
		self.image.putdata(Sprite3.prepareSprite(data1, data2, self.getPalette()))
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

	def __init__(self, top, name, parent=None):
		Sprite3.__init__(self, top, name, parent)

		self.curBase = None
	#enddef

	def register(self):
		Sprite3.register(self, True)
		self.registerKey("map", "range", "[]")
		self.registerKey("dir", "readdir", "LRUD")

		self.registerStruct(Sprite3)
	#enddef

	def importData(self, rom, folder):
		tilemap, base1, base2 = self["map"].get(), self["base1"].number(), self["base2"].number()
		self.definePalette(self.getPalette())
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i]
			if isinstance(t, rpl.Number):
				t, x, y = t.get() * 64, x * 16, y * 16
				self.importSprite(rom, base1 + t, base2 + t,
					self.image.crop((x, y, x + 16, y + 16)).load()
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
		self.rpl.rom.seek(self["base1"].number())
		bytes1 = self.rpl.rom.read(mapSize)
		self.rpl.rom.seek(self["base2"].number())
		bytes2 = self.rpl.rom.read(mapSize)
		palette = self.getPalette()
		for i, x, y in self["dir"].rect(*[x.get() for x in self["dimensions"].get()]):
			t = tilemap[i].get()
			if t != "i":
				x, y = x * 16, y * 16
				cut = self.image.crop((x, y, x + 16, y + 16))
				if t == "x": cut.putdata(secx)
				else:
					t *= 64
					cut.putdata(Sprite3.prepareSprite(bytes1[t:t + 64], bytes2[t:t + 64], palette))
				#endif
				self.image.paste(cut, (x, y))
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

	Katakana starts at $a6.
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
		self.data = convUnserialize.sub(Pokestr.joinKatakana, new)
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
