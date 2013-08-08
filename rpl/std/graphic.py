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

import os, re, Image
from .. import rpl, helper
from ..rpl import RPLError, RPLBadType
from StringIO import StringIO

def register(rpl):
	rpl.registerStruct(GenericGraphic)

	rpl.registerType(Pixel)
	rpl.registerType(Color)
#enddef

class ImageFile(rpl.Share):
	def __init__(self, width=0, height=0):
		self.dimensions = (width, height)
		self.image = None
		self.pixels = None
	#enddef

	def read(self):
		if self.image is None: self.image = Image.open(self.path).convert("RGBA")
	#enddef

	def write(self):
		if self.image is None: return # Maybe throw an exception?
		ext = os.path.splitext(self.path)[1][1:].lower()
		# Cannot save alpha..
		if ext == "bmp": self.image = self.image.convert("RGB")
		helper.makeParents(self.path)
		self.image.save(self.path)
	#enddef

	def newImage(self, width=1, height=1, blank=0xffffff):
		self.image = Image.new("RGBA", (width, height))
		self.image.paste(blank, (0, 0, width, height))
		self.pixels = self.image.load()
	#endif

	def ensureSize(self, width, height):
		# Only necessary when writing, remember!
		if self.image is None: return self.newImage(width, height)
		curWidth, curHeight = self.image.size
		if curWidth < width or curHeight < height:
			width = max(curWidth, width)
			height = max(curHeight, height)
			region = self.image.crop((0, 0, width, height))
			region.load()
			self.image = self.image.resize((width, height))
			self.image.paste(0xffffff, (0, 0, width, height))
			self.image.paste(region, (0, 0))
		#endif
	#enddef

	def addRect(self, data, left, top, width, height):
		if self.image is None: self.newImage()
		region = Image.new("RGBA", (width, height))
		region.putdata(data)
		self.image.paste(region, (left, top), region)
	#enddef

	def addImage(self, image, left, top):
		if self.image is None: self.newImage()
		self.image.paste(image, (left, top), image)
	#enddef

	def addPixel(self, rgba, x, y):
		if self.image is None: self.newImage()
		self.pixels[x, y] = rgba
	#enddef

	def getImage(self, left, top, width, height):
		img = self.image.crop((left, top, left + width, top + height))
		img.load()
		return img
	#enddef
#endclass

class ColorScan(object):
	"""
	In the future, this will handle scanning for nearest colors.
	At the moment, I don't care.
	"""
	def __init__(self, palette):
		try: obj = palette.iterkeys()
		except AttributeError: obj = enumerate(palette)

		# Convert to HSL and sort
		self.palette = {}
		for k, v in obj: self.palette[Graphic.hex(v)] = k
	#enddef

	def scan(self, color):
		return self.palette[Graphic.hex(color)]
	#enddef
#endclass

################################################################################
############################# Media Parent Struct ##############################
################################################################################

