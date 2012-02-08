#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Pokemon Mini module for gfxchgr by Wa (logicplace.com) - v8
"""

## Struct defs
dAllowed = {
	"root": {
		"ROM": ["struct",False]
		,"tilemap": ["struct",False]
		,"spritemap": ["struct",False]
		,"tile": ["struct",False]
		,"tiles": ["struct",False]
		,"tile3": ["struct",False]
		,"tile3s": ["struct",False]
		,"sprite": ["struct",False]
		,"sprites": ["struct",False]
		,"sprite3": ["struct",False]
		,"sprite3s": ["struct",False]
	},
	"ROM": {
		"id": ["[string]*",True]
		,"name": ["[pokestr]*",False]
	},
	"tilemap": {
		"base": ["number",False,0]
		,"base1": ["number",False]
		,"base2": ["number",False]
		,"file": ["string",False]
		,"dimensions": ["[number,number]",False]
		,"white": ["color",False,RPL.static["white"]]
		,"black": ["color",False,RPL.static["black"]]
		,"gray": ["color",False,RPL.static["gray"]]
		,"invert": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,RPL.static["false"]]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
		,"map": ["[number|string]+",False]
		,"tile": ["struct",False]
		,"tiles": ["struct",False]
		,"tile3": ["struct",False]
		,"tile3s": ["struct",False]
	},
	"tilemap3": "tilemap",
	"spritemap": {
		"base": ["number",False,0]
		,"base1": ["number",False]
		,"base2": ["number",False]
		,"file": ["string",False]
		,"dimensions": ["[number,number]",False]
		,"white": ["color",False,RPL.static["white"]]
		,"black": ["color",False,RPL.static["black"]]
		,"gray": ["color",False,RPL.static["gray"]]
		,"alpha": ["color",False,RPL.static["cyan"]]
		,"setalpha": ["color",False,RPL.static["magenta"]]
		,"invert": ["number",False,RPL.static["false"]]
		,"inverta": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,RPL.static["false"]]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
		,"sprite": ["struct",False]
		,"sprites": ["struct",False]
		,"sprite3": ["struct",False]
		,"sprite3s": ["struct",False]
	},
	"spritemap3": "spritemap",
	"tile": {
		"position": ["[[number]*,[number]*]",False,[0,0]]
		,"index": ["[number]*",False,0]
		,"dir": ["string",False,"LRUD"]
		,"base": ["number",False,0]
		,"file": ["string",True]
		,"dimensions": ["[number,number]",True]
		,"white": ["color",False,RPL.static["white"]]
		,"black": ["color",False,RPL.static["black"]]
		,"invert": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,RPL.static["false"]]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
	},
	"tiles": "tile",
	"tile3": {
		"position": ["[[number]*,[number]*]",False,[0,0]]
		,"index": ["[number]*",False,0]
		,"dir": ["string",False,"LRUD"]
		,"base1": ["number",True]
		,"base2": ["number",True]
		,"file": ["string",True]
		,"dimensions": ["[number,number]",True]
		,"white": ["color",False,RPL.static["white"]]
		,"black": ["color",False,RPL.static["black"]]
		,"gray": ["color",False,RPL.static["gray"]]
		,"invert": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,RPL.static["false"]]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
	},
	"tile3s": "tile3",
	"sprite": {
		"position": ["[[number]*,[number]*]",False,[0,0]]
		,"index": ["[number]*",False,0]
		,"dir": ["string",False,"LRUD"]
		,"base": ["number",False,0]
		,"file": ["string",True]
		,"dimensions": ["[number,number]",True]
		,"white": ["color",False,RPL.static["white"]]
		,"black": ["color",False,RPL.static["black"]]
		,"alpha": ["color",False,RPL.static["cyan"]]
		,"setalpha": ["color",False,RPL.static["magenta"]]
		,"invert": ["number",False,RPL.static["false"]]
		,"inverta": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,RPL.static["false"]]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
	},
	"sprites": "sprite",
	"sprite3": {
		"position": ["[[number]*,[number]*]",False,[0,0]]
		,"index": ["[number]*",False,0]
		,"dir": ["string",False,"LRUD"]
		,"base1": ["number",True]
		,"base2": ["number",True]
		,"file": ["string",True]
		,"dimensions": ["[number,number]",True]
		,"white": ["color",False,RPL.static["white"]]
		,"black": ["color",False,RPL.static["black"]]
		,"alpha": ["color",False,RPL.static["cyan"]]
		,"setalpha": ["color",False,RPL.static["magenta"]]
		,"gray": ["color",False,RPL.static["gray"]]
		,"invert": ["number",False,RPL.static["false"]]
		,"inverta": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,RPL.static["false"]]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
	},
	"sprite3s": "sprite3"
}

# Map aliases
for sI in dAllowed:
	if type(dAllowed[sI]) is str: dAllowed[sI] = dAllowed[dAllowed[sI]]
#endfor

## Methods ##

### Export Methods ###

def CombineMask(gfx,mask,pal,im,idx):
	# Pixels dir: DULR
	# pal is [white,black,alpha,setalpha]
	data = []
	for y in [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80]:
		for x in range(8):
			data.append(pal[
				(int(bool(ord(mask[x])&y))<<1)
				|int(bool(ord(gfx[x])&y))
			])
		#endfor
	#endfor
	
	tBox=tuple([(0,0,8,8),(8,0,16,8),(0,8,8,16),(8,8,16,16)][idx])
	rg = im.crop(tBox)
	rg.putdata(data)
	im.paste(rg,tBox)
#enddef

def Combine3Mask(gfx1,mask1,gfx2,mask2,pal,im,idx):
	# Pixels dir: DULR
	# pal is [white,black,alpha,setalpha,gray]
	data = []
	for y in [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80]:
		for x in range(8):
			d1 = (
				(int(bool(ord(mask1[x])&y))<<1)
				|int(bool(ord(gfx1[x])&y))
			)
			d2 = (
				(int(bool(ord(mask2[x])&y))<<1)
				|int(bool(ord(gfx2[x])&y))
			)
			if d1 == 0 and d2 == 1\
			or d1 == 1 and d2 == 0: data.append(pal[4])
			else: data.append(pal[d1])
		#endfor
	#endfor
	
	tBox=tuple([(0,0,8,8),(8,0,16,8),(0,8,8,16),(8,8,16,16)][idx])
	rg = im.crop(tBox)
	rg.putdata(data)
	im.paste(rg,tBox)
#enddef

# Take in the file handler, info, transforms function, and base image
def Sprite2Image(hROM,info,fTrans,imBase):
	imSprite = Image.new("RGB",(16,16))
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		hROM.seek(info.base+idx*64) # 16(w)*16(h)*2(d)/8(bpp)
		for i in range(2):
			m1,m2,g1,g2 = hROM.read(8),hROM.read(8),hROM.read(8),hROM.read(8)
			CombineMask(g1,m1,[
				info.white,info.black,
				info.alpha,info.setalpha
			],imSprite,i)
			CombineMask(g2,m2,[
				info.white,info.black,
				info.alpha,info.setalpha
			],imSprite,i+2)
		#endfor
	
		imSprite = fTrans(info,imSprite)
		
		imBase.paste(imSprite,(x*16,y*16))
	#endfor
#enddef

def Sprite32Image(hROM,info,fTrans,imBase):
	imSprite = Image.new("RGB",(16,16))
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		for i in range(2):
			hROM.seek(info.base1+idx*64+i*32) # 16(w)*16(h)*2(d)/8(bpp)
			m11,m21,g11,g21 = hROM.read(8),hROM.read(8),hROM.read(8),hROM.read(8)
			hROM.seek(info.base2+idx*64+i*32) # 16(w)*16(h)*2(d)/8(bpp)
			m12,m22,g12,g22 = hROM.read(8),hROM.read(8),hROM.read(8),hROM.read(8)
			Combine3Mask(g11,m11,g12,m12,[
				info.white,info.black,
				info.alpha,info.setalpha,
				info.gray
			],imSprite,i)
			Combine3Mask(g21,m21,g22,m22,[
				info.white,info.black,
				info.alpha,info.setalpha,
				info.gray
			],imSprite,i+2)
		#endfor
	
		imSprite = fTrans(info,imSprite)
		
		imBase.paste(imSprite,(x*16,y*16))
	#endfor
#enddef

def Tile2Image(hROM,info,fTrans,imBase):
	imTile = Image.new("RGB",(8,8))
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		hROM.seek(info.base+idx*8) # 8(w)*8(h)/8(bpp)
		CombineMask(hROM.read(8),"\x00"*8,[
			info.white,info.black
		],imTile,0)
	
		imTile = fTrans(info,imTile)
	
		imBase.paste(imTile,(x*8,y*8))
	#endfor
#enddef

def Tile32Image(hROM,info,fTrans,imBase):
	imTile = Image.new("RGB",(8,8))
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		hROM.seek(info.base1+idx*8) # 8(w)*8(h)/8(bpp)
		g1 = hROM.read(8)
		hROM.seek(info.base2+idx*8) # 8(w)*8(h)/8(bpp)
		m = "\x00"*8
		Combine3Mask(g1,m,hROM.read(8),m,[
			info.white,info.black,
			info.white,info.black,
			info.gray
		],imTile,0)
	
		imTile = fTrans(info,imTile)
	
		imBase.paste(imTile,(x*8,y*8))
	#endfor
#enddef

def Tilemap2Image(hROM,info,fTrans,imBase,bImport=False):
	if "map" not in info or info.map is None: return
	for i in range(len(info.map)):
		vTile = info.map[i]
		lDimens = info.dimensions
		if type(vTile) is int:
			info.createChild("tile",None,{
				"position": [
					i%lDimens[0],
					int(i/lDimens[0])
				],
				"index": vTile
			})
		elif vTile == "x":
			if bImport: continue
			imTile = fTrans(info,imTile)
			imTile.putdata([0x000000]*64)
			imBase.paste(imTile,(i%lDimens[0]*8,int(i/lDimens[0]*8)))
		elif vTile != "i": pass # Potentially error?
	#endfor
#enddef

### ImportMethods ###

def ColorTuple2Hex(tClr):
	return (tClr[2]<<16)|(tClr[1]<<8)|tClr[0]
#enddef

def UncombineMask(im,pal):
	data = im.getdata()
	
	dCol = {}
	for i in range(len(pal)): dCol[pal[i]] = i
	
	lGfx = [0]*8
	lMask = [0]*8
	i = 0
	for y in [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80]:
		for x in range(8):
			iPx = dCol[ColorTuple2Hex(data[i])]
			if iPx&1: lGfx[x] |= y
			if iPx&2: lMask[x] |= y
			i += 1
		#endfor
	#endfor
	return (''.join(map(chr,lGfx)),''.join(map(chr,lMask)))
#enddef

def Uncombine3Mask(im,pal):
	data = im.getdata()
	
	dCol = {}
	for i in range(len(pal)): dCol[pal[i]] = i
	
	lGfx1 = [0]*8
	lMask1 = [0]*8
	lGfx2 = [0]*8
	lMask2 = [0]*8
	i = 0
	for y in [0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80]:
		mesh = y&0x55 and 0x55 or 0xaa
		for x in range(8):
			iPx = dCol[ColorTuple2Hex(data[i])]
			if iPx&1:
				lGfx1[x] |= y
				lGfx2[x] |= y
			if iPx&2:
				lMask1[x] |= y
				lMask2[x] |= y
			if iPx&4:
				if (1<<x)&mesh: lGfx1[x] ^= y
				else: lGfx2[x] ^= y
			#endif
			i += 1
		#endfor
	#endfor
	return (''.join(map(chr,lGfx1)),''.join(map(chr,lMask1)),
		''.join(map(chr,lGfx2)),''.join(map(chr,lMask2))
	)
#enddef

def Image2Sprite(hROM,info,fTrans,imBase):
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		lCol = [
			info.white,info.black,
			info.alpha,info.setalpha
		]
		x *= 16
		y *= 16
		imSprite = fTrans(info,imBase.crop((x,y,x+16,y+16)))
		TLg,TLm = UncombineMask(imSprite.crop((0,0,8,8)),lCol)
		TRg,TRm = UncombineMask(imSprite.crop((8,0,16,8)),lCol)
		BLg,BLm = UncombineMask(imSprite.crop((0,8,8,16)),lCol)
		BRg,BRm = UncombineMask(imSprite.crop((8,8,16,16)),lCol)
		
		hROM.seek(info.base+idx*64)
		hROM.write(TLm+BLm+TLg+BLg+TRm+BRm+TRg+BRg)
	#endfor
	return True
#enddef

def Image2Sprite3(hROM,info,fTrans,imBase):
	#print "Attempting to write sprite "+info._name
	wr = 0
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		lCol = [
			info.white,info.black,
			info.alpha,info.setalpha,
			info.gray
		]
		x *= 16
		y *= 16
		imSprite = fTrans(info,imBase.crop((x,y,x+16,y+16)))
		TLg1,TLm1,TLg2,TLm2 = Uncombine3Mask(imSprite.crop((0,0,8,8)),lCol)
		TRg1,TRm1,TRg2,TRm2 = Uncombine3Mask(imSprite.crop((8,0,16,8)),lCol)
		BLg1,BLm1,BLg2,BLm2 = Uncombine3Mask(imSprite.crop((0,8,8,16)),lCol)
		BRg1,BRm1,BRg2,BRm2 = Uncombine3Mask(imSprite.crop((8,8,16,16)),lCol)
		
		hROM.seek(info.base1+idx*64)
		hROM.write(TLm1+BLm1+TLg1+BLg1+TRm1+BRm1+TRg1+BRg1)
		hROM.seek(info.base2+idx*64)
		hROM.write(TLm2+BLm2+TLg2+BLg2+TRm2+BRm2+TRg2+BRg2)
	#endfor
	#print "Wrote sprite to %i and %i (%i bytes written)"%(info.base1,info.base2,wr)
	return True
#enddef

# Import tile
def Image2Tile(hROM,info,fTrans,imBase):
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		lCol = [
			info.white,info.black,
			info.white,info.black
		]
		x *= 8
		y *= 8
		imTile = fTrans(info,imBase.crop((x,y,x+8,y+8)))
		Tile = UncombineMask(imTile.crop((0,0,8,8)),lCol)[0]
		
		hROM.seek(info.base+idx*8)
		hROM.write(Tile)
	#endfor
	return True
#enddef

def Image2Tile3(hROM,info,fTrans,imBase):
	for x,y,idx in PosIdxPair(info.position,info.index,info.dir):
		lCol = [
			info.white,info.black,
			info.white,info.black,
			info.gray
		]
		x *= 8
		y *= 8
		imTile = fTrans(info,imBase.crop((x,y,x+8,y+8)))
		Tile = Uncombine3Mask(imTile.crop((0,0,8,8)),lCol)
		
		hROM.seek(info.base1+idx*8)
		hROM.write(Tile[0])
		hROM.seek(info.base2+idx*8)
		hROM.write(Tile[2])
	#endfor
	return True
#enddef

def Image2Tilemap(hROM,info,fTrans,imBase):
	Tilemap2Image(hROM,info,fTrans,imBase,bImport=True)
#enddef

### Custom Type Handlers ###

def UTF82Text(data,sMap,dMap):
	if data is None: return None
	if not dMap:
		for i in range(len(sMap)): dMap[sMap[i]] = chr(i)
	#endif
	if type(data) is not unicode: data = unicode(data.decode("utf8"))
	bytes = ""
	for x in data:
		try: bytes += dMap[x]
		except: pass
	#endfor
	return bytes
#enddef
def Text2UTF8(data,info,sMap):
	if data is None: return None
	data = Unpad(data,info)
	sOut = u""
	for x in data:
		try: sOut += sMap[ord(x)]
		except: sOut += "?"
	return sOut
#enddef

sKatakana = (
	u"\x00"*61
	+u"2 ーアイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
	+u"ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポァィゥェォャュョッ"
)
dKatakana = {}
def UTF82Katakana(data,info):
	global dKatakana,sKatakana
	return UTF82Text(data,sKatakana,dKatakana)
#enddef
def Katakana2UTF8(data,info):
	global sKatakana
	return Text2UTF8(data,info,sKatakana)
#enddef

sSodate = (
	u" あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆらりるれろわをん"
	+u"がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽぁぃぅぇぉゃゅょっ"
	+u"アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
	+u"ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポァィゥェォャュョッ"
	+u"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz,"
	+u"・「」.ー:;(=)?!"
	+u"<&>" # なまえ    
	+u"▂$-%°*☑⧻∭‾─⧶╭╮/\n#"
)
dSodate = {}
def UTF82Sodate(data,info):
	global dSodate,sSodate
	return UTF82Text(data,sSodate,dSodate)
#enddef
def Sodate2UTF8(data,info):
	global sSodate
	return Text2UTF8(data,info,sSodate)
#enddef

sPokestr = (
	u"\x00"*0x20
	+u" !\"#$&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	+u"[￥]^_`"
	+u"abcdefghijklmnopqrstuvwxyz"
	+u"{|}~"
	+u"\x00"*34
	+u"。「」、・ヲァィゥェォャュョッー"
	+u"アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
	+u"゛゜"
)
dPokestr = {}
def UTF82Pokestr(data,info):
	global dPokestr,sPokestr
	return UTF82Text(data,sPokestr,dPokestr)
#enddef
def Pokestr2UTF8(data,info):
	global sPokestr
	return UTF82Text(data,info,sPokestr)
#enddef

### Handlers ###

# Creation handler
def handle_create(hROM,info,dFiles):
	if info._type in ["sprite","tile","sprites","tiles","sprite3","sprite3s","tile3","tile3s","tilemap","spritemap"]\
	and "file" in info and info.file and "dimensions" in info:
		if info._type in ["sprite","sprites","spritemap","sprite3","sprite3s","spritemap3"]: iMul = 16
		else: iMul = 8
		sFn = info.file
		lDmn = info.dimensions
		
		if sFn not in dFiles:
			try: dFiles[sFn] = eopen(sFn,Image)
			except: dFiles[sFn] = Image.new("RGB",(lDmn[0]*iMul,lDmn[1]*iMul))
		#endif
		return sFn
	else: return None
#enddef

# Export handler
def handle_export(hROM,info,fTrans,imBase):
	f = {
		"sprite": Sprite2Image
		,"sprites": Sprite2Image
		,"sprite3": Sprite32Image
		,"sprite3s": Sprite32Image
		,"tile": Tile2Image
		,"tiles": Tile2Image
		,"tile3": Tile32Image
		,"tile3s": Tile32Image
		,"tilemap": Tilemap2Image
	}
	try:
		if "export" in info and info.export:
			return f[info._type](hROM,info,fTrans,imBase)
		#endif
	except:
		if info._type in f: raise
		else: return False
	#endtry
#enddef

# Import handler
def handle_import(hROM,info,fTrans,imBase):
	f = {
		"sprite": Image2Sprite
		,"sprites": Image2Sprite
		,"sprite3": Image2Sprite3
		,"sprite3s": Image2Sprite3
		,"tile": Image2Tile
		,"tiles": Image2Tile
		,"tile3": Image2Tile3
		,"tile3s": Image2Tile3
		,"tilemap": Image2Tilemap
	}
	try:
		if "import" in info and info["import"]:
			return f[info._type](hROM,info,fTrans,imBase)
		#endif
	except:
		if info._type in f: raise
		else: return False
	#endtry
#enddef

# ROM Info
def GetROMInfo(hROM):
	hROM.seek(0x21ac)
	return (hROM.read(4),hROM.read(12).replace("\x00",""))
#enddef

dCustomType = {
	"katakana": ["string",UTF82Katakana,Katakana2UTF8] # Pokedex entries in Puzzle 2
	,"pokestr": ["string",UTF82Pokestr,Pokestr2UTF8] # Names
	,"sodate": ["string",UTF82Sodate,Sodate2UTF8] # Sodate text
}
