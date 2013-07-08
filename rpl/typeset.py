#-*- coding:utf-8 -*-
#
# Copyright (C) 2013 Sapphire Becker (http://logicplace.com)
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

import rpl, std, helper, os
import Image, ImageFont

def register(rpl):
	# Like a forced lib entry. std must be loaded for color type.
	std.register(rpl)

	rpl.registerStruct(Font)
	rpl.registerStruct(TypeSet)
#enddef

def printHelp(moreInfo=[]):
	helper.genericHelp(globals(), moreInfo,
		"The typeset library allows you to easily write text onto an image "
		"by means of either a self-defined bitmap font or a font file.", "typeset", [
			# Structs
			Font, Char, Charset,
			TypeSet, Text
		]
	)
#enddef

class Font(rpl.RPLStruct):
	"""
	Define a font for use with typesetting.
	This is a sliced bitmap.
	"""
	typeName = "font"

	def __init__(self, top, name, parent=None):
		rpl.RPLStruct.__init__(self, top, name, parent)

		self.bmp = {}
	#enddef

	def register(self):
		self.registerKey("file", "path")
		self.registerKey("spacing", "number", "0")
		self.registerKey("backspace", "number", "0")
		self.registerKey("vertical", "string:(top, middle, base, bottom)", "base")
		self.registerKey("transparent", "color", "transparent")
		self.registerStruct(Char)
		self.registerStruct(Charset)
	#enddef

	def prepare(self, folder):
		if not self.bmp:
			filename = self.resolve("file").get(folder)
			img = Image.open(filename).convert("RGBA")

			# Convert color to transparency.
			transparent = self.resolve("transparent").tuple()
			if transparent[3] != 0:
				pixdata = img.load()
				for y in xrange(img.size[1]):
					for x in xrange(img.size[0]):
						if pixdata[x, y] == transparent:
							pixdata[x, y] = (0, 0, 0, 0)
						#endif
					#endfor
				#endfor
			#endif

			# Slice a font from an image
			for x in self:
				x.slice(img, self.bmp)
			#endfor
			del img
		#endif
	#enddef

	def render(self, img, text, settings):
		# Note that here, img is a Share of type ImageFile.
		vert = self["vertical"].string()
		if "spacing" in settings:
			space = settings["spacing"] - settings["backspace"]
		else:
			space = self["spacing"].number() - self["backspace"].number()
		#endif
		bg = settings["bg"]
		maxn, x, y, width, height, sub = 0, 0, 0, 0, 0, 0
		if vert == "base":
			# Precalculate maximum base.
			for c in text:
				c = self.bmp[c]
				maxn = max(maxn, c[3])
				width += c[1] + space
				height = max(height, c[2])
				sub = max(sub, c[2] - c[3])
			#endfor
			width -= space
			height += sub

			# Render text.
			textimg = Image.new("RGBA", (width, height))
			for c in text:
				c = self.bmp[c]
				#      _ Max base (height/base of A (3))
				#   /\  |     ] y offset: maxn - p.base (2) = 1
				#  /=\  |  |\
				# /  \ _|  |/ __ Base
				#          |
				textimg.paste(c[0], (x, y + maxn - c[3]), c[0])
				x += c[1] + space
			#endfor
		elif vert == "top":
			# Find width and max height.
			for c in text:
				c = self.bmp[c]
				width += c[1] + space
				height = max(height, c[2])
			#endfor
			width -= space

			# Render text.
			textimg = Image.new("RGBA", (width, height))
			for c in text:
				c = self.bmp[c]
				textimg.paste(c[0], (x, y), c[0])
				x += c[1] + space
			#endfor
		elif vert == "middle":
			# Precalculate maximum middle.
			for c in text:
				c = self.bmp[c]
				width += c[1] + space
				height = max(height, c[2])
				maxn = max(maxn, c[2] / 2)
			#endfor
			width -= space

			# Render text.
			textimg = Image.new("RGBA", (width, height))
			for c in text:
				c = self.bmp[c]
				textimg.paste(c[0], (x, y + maxn - (c[2] / 2)), c[0])
				x += c[1] + space
			#endfor
		elif vert == "bottom":
			# Precalculate maximum height.
			for c in text:
				c = self.bmp[c]
				width += c[1] + space
				height = max(height, c[2])
				maxn = max(maxn, c[2])
			#endfor
			width -= space

			# Render text.
			textimg = Image.new("RGBA", (width, height))
			for c in text:
				c = self.bmp[c]
				textimg.paste(c[0], (x, y + maxn - c[2]), c[0])
				x += c[1] + space
			#endfor
		#endif

		box = settings["box"]
		bg = Image.new("RGBA", (box[2], box[3]))
		bg.paste(settings["bg"])

		pl, pt = settings["padleft"], settings["padtop"]
		effwidth = width - pl - settings["padright"]
		effheight = height - pt - settings["padbottom"]

		# Set position in bg by alignment.
		align, valign = settings["align"], settings["valign"]
		if align == "left": x = pl
		elif align == "center": x = pl + effwidth / 2 - width / 2
		elif align == "right": x = pl + effwidth - width

		if valign == "top": y = pt
		elif valign == "middle": y = pt + effheight / 2 - height / 2
		elif valign == "right": y = pl + effheight - height

		# Paste text into bg.
		bg.paste(textimg, (x, y), textimg)

		# Paste bg into img.
		img.addImage(bg, box[0], box[1])
	#enddef