class Graphic(rpl.Serializable):
	"""
	Structs that handle images should inherit this.
	Do note that this is for flat images. If something were to handle layers,
	it would currently inherit this as well, but have to add a lot of
	functionality. This, however, should not be used for anything using more
	than two dimensions.
	<all><imp rpl.Serializable.all BR /><graphic>
	<transformations>
	Transformations are handled in the order: rotate -> mirror -> flip
	And this is reversed for exporting. But they are spoken about in regards
	to importing throughout the documentation.
	<rotate>
	rotate: Optional. 90 degree interval to rotate clockwise. 1 = 90, 2 = 180,
	        3 = 270 Other intervals are lossy and will not be supported. If you
	        need them rotated in such a way, do it in your graphics editor.
	        (Default: 0)</rotate>
	<mirror>
	mirror: Optional. Mirror the image horizontally. (Default: false)</mirror>
	<flip>
	flip:   Optional. Flip the image vertically. (Default: false)</flip></transformations>
	<blank>
	blank:  Optional. Background color, ie. what to use in places where graphics
	        aren't specifically drawn. (Default: white)</blank>
	<dimensions>
	dimensions: [width, height] of the canvas to draw on. By default it refers
	            to pixels, but *maps may adjust this to pw = width * multiplier;
	            ph = height * multiplier;</dimensions>
	<offset>
	offset: Optional. [x, y] of where to draw the image on the canvas. These are
	        0-based and are (by default) the pixel locations of the image. *maps
	        may adjust this to be px = x * multiplier; py = y * multiplier;
	        (Default: [0, 0])</offset></graphic></all>
	"""

	def __init__(self, top, name, parent=None):
		rpl.Serializable.__init__(self, top, name, parent)

		self.image = None
		self.importing = False
		# Offset Width/Height Multipliers
		self.owm, self.ohm = 1, 1
		# Width/Height Multipliers
		self.wm, self.hm = 1, 1
		self.palette = None
	#enddef

	def register(self):
		rpl.Serializable.register(self)
		self.registerKey("rotate", "number", "0")
		self.registerKey("mirror", "bool", "false")
		self.registerKey("flip", "bool", "false")
		self.registerKey("blank", "color", "white")
		self.registerKey("dimensions", "[number, number]")
		self.registerKey("offset", "[number, number]", "[0, 0]")
	#enddef

	def dimensions(self):
		try:
			dimens = self["dimensions"].get()
			return dimens[0].get() * self.wm, dimens[1].get() * self.hm
		except RPLError: return self.wm, self.hm
	#enddef

	def importTransform(self):
		if self.image is None: return False
		if self["rotate"].get() != 0:
			self.image = self.image.transpose([
				Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270
			][self["rotate"].get() - 1])
		#endif
		if self["mirror"].get(): self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
		if self["flip"].get(): self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
		return True
	#enddef

	def exportTransform(self):
		if self.image is None: return False
		if self["flip"].get(): self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
		if self["mirror"].get(): self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
		if self["rotate"].get() != 0:
			self.image = self.image.transpose([
				Image.ROTATE_270, Image.ROTATE_180, Image.ROTATE_90
			][self["rotate"].get() - 1])
		#endif
		return True
	#enddef

	def importPrepare(self, rom, folder):
		"""
		More often than not you won't have to overwrite this.
		Just set self.owm, self.ohm, self.wm, and self.hm
		"""
		# Read in image
		self.importing = True
		filename = self.open(folder, "png", True)
		image = self.rpl.share(filename, ImageFile)
		image.read()
		offs = self["offset"].get()
		width, height = self.dimensions()
		self.image = image.getImage(
			offs[0].get() * self.owm, offs[1].get() * self.ohm,
			width, height
		)
		# Do this here because export does it last
		self.importTransform()
	#enddef

	def prepareImage(self):
		"""
		Should override this with reading method.
		"""
		width, height = self.dimensions()
		# Palettes can't have per-color transparency? ;~;
		self.image = Image.new("RGBA", (width, height))
		self.image.paste(self["blank"].get(), (0, 0, width, height))
	#enddef

	def exportData(self, rom, folder):
		"""
		More often than not you won't have to overwrite this.
		Just set self.owm, self.ohm, self.wm, and self.hm
		"""
		if self.image is None: self.prepareImage()
		self.exportTransform()
		offs = self["offset"].get()
		offx, offy = offs[0].get() * self.owm, offs[1].get() * self.ohm
		width, height = self.dimensions()
		filename = self.open(folder, "png", True)
		image = self.rpl.share(filename, ImageFile)
		image.ensureSize(offx + width, offy + height)
		image.addImage(self.image, offx, offy)
	#enddef

	def basic(self):
		"""
		This operates under the assumption that if something wants to edit
		the image itself, it should reference the basic value, which will force
		the class to prepare the image (during exporting).
		"""
		if not self.importing: self.prepareImage()
		return rpl.String(self.name)
	#enddef

	def definePalette(self, palette):
		"""
		palette is an object keyed by palette index with value of the color.
		"""
		self.palette = ColorScan(palette)
	#enddef

	def indexOf(self, color):
		"""
		Return palette index of most similar color.
		color is form: 0xaaRRGGBB
		"""
		return self.palette.scan(color)
	#enddef

	@staticmethod
	def col(color):
		"""
		color can be: (r, g, b), (r, g, b, a), or 0xaaRRGGBB
		"""
		if type(color) is tuple:
			if len(color) == 3: return color + (255,)
			else: return color
		#endif
		return (
			(color & 0x00FF0000) >> 16,
			(color & 0x0000FF00) >> 8,
			(color & 0x000000FF),
			255 - ((color & 0xFF000000) >> 24),
		)
	#enddef

	@staticmethod
	def hex(color):
		if type(color) is tuple:
			if len(color) == 3: r, g, b, a = color + (255,)
			else: r, g, b, a = color
			return (
				(255 - (a & 0xff)) << 24 |
				(r & 0xff) << 16 |
				(g & 0xff) << 8 |
				b & 0xff
			)
		#endif
		return color
	#enddef

	@staticmethod
	def rgb2rgbMmhc(color):
		r, g, b, a = Graphic.col(color)
		r, g, b = r / 255.0, g / 255.0, b / 255.0
		M, m = max(r, g, b), min(r, g, b)
		c = M - m
		if c == 0: h = 0
		elif M == r: h = 60 * ((g - b) / c % 6)
		elif M == g: h = 60 * ((b - r) / c + 2)
		elif M == b: h = 60 * ((r - g) / c + 4)
		return r, g, b, a, M, m, h, c
	#enddef

	@staticmethod
	def rgb2hsl(color):
		r, g, b, a, M, m, h, c = Graphic.rgb2rgbMmhc(color)
		l = (M + m) / 2
		s = 0 if c == 0 else c * 100 / (1 - abs(2 * l - 1))
		return int(h), int(s), int(round(l * 100)), a
	#enddef

	@staticmethod
	def rgb2hsv(color):
		r, g, b, a, M, m, h, c = Graphic.rgb2rgbMmhc(color)
		v = M
		s = 0 if c == 0 else c * 100 / v
		return int(h), int(s), int(round(v * 100)), a
	#enddef
