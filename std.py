#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Standard data type handlers for gfxchgr.py by Wa (logicplace.com) - v7
"""

lIgnoreFocus = ["font","ROM"]

dStdCustomType = {
	"color": [
		(lambda x,i: ((x&0xff)<<16)|(x&0xff00)|((x&0xff0000)>>16)),
		(lambda x,i: ((x&0xff)<<16)|(x&0xff00)|((x&0xff0000)>>16))
	]
}

dStdAllowed = {
	"root": {
		"data": ["struct",False]
		,"font": ["struct",False]
		,"typeset": ["struct",False]
	}
	,"data": {
		"base": ["number",True]
		,"format": ["[string|[string,int]]*",True]
		,"file": ["string",True]
		,"times": ["number",False,1]
		,"export": ["number",False,RPL.static["true"]]
		,"import": ["number",False,RPL.static["true"]]
		,"endian": ["string",False,"little"]
		,"pad": ["string",False,"\x00"]
		,"padleft": ["number",False,RPL.static["false"]]
		,"pretty": ["number",False,RPL.static["false"]]
		,"comment": ["string",False]
	}
	,"font": {
		"file": ["string",True]
		,"spacing": ["number",False,0]
		,"backspace": ["number",False,0]
		,"vertical": ["string",False,"base"] # base, bottom, middle, top
		,"charset": ["struct",False]
		,"chars": ["struct",False]
		,"char": ["struct",False]
	}
	,"charset": {
		"set": ["string",False,
			" !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~"
		]
		,"dimensions": [["number","number"],False]
		,"spacing": ["number",False,0]
		,"start": [["number","number"],False,[0,0]]
		,"chars": ["struct",False]
		,"char": ["struct",False]
		,"base": ["number",False]
	}
	,"chars": {
		"set": ["string",True]
		,"dimensions": [["number","number"],True]
		,"spacing": ["number",False,0]
		,"start": [["number","number"],False,[0,0]]
		,"base": ["number",False]
	}
	,"char": {
		"c": ["string",True]
		,"box": [["number","number","number","number"],False]
		,"position": [["number","number"],False]
		,"size": [["number","number"],False]
		,"base": ["number",False]
	}
	,"typeset": {
		"font": ["string",False,"font0"]
		,"file": ["string",True]
		,"dimensions": [["number","number"],False]
		,"entry": [["number","number"],False]
		,"align": [["string","string"],False,["left","top"]]
		,"padding": [["number","number","number","number"],False,[0,0,0,0]]
		,"paddingleft": ["number",False,0]
		,"paddingright": ["number",False,0]
		,"paddingtop": ["number",False,0]
		,"paddingbottom": ["number",False,0]
		,"import": ["number",False,RPL.static["true"]]
		,"bg": ["number",False,RPL.static["white"]]
		,"colorize": ["[[number,number]]+",False]
		,"mirror": ["number",False,RPL.static["false"]]
		,"flip": ["number",False,RPL.static["false"]]
		,"rotate": ["number",False,0]
		,"text": ["struct",False]
	}
	,"text": {
		"font": ["string",False]
		,"dimensions": [["number","number"],True]
		,"entry": [["number","number"],False]
		,"text": ["string",True]
		,"align": [["string","string"],False]
		,"padding": [["number","number","number","number"],False]
		,"paddingleft": ["number",False]
		,"paddingright": ["number",False]
		,"paddingtop": ["number",False]
		,"paddingbottom": ["number",False]
		,"index": ["number",False]
		,"position": [["number","number"],False]
		,"size": [["number","number"],False]
		,"box": [["number","number","number","number"],False]
		,"colorize": ["[[number,number]]+",False]
		,"mirror": ["number",False]
		,"flip": ["number",False]
		,"rotate": ["number",False]
		,"import": ["number",False]
		,"bg": ["number",False]
	}
}

def EscapeData(data):
	st = ""
	for x in data:
		iChar = ord(x)
		if iChar >= 0x20 and iChar <= 0x7e: st += x
		else: st += "$%02x" % iChar
	#endfor
	return st
#enddef

def Bytes2Num(sBytes,sEndian):
	iNum = 0
	iShift = 0
	for x in sBytes:
		n = ord(x)
		if sEndian == "big": iNum <<= iShift
		else: n <<= iShift
		iNum |= n
		iShift += 8
	#endfor
	return iNum
#enddef

def Unpad(data,info):
	if info.padleft: return data.lstrip(info.pad)
	else: return data.rstrip(info.pad)
#enddef

def ExportData(hROM,info,fTrans,sFile):
	global dCustomType
	if sFile:
		hROM.seek(info.base)
		sExt = sFile[-4:]
		hOut = eopen(sFile,"wb",sExt==".bin")
		
		if info.comment:
			if sExt == ".txt": hOut.write("%s\n"%info.comment)
			elif sExt == ".rpl": hOut.write("#%s\n"%info.comment)
		#endif
		
		bscParents = [[]]
		def addbasic(data):
			bscParents[-1].append(data)
			if type(data) is list: bscParents.append(data)
		#enddef
		
		def popbasic():
			if len(bscParents) > 1: bscParents.pop()
		#enddef
		
		def Format(fmt,nest=0,bEnd=False):
			if type(fmt) is list:
				if len(fmt) == 2 and type(fmt[0]) is str and type(fmt[1]) is int:
					fmt,size = fmt[0],fmt[1]
				else:
					if sExt == ".rpl":
						if info.pretty: hOut.write("[\n")
						else: hOut.write("[")
					#endif
					for i in range(len(fmt)):
						if sExt == ".rpl" and info.pretty: hOut.write("\t"*(nest+1))
						Format(fmt[i],nest+1,i==len(fmt)-1)
					#endfor
					if sExt == ".rpl":
						if info.pretty: hOut.write(("\t"*(nest))+"]\n")
						else: hOut.write("]\n")
					#endif
					return
				#endif
			else: size = 1
			data = hROM.read(size)
			if fmt == "string": pdata = Unpad(data,info)
			elif fmt in ["number","hexnum"]: pdata = Bytes2Num(data,info.endian)
			elif fmt in dCustomType: pdata = dCustomType[fmt][1](data,info)
			addbasic(pdata)
			if sExt == ".bin": hOut.write(str(data))
			elif sExt == ".txt":
				if fmt == "string": hOut.write(data)
				elif fmt == "number": hOut.write(str(pdata))
				elif fmt == "hexnum": hOut.write("%x"%pdata)
				elif fmt in dCustomType: hOut.write(pdata)
				else: return error("Unknown type %s." % fmt)
				hOut.write("\n")
			elif sExt == ".rpl":
				if fmt == "string": hOut.write('"%s"'%EscapeData(pdata))
				elif fmt == "number": hOut.write(str(pdata))
				elif fmt == "hexnum": hOut.write("$%x"%pdata)
				elif fmt in dCustomType:
					if type(pdata) is str: hOut.write('"%s"'%EscapeData(pdata))
					elif type(pdata) is unicode: hOut.write(u'"%s"'%pdata)
					elif type(pdata) is int: hOut.write(str(pdata,info.endian))
					else: return error("Don't know what to do with data.")
				else: return error("Unknown type %s." % fmt)
				#endif
				if info.pretty: hOut.write("\n")
				elif not bEnd: hOut.write(",")
			#endif
		#enddef
		for i in range(info.times):
			addbasic([])
			Format(info.format)
			popbasic()
		#endfor
		
		if info.times == 1: basic = bscParents[0][0]
		else: basic = bscParents[0]
		if type(basic) is list and len(basic) == 1: info._basic = basic[0]
		else: info._basic = basic
		
		hOut.close()
	#endif
	return True
#enddef

def Num2Bytes(iNum,iSize,info):
	mask = 0xFF
	sBytes = ""
	sEndian = info.endian
	for i in range(iSize):
		n = chr((iNum&mask) >> (i*8))
		if sEndian == "big": sBytes = n+sBytes
		else: sBytes += n
		mask <<= 8
	#endfor
	return sBytes
#enddef

def PadString(sStr,iSize,info):
	sPad = info.pad
	sPad = (sPad*iSize)
	if info.padleft: return (sPad+sStr)[-iSize:]
	else: return (sStr+sPad)[0:iSize]
#enddef

def ImportData(hROM,info,fTrans,sFile):
	if "file" in info and info.file:
		sExt = sFile[-4:]
		if sExt == ".bin": hIn = open(sFile,"rb")
		elif sExt == ".txt": hIn = codecs.open(sFile,encoding='utf-8',mode="r")
		elif sExt == ".rpl": hIn = RPL({},dCustomType,sFile)
		
		info.pad = (info.pad or "\x00")
		
		# Remove comment
		if info.comment and sExt == ".txt": hIn.readline()
		
		bscParents = [[]]
		def addbasic(data):
			bscParents[-1].append(data)
			if type(data) is list: bscParents.append(data)
		#enddef
		
		def popbasic():
			if len(bscParents) > 1:bscParents.pop()
		#enddef
		
		tbytes = ""
		
		def Format(fmt,rplp=None):
			bytes = ""
			if type(fmt) is list:
				if len(fmt) == 2 and type(fmt[0]) is str and type(fmt[1]) is int:
					fmt,size = fmt[0],fmt[1]
				else:
					addbasic([])
					for i in range(len(fmt)):
						if len(rplp) > 1:
							tmp = Format(fmt[i],rplp[i])
							if tmp is False: return error("Error in formatting.")
							bytes += tmp
						elif rplp is not None:
							print("Expected list, got %s." % rplp._data)
							return False
						else:
							tmp = Format(fmt[i])
							if tmp is False: return error("Error in formatting.")
							bytes += tmp
						#endif
					#endfor
					popbasic()
					return bytes
				#endif
			else: size = 1
			
			if sExt == ".bin":
				data = hIn.read(size)
				if fmt == "string": addbasic(Unpad(data,info))
				elif fmt in ["number","hexnum"]: addbasic(Bytes2Num(data,info.endian))
				elif fmt in dCustomType: addbasic(dCustomType[fmt][1](data,info))
				bytes += data
			elif sExt == ".txt":
				data = hIn.readline().rstrip("\r\n")
				if fmt == "string":
					addbasic(data)
					bytes += PadString(str(data),size,info)
				elif fmt == "number":
					data = int(data)
					addbasic(data)
					bytes += Num2Bytes(data,size,info)
				elif fmt == "hexnum":
					data = int(data,16)
					addbasic(data)
					bytes += Num2Bytes(data,size,info)
				elif fmt in dCustomType:
					addbasic(data)
					data = dCustomType[fmt][0](data,info)
					if type(data) in [str,unicode]: bytes += PadString(data,size,info)
					elif type(data) is int: bytes += Num2Bytes(data,size,info)
				else: return error("Unknown type %s." % fmt)
			elif sExt == ".rpl":
				rpld = rplp.d(fmt)
				addbasic(rpld)
				if fmt == "string" or (fmt in dCustomType and type(rpld) in [str,unicode]):
					#print rpld
					if type(rpld) in [str,unicode]: bytes += PadString(str(rpld),size,info)
					else:
						print("Expected string, got %s." % rpld)
						return False
					#endif
				elif fmt in ["number","hexnum"] or (fmt in dCustomType and type(rpld) is int):
					if type(rpld) is int: bytes += Num2Bytes(rpld,size,info)
					else:
						print("Expected %s, got %s." % (fmt,rpld))
						return False
					#endif
#				elif fmt in dCustomType:
#					if type(data) in [str,unicode]: bytes += PadString(rpld,size,info)
#					elif type(data) is int: bytes += Num2Bytes(rpld,size,info)
#					else: return error("Don't know what to do with data.")
				else: return error("Unknown type %s." % fmt)
				#endif
			#endif
			return bytes
		#enddef
		
		for i in range(info.times):
			addbasic([])
			tmp = Format(info.format,hIn[i] if sExt == ".rpl" else None)
			if tmp is not False: tbytes += tmp
			else: return error("Error in formatting.")
			popbasic()
		#endfor
		
		if info.times == 1: basic = bscParents[0][0]
		else: basic = bscParents[0]
		if type(basic) is list and len(basic) == 1: info._basic = basic[0]
		else: info._basic = basic
		
		hROM.seek(info.base)
		hROM.write(tbytes)
		if sExt != ".rpl": hIn.close()
	#endif
	return True
#enddef

class Font:
	def __init__(self,info):
		self.vertical = info.vertical
		self.spacing = info.spacing-info.backspace
		self.char = {}
		dCharDesc = {}
		
		def recurse(inf):
			for x in inf.children():
				if x._type == "chars":
					xpos,ypos,w,h,sp = x.start[0],x.start[1],x.dimensions[0],x.dimensions[1],x.spacing
					for ch in x.set:
						dCharDesc[ch] = {
							"l": xpos, "t": ypos
							,"w": w, "h": h
							,"base": x.base or h
						}
						xpos += w+sp
					#endfor
				elif x._type == "char":
					dCharDesc[x.c] = {
						"l":  x.position[0] if x.position else x.box[0]
						,"t": x.position[1] if x.position else x.box[1]
						,"w": x.size[0] if x.size else x.box[2]
						,"h": x.size[1] if x.size else x.box[3]
						,"base": x.base
					}
					if dCharDesc[x.c]["base"] is None:
						dCharDesc[x.c]["base"] = dCharDesc[x.c]["h"]
					#endif
				elif x._type == "charset": recurse(x)
			#endfor
		#enddef
		recurse(info)
		
		im = Image.open(info.file)
		for i in dCharDesc:
			x = dCharDesc[i]
			self.char[i] = {
				"im": im.crop((x["l"],x["t"],x["l"]+x["w"],x["t"]+x["h"]))
				,"base": x["base"]
				,"w": x["w"]
				,"h": x["h"]
			}
			# TODO: Alpha adjustment
		#endfor
	#enddef

	def draw(self,im,info,fTrans):
		# Get the box:
		if "position" in info and info.position:
			box = [
				info.position[0],info.position[1],
				info.size[0] if "size" in info else info.entry[0],
				info.size[1] if "size" in info else info.entry[1]
			]
		elif "index" in info and info.index is not None:
			iPerRow = int(info.dimensions[0]/info.entry[0])
			box = [
				(info.index%iPerRow)*info.entry[0],
				int(info.index/iPerRow)*info.entry[1],
				info.entry[0],info.entry[1]
			]
		elif "box" in info and info.box: box = info.box
		else: return False
		
		# Create image..
		txt = Image.new("RGBA",(box[2],box[3]),(
			(info.bg&0xff0000)>>16,(info.bg&0xff00)>>8,info.bg&0xff,0xff
		))
		
		# Get height and baseline for entire text:
		iMaxHeight,iMaxBase,iTotalWidth = 0,0,0
		for ch in info.text:
			iMaxHeight = max(self.char[ch]["h"],iMaxHeight)
			iMaxBase = max(self.char[ch]["base"],iMaxBase)
			iTotalWidth += self.char[ch]["w"]+self.spacing
		#endfor
		iTotalWidth -= self.spacing
		
		# Align text
		if info.align[0] == "center": pos = int(box[2]/2 - iTotalWidth/2)
		elif info.align[0] == "right": pos = box[2] - iTotalWidth
		else: pos = 0
		if info.align[1] == "middle": yBase = int(box[3]/2 - iMaxHeight/2)
		elif info.align[1] == "bottom": yBase = box[3] - iMaxHeight
		else: yBase = 0
		
		# Add net padding
		pos += info.padding[0]+info.paddingleft-info.padding[1]-info.paddingright
		yBase += info.padding[2]+info.paddingtop-info.padding[3]-info.paddingbottom
		
		
		# Set text
		#print "Drawing \"%s\" at (%i,%i) %ix%i" % (info.text,pos,yBase,iTotalWidth,iMaxHeight)
		for ch in info.text:
			if self.vertical == "top": yOff = 0
			elif self.vertical == "bottom": yOff = iMaxHeight-self.char[ch]["h"]
			else: 
				yOff = iMaxBase-self.char[ch]["base"]
			#print "Drawing %s at (%i,%i)" % (ch,pos,yBase+yOff)
			txt.paste(self.char[ch]["im"],(pos,yBase+yOff),self.char[ch]["im"])
			pos += self.char[ch]["w"]+self.spacing
		#endfor
		
		fTrans(info,txt)
		# TODO: Colorize
		
		im.paste(txt,(box[0],box[1]))
		return True
	#enddef
#endclass

def ImportTypeset(hRom,info,fTrans,font):
	sFn = info.parent().file
	try: im = Image.open(sFn)
	except: im = Image.new("RGBA",(info.dimensions[0],info.dimensions[1]))
	if not font.draw(im,info,fTrans): error("Typesetting failed for %s." % info._type)
	im.save(sFn)
#enddef

def stdhandle_create(hRom,info,dFiles):
	if info._type == "data" and "file" in info:
		dFiles[info.file] = info.file
		return info.file
	elif info._type in ["typeset","text"]:
		return "FONT:"+info.font
	elif info._type == "font":
		sFn = "FONT:"+info._name
		if sFn not in dFiles: dFiles[sFn] = Font(info)
		return sFn
	#endif
#enddef

def stdhandle_export(hROM,info,fTrans,sFile):
	try:
		if "export" in info and info.export:
			{
				"data": ExportData
			}[info._type](hROM,info,fTrans,sFile)
			return True
		#endif
	except:
		if info._type in ["data"]: raise
		else: return False
	#endtry
#enddef

def stdhandle_import(hROM,info,fTrans,sFile):
	try:
		if "import" in info and info["import"]:
			{
				"data": ImportData
				,"text": ImportTypeset
			}[info._type](hROM,info,fTrans,sFile)
			return True
		#endif
	except:
		if info._type in ["data","text"]: raise
		else: return False
	#endtry
#enddef