#endclass

class Char(rpl.RPLStruct):
	"""
	Describe one character in a font.
	"""
	typeName = "char"

	def register(self):
		self.registerKey("c", "string")
		# [L, T, W, H]
		self.registerKey("box", "[number, number, number, number]")
		# Should default to height, so leave it an empty string for that dynamicness.
		self.registerKey("base", "number", "")
		self.registerVirtual("char", "c")
		self.registerVirtual("bounds", "box")
	#enddef

	def slice(self, img, bmp):
		c = self["c"].string()
		if c in bmp:
			raise rpl.RPLError('Redeclaration of character "%s" in font "%s"' % (c, self.parent.name))
		#endif
		x, y, width, height = tuple([x.number() for x in self["box"].list()])
		tmp = img.crop((x, y, x + width, y + height))
		tmp.load()
		bmp[c] = [
			tmp, width, height,
			height if self["base"].get() == "" else self["base"].number()
		]
	#enddef
#endclass

class Charset(rpl.RPLStruct):
	"""
	Describe a set of characters predictably positioned in a font.
	"""
	typeName = "charset"

	def register(self):
		self.registerKey("set", "string")
		self.registerKey("dimensions", "[number, number]")
		self.registerKey("spacing", "number", "0")
		self.registerKey("start", "[number, number]", "[0, 0]")
		# Should default to height, so leave it an empty string for that dynamicness.
		self.registerKey("base", "number", "")
	#enddef

	def slice(self, img, bmp):
		left, top = tuple([x.number() for x in self["start"].list()])
		width, height = tuple([x.number() for x in self["dimensions"].list()])
		spacing = self["spacing"].number()
		base = None if self["base"].get() == "" else self["base"].number()
		for c in self["set"].string():
			if c in bmp:
				raise rpl.RPLError('Redeclaration of character "%s" in font "%s"' % (c, self.parent.name))
			#endif
			tmp = img.crop((left, top, left + width, top + height))
			tmp.load()
			bmp[c] = [tmp, width, height, height if base is None else base]
			left += width + spacing
		#endfor
	#enddef
#endclass