#endclass

################################################################################
#################################### Structs ###################################
################################################################################

def reverseEvery(data, x):
	return "".join(["".join(reversed(data[i:i+x])) for i in helper.range(0, len(data), x)])
#enddef

class GenericGraphic(Graphic):
	"""
	Manage generic graphical content.
	<if all><imp Graphic.all /></if>
	<read>
	read: Read direction. See [readdir].</read>
	<pixel>
	pixel: List of pixel formats, in order. More often than not there will
	       only be one pixel format. It will loop through these when it
	       reaches the end. See [pixel].</pixel>
	<palette>
	palette: 0-based palette. Use i form in palette to index against this.</palette>
	<reverse>
	reverse: Reverse the order of the bytes every X bytes. Example:
	         Data is: 0x01 23 45 67
	         reverse: 2
	         Final data is: 0x23 01 67 45</reverse>
	"""
	typeName = "graphic"

	def __init__(self, top, name, parent=None):
		Graphic.__init__(self, top, name, parent)
		self.image = None
	#enddef

	def register(self):
		Graphic.register(self)
		self.registerKey("read", "readdir", "LRUD")
		self.registerKey("pixel", "[pixel]*")
		self.registerKey("palette", "[color]+", "[]")
		self.registerKey("padding", "[string:(none, row, pixel, column), number]", "[none, 0]")
		self.registerKey("reverse", "math", "0")
	#enddef

	def padfuncDef(self, width, height):
		padmethod, padmod = tuple(self.list("padding", "get"))
		if self.rpl.importing:
			if padmethod == "row":
				widthmo = width - 1
				def padfunc(i, prev, leftover, stream):
					if i % width == widthmo:
						tmpmod = (stream.tell() - prev) % padmod
						#print "Skipping %i.%i bytes" % (padmod - tmpmod  if tmpmod else 0, 8 - leftover if leftover else 0)
						return (padmod - tmpmod  if tmpmod else 0, 0)
					#endif
					return (None, leftover)
				#enddef
			elif padmethod == "column":
				heightmo = height - 1
				def padfunc(i, prev, leftover, stream):
					if i % height == heightmo:
						tmpmod = (stream.tell() - prev) % padmod
						return (padmod - tmpmod  if tmpmod else 0, 0)
					return (None, leftover)
				#enddef
			elif padmethod == "pixel":
				def padfunc(i, prev, leftover, stream):
					tmpmod = (stream.tell() - prev) % padmod
					return (padmod - tmpmod  if tmpmod else 0, 0)
				#enddef
			else:
				def padfunc(i, prev, leftover, stream): return (None, leftover)
			#endif
		else:
			if padmethod == "row":
				widthmo = width - 1
				def padfunc(i, prev, leftovers, pos=None, stream=None):
					if i % width == widthmo:
						tmpmod = ((pos or stream.tell()) - prev) % padmod
						leftovers[1] = 0
						return padmod - tmpmod  if tmpmod else 0
					#endif
					return None
				#enddef
			elif padmethod == "column":
				heightmo = height - 1
				def padfunc(i, prev, leftovers, pos=None, stream=None):
					if i % height == heightmo:
						tmpmod = ((pos or stream.tell()) - prev) % padmod
						leftovers[1] = 0
						return padmod - tmpmod if tmpmod else 0
					#endif
					return None
				#enddef
			elif padmethod == "pixel":
				def padfunc(i, prev, leftovers, pos=None, stream=None):
					tmpmod = ((pos or stream.tell()) - prev) % padmod
					leftovers[1] = 0
					return padmod - tmpmod if tmpmod else 0
				#enddef
			else:
				def padfunc(i, prev, leftovers, pos=None, stream=None): return None
			#endif
		#endif
		return padfunc
	#enddef

	def importData(self, rom, folder):
		read = self["read"].get()
		width, height = tuple(self.list("dimensions", "number"))

		# Create padding function...
		prev = 0
		padfunc = self.padfuncDef(width, height)

		# Prepare palette
		self.definePalette(self.list("palette", "tuple"))

		# Prepare data
		leftover = 0
		data = self.image.load()
		pixels = self["pixel"].get()
		stream = StringIO()
		for idx, x, y in self["read"].rect(width, height):
			leftover = pixels[idx % len(pixels)].write(stream, self, leftover, data[x, y])
			skip, leftover = padfunc(idx, prev, leftover, stream)
			if skip is not None:
				if skip: stream.write("\x00" * skip)
				prev = stream.tell()
			#endif
		#endfor

		# Commit to ROM
		reverse = self["reverse"].get({
			"w": width, "width": width,
			"h": height, "height": height,
		})
		if reverse: rom.write(reverseEvery(stream.getvalue(), reverse))
		else: rom.write(stream.getvalue())
	#enddef

	def prepareImage(self):
		Graphic.prepareImage(self)
		width, height = tuple(self.list("dimensions", "number"))
		numPixels = width * height

		# Create padding function...
		prev = 0
		padfunc = self.padfuncDef(width, height)

		# Collect size of data to read
		pixels = self["pixel"].get()
		bytes = self.len(numPixels, padfunc, pixels)

		# Prepare palette
		palette = self.list("palette", "tuple")

		# Read pixels
		self.rpl.rom.seek(self.number("base"))
		reverse = self.resolve("reverse").get({
			"w": width, "width": width,
			"h": height, "height": height,
		})
		if reverse: stream = StringIO(reverseEvery(self.rpl.rom.read(bytes), reverse))
		else: stream = StringIO(self.rpl.rom.read(bytes))

		leftovers, data, prev = ["", 0], [], 0
		for i in helper.range(numPixels):
			data.append(pixels[i % len(pixels)].read(stream, palette, leftovers))
			tmp = padfunc(i, prev, leftovers, stream=stream)
			if tmp is not None:
				#print "Skipping %i bytes." % tmp
				stream.seek(tmp, 1)
				prev = stream.tell()
			#endif
		#endfor

		# Paste to image
		self.image.putdata(data)

		# Transform resultant image by read.
		# Since this is confusing, here's a full readout:
		# LRUD: Nothing
		# LRDU: FLIP_TOP_BOTTOM
		# RLUD: FLIP_LEFT_RIGHT
		# RLDU: FLIP_TOP_BOTTOM, FLIP_LEFT_RIGHT
		# UDLR: ROTATE_270, FLIP_TOP_BOTTOM
		# UDRL: ROTATE_90
		# DULR: ROTATE_270
		# DURL: ROTATE_90, FLIP_TOP_BOTTOM
		primary, secondary = self.resolve("read").ids()
		# if xxDU
		if secondary == 3: self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
		# if xxLR
		elif secondary == 0: self.image = self.image.transpose(Image.ROTATE_270)
		# if xxRL
		elif secondary == 1: self.image = self.image.transpose(Image.ROTATE_90)
		# if RLxx
		if primary == 1: self.image = self.image.transpose(Image.FLIP_LEFT_RIGHT)
		# if UDLR or DURL
		elif primary - secondary == 2: self.image = self.image.transpose(Image.FLIP_TOP_BOTTOM)
	#enddef

	def len(self, numPixels=None, padfunc=None, pixels=None):
		if numPixels is None or padfunc is None:
			width, height = tuple(self.list("dimensions", "number"))
			numPixels = width * height
			padfunc = self.padfuncDef(width, height)
		#endif
		prev, bytes, leftovers = 0, 0, ["", 0]
		pixels = pixels or self.list("pixel")
		# TODO: Make more efficient for repeated rows or uniform pixel size...
		for i in helper.range(numPixels):
			pixel = pixels[i % len(pixels)]
			bytes += pixel.bytes
			leftovers[1] += pixel.extraBits
			if leftovers[1] >= 8:
				bytes += 1
				leftovers[1] -= 8
			#endif
			tmp = padfunc(i, prev, leftovers, bytes)
			if tmp is not None:
				bytes += tmp
				prev = bytes
			#endif
		#endfor
		#bytes = bytes * numPixels + int(ceil(extraBits * numPixels / 8))
		return bytes
	#enddef
#endclass

################################################################################
##################################### Types ####################################
################################################################################

#PIXEL = 0
class Pixel(rpl.String):
	typeName = "pixel"

	specification = re.compile(r'(\d+)([bBxX])([rgbRGBhslHSLwWaAi0]+)')

	def set(self, data, bigEndian=True):
		"""
		Format: type desc
		type:
		  0x or x for hexadecimal, #x for number of nibbles
		  0b or b for binary, #b for number of bits
		desc: [rgbRGBhslHSLwWaAi0]+
		Each entry in desc represents the number of bits given by type.
		Full data is read, same bits are masked and concatenated then interpreted
		by the given endian.
		Lower case letters are the inverse of the uppercase versions. ie. R is
		reddest at 1 and r is reddest at 0. The special case being i.
		Meanings:
		 * Red
		 * Green
		 * Blue
		 * Hue
		 * Saturation
		 * Lightness
		 * White
		 * Alpha
		 * Index in a palette
		 * 0 is ignored
		"""
		rpl.String.set(self, data)
		self.source = self.data
		self.bigEndian = bigEndian

		tokens = Pixel.specification.match(self.data)
		if not tokens: raise RPLError("Invalid pixel format.")
		self.type = tokens.group(2)
		self.bits = (lambda(x): (1 if tokens.group(2) in "bB" else 4)*x)(
			max(int(tokens.group(1)), 1)
		)
		self.format = tokens.group(3)

		# Read this many bytes from the stream
		self.bytes = int(len(self.format) * self.bits / 8)
		self.extraBits = len(self.format) * self.bits % 8

		# Does a pixel fit perfectly within the certain number of bytes
		#self.even = (len(self.format) * self.bits) & 0x7 == 0

		# Expand the format
		self.expanded = ""
		for x in self.format: self.expanded += x * self.bits

		# Which "group" this is using (RGBA?, HSLA?, WA?, I)
		rgb = helper.oneOfIn("rRgGbB", self.format)
		hsl = helper.oneOfIn("hHsSlL", self.format)
		ww = helper.oneOfIn("wW", self.format)
		index = "i" in self.format
		if int(rgb) + int(hsl) + int(ww) + int(index) > 1:
			raise RPLError("Invalid pixel format, must only use one group.")
		#endif
		if rgb:   self.group = 0
		if hsl:   self.group = 1
		if ww:    self.group = 2
		if index: self.group = 3
		self.alpha = helper.oneOfIn("aA", self.format)

		self.max = {}
		for x in "RGBHSLWAI":
			self.max[x] = (1 << (self.expanded.count(x.lower()) + self.expanded.count(x))) - 1
		#endif
	#enddef

	def __unicode__(self):
		return (
			u"%ix" % (self.bits >> 2)
			if self.type in "xX" else
			u"%ib" % self.bits
		) + self.format
	#enddef

	def write(self, stream, palette, leftovers, pixel):
		"""
		leftovers: number of bits
		"""
		#global PIXEL
		r, g, b, a = pixel
		val  = {
			"R": int(round(r * self.max["R"] / 255)) if self.max["R"] else 0,
			"G": int(round(g * self.max["G"] / 255)) if self.max["G"] else 0,
			"B": int(round(b * self.max["B"] / 255)) if self.max["B"] else 0,
			# TODO: Calc HSL values
			# Silently ensure a grayscale value
			"W": int(round((r + b + g) / 3 * 255 / self.max["W"])) if self.max["W"] else 0,
			"A": int(round(a * 255 / self.max["A"])) if self.max["A"] else 0,
		}
		if self.max["I"]:
			try: val["I"] = palette.indexOf((r, g, b, a))
			except KeyError:
				try: val["I"] = palette.indexOf((r, g, b, 0xff))
				except KeyError:
					# TODO: Search for most similar color
					raise RPLError("No entry in palette for #%02x%02x%02x.%i%%." % (r, g, b, a * 100 / 255))
				#endtry
			#endtry
		else: val["I"] = 0

		mask = {}
		for k, x in self.max.iteritems(): mask[k] = (x + 1) >> 1
		bytes, bits = [0], 8 - (leftovers + 1)
		for x in self.expanded[::-1]:
			if bits == -1:
				bytes.insert(0, 0)
				bits = 7
			#endif
			if x != "0":
				u = x.upper()
				bit = 1 if val[u] & mask[u] else 0
				if x in "rgbhslwa": bit ^= 1
				bytes[0] |= bit << bits
			#endif
			bits -= 1
			mask[u] >>= 1
		#endfor
		if bits == -1: bits = 0
		else: bits = 8 - (bits + 1)

		#print "Pixel [%i,%i] starting from $%06x.%i" % (PIXEL % 71, int(PIXEL / 71), stream.tell() - (1 if leftovers else 0), leftovers),
		#PIXEL += 1
		if leftovers:
			stream.seek(-1, 1)
			lastChar = ord(stream.read(1))
			stream.seek(-1, 1)
			bytes[0] |= lastChar
		#endif
		bytes = "".join(map(chr, bytes))
		stream.write(bytes)
		#print "Writing %i.%i bytes. #%02x%02x%02x.%i%% Data: %s" % (len(bytes) - (1 if bits or leftovers else 0), bits + (8 - leftovers if leftovers else 0), r, g, b, a * 100 / 255, "".join(["%02x" % ord(c) for c in bytes]))

		return bits
	#enddef

	def read(self, stream, palette, leftovers):
		"""
		leftovers: (data, number of bits)
		"""
		global PIXEL
		values = {
			"R": 0,
			"G": 0,
			"B": 0,
			"H": 0,
			"S": 0,
			"L": 0,
			"W": 0,
			"A": 0,
			"I": 0,
		}

		#print "Pixel [%i,%i] starting from $%06x.%i" % (PIXEL % 71, int(PIXEL / 71), stream.tell(), leftovers[1]),
		#PIXEL += 1
		if leftovers[1]:
			bytes = leftovers[0] + stream.read(self.bytes + (1 if leftovers[1] < self.extraBits else 0))
			byte = 0
			mask = 1 << (leftovers[1] - 1)
		else:
			bytes = stream.read(self.bytes + (1 if self.extraBits else 0))
			byte = 0
			mask = 0x80
		#endif

		curbyte = ord(bytes[byte])
		for x in self.expanded:
			if x != "0":
				bit = 1 if curbyte & mask else 0
				if x in "rgbhslwa": bit ^= 1
				x = x.upper()
				values[x] = values[x] << 1 | bit
			#endif
			mask >>= 1
			if mask == 0:
				byte += 1
				mask = 0x80
				try: curbyte = ord(bytes[byte])
				except IndexError: curbyte = None
			#endif
		#endfor

		if mask == 0x80: leftovers[0], leftovers[1] = "", 0
		else:
			leftovers[0], leftovers[1] = bytes[byte], {
				         0x40: 7, 0x20: 6, 0x10: 5,
				0x08: 4, 0x04: 3, 0x02: 2, 0x01: 1,
			}[mask]
		#endif

		# Make them relative to max values
		for x in "RGBHSLWA":
			if self.max[x]: values[x] = int(round(values[x] * 255 / self.max[x]))
		#endfor

		a = 0xff
		if self.group == 0: r, g, b = values["R"], values["G"], values["B"]
		#elif self.group == 1: TODO
		elif self.group == 2: r, g, b = values["W"], values["W"], values["W"]
		elif self.group == 3: r, g, b, a = palette[values["I"]]
		if self.alpha: a = values["A"]

		#print "#%02x%02x%02x.%i%%" % (r, g, b, a * 100 / 255)
		return (r, g, b, a)
	#enddef