class TypeSet(std.Graphic):
	"""
	Set and format text on an image.
	"""
	typeName = "typeset"

	def register(self, typeset=True):
		# Text subclass won't want to register these.
		if typeset:
			std.Graphic.register(self)
			self.registerStruct(Text)
		#endif
		self.registerKey("on", "string:(import, export)", "import")
		self.registerKey("font", "reference|path")
		self.registerKey("align", "string:(left, center, right)", "left")
		self.registerKey("valign", "string:(top, middle, bottom)", "top")
		self.registerKey("padleft", "number", "")
		self.registerKey("padright", "number", "")
		self.registerKey("padtop", "number", "")
		self.registerKey("padbottom", "number", "")
		# All | [Horizontal, Vertical] | [L, R, T, B]
		# "padding" is overwriten by specific entries.
		self.registerKey("padding", "number|[number, number]|[number, number, number, number]", "0")
		self.registerKey("bg", "color", "transparent")
		self.registerVirtual("paddingleft", "padleft")
		self.registerVirtual("paddingright", "padright")
		self.registerVirtual("paddingtop", "padtop")
		self.registerVirtual("paddingbottom", "padbottom")
		self.registerVirtual("background", "bg")

		# Keys more or less specific to non-sliced fonts.
		self.registerKey("size", "number", "10")
	#enddef

	def apply(self, folder):
		if self["font"].reference():
			for text in self:
				font = text["font"].pointer()
				font.prepare(folder)

				# Setup padding.
				padding = [
					text["padleft"].get(),
					text["padright"].get(),
					text["padtop"].get(),
					text["padbottom"].get(),
				]
				try: pad = self.number("padding")
				except rpl.RPLBadType:
					pad = self.list("padding")
					if len(pad) == 2:
						if padding[0] == "": padding[0] = pad[0].number()
						if padding[1] == "": padding[1] = pad[0].number()
						if padding[2] == "": padding[2] = pad[1].number()
						if padding[3] == "": padding[3] = pad[1].number()
					else:
						if padding[0] == "": padding[0] = pad[0].number()
						if padding[1] == "": padding[1] = pad[1].number()
						if padding[2] == "": padding[2] = pad[2].number()
						if padding[3] == "": padding[3] = pad[3].number()
					#endif
				else:
					if padding[0] == "": padding[0] = pad
					if padding[1] == "": padding[1] = pad
					if padding[2] == "": padding[2] = pad
					if padding[3] == "": padding[3] = pad
				#endtry

				font.render(
					self.rpl.share(text.resolve("file").get(folder), std.ImageFile),
					text.string(), {
						"box": [x.number() for x in text["box"].list()],
						"align": text["align"].string(),
						"valign": text["valign"].string(),
						"padleft": padding[0],
						"padright": padding[1],
						"padtop": padding[2],
						"padbottom": padding[3],
						"bg": text["bg"].tuple()
					}
				)
			#endfor
		else:
			# Load a font file..
			filename = self["font"].string()
			ext = os.path.splitext(filename)[1][1:].lower()
			try: self.font = ImageFont.load(filename)
			except IOError as err1:
				try: self.font = ImageFont.truetype(filename, self["size"].number())
				except IOError as err2:
					raise RPLError("Could not load font %s, %s, %s." % (filename, err1.args[0], err2.args[0]))
				#endtry
			#endtry

			# Draw text onto image
		#endif
	#enddef

	def importPrepare(self, rom, folder):
		if self.get("on") == "import": self.apply(folder)
	#enddef

	def exportData(self, rom, folder):
		if self.get("on") == "export": self.apply(folder)
	#enddef
#endclass

class Text(TypeSet):
	"""
	Describe the text to set on the image.
	"""
	typeName = "text"

	def __init__(self, top, name, parent=None):
		TypeSet.__init__(self, top, name, parent)
		self.unmanaged = False
	#enddef

	def register(self):
		TypeSet.register(self, False)
		self.registerKey("text", "string", "")
		self.registerKey("textfile", "string", "")
		# [L, T, W, H]
		self.registerKey("box", "[number, number, number, number]")
	#enddef

	def basic(self):
		if self.get("textfile"): return rpl.String(helper.readFrom(self.get("textfile")))
		elif self.get("text"): return rpl.String(self.get("text"))
		else: raise RPLError("%s has no text write." % self.name)
	#enddef
#endclass