#endclass

class Color(rpl.Named, rpl.Number):
	typeName = "color"

	names = {
		"black":       0x00000000,
		"white":       0x00ffffff,
		"red":         0x00ff0000,
		"blue":        0x0000ff00,
		"green":       0x000000ff,
		"yellow":      0x00ffff00,
		"magenta":     0x00ff00ff,
		"pink":        0x00ff00ff,
		"cyan":        0x0000ffff,
		"gray":        0x00a5a5a5,
		"grey":        0x00a5a5a5,
		"transparent": 0xff000000,
	}

	def set(self, data):
		if type(data) in [int, long]:
			if data & ~0xffffffff: raise RPLError("Colors must be 3-4 byte values.")
			else: self.data = data
		elif type(data) in [list, tuple]:
			self.data = (
				(data[0] & 0xff) << 16 |
				(data[1] & 0xff) << 8 |
				(data[2] & 0xff)
			)
			if len(data) == 4: self.data |= (255 - (data[3] & 0xff)) << 24
		else: rpl.Named.set(self, data, ["int", "long", "list", "tuple"])
	#enddef

	def __unicode__(self):
		return rpl.Named.__unicode__(self, "$%06x")
	#enddef

	def tuple(self):
		return (
			(self.data & 0x00ff0000) >> 16,
			(self.data & 0x0000ff00) >> 8,
			(self.data & 0x000000ff),
			255 - ((self.data & 0xff000000) >> 24),
		)
	#enddef
#endclass
