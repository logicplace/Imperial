#!/usr/bin/env python
#-*- coding:utf-8 -*-

import sys
import os
import codecs

sBaseDir = ""
if "GFXCHGR_DIR" in os.environ: sBaseDir = os.environ["GFXCHGR_DIR"]+"/"
if sBaseDir: sys.path.append(sBaseDir)

import re
import Image
from PosIdxPair import PosIdxPair
from rpl import *
from clargs import clargs
from textwrap import dedent

def error(s,r=False):
	sys.stderr.write(str(s)+"\n")
	return r
#enddef

def verror(sKey,sErr):
	return error("Value error %s: %s" % (sKey,sErr))
#enddef

def normpath(path):
	if os.sep == "/": return path.replace("\\","/")
	elif os.sep == "\\": return path.replace("/","\\")
	else: return re.sub(r'[/\\]',os.sep,path)
#endif

def eopen(path,method,bin=False):
	path = normpath(path)
	
	sDir = os.path.dirname(path)
	try: os.mkdir(sDir)
	except: pass
	if type(method) not in [str,unicode]: return method.open(path)
	elif bin: return open(path,method)
	return codecs.open(path,encoding='utf-8',mode=method)
#enddef

dCustomType = {}
def main():
	global dCustomType
	lDebug = False
	
	clArgs = clargs([
		 [['h','?'], "help", 0, False, None]
		,['x', "export", 0, False, "Export graphics from the ROM"]
		,['i', "import", 0, False, "Import graphics via the descriptor"]
		,['t', "template", 0, False, "Generate a descriptor template"]
		,['d', "debug", 1, None, None]
		,['r', "romless", 0, False, "Skip validation"]
		,['f', "format", 1, None, "Provide format name (Default: Uses file extension)"]
		,['m', "makefile", 0, False, "Make ROM file if it doesn't exist"]
		,['b', "binary", "rmf", None, "Compiling to binary instead of a ROM, same as -rmf"]
		,['d', "define", 2, None, "Define a value that can be referenced by @Defs.name\n"\
			+"Format is -d name value[:type]\nDefault type is string"
		]
	]).parse()
	
	lDebug = clArgs.debug
	
	if clArgs.help:
		print(("%s v8 by Wa (logicplace.com)\n" % clArgs[0])
			+"Modify graphics in a Pokemon Mini ROM easily.\n"
			+("Usage: %s [OPTIONS] ROM_FILE DESCRIPTOR [STRUCTs]\n" % clArgs[0])
			+"Structs are what structs to behave on only. If nothing's passed assume all.\n"
			+"Options:\n"
			+str(clArgs)
		)
		return 0
	#endif
	
	# Open ROM
	try: hRom = eopen(clArgs[1],"r+b",True)
	except:
		if clArgs.makefile:
			try:
				eopen(clArgs[1],"w").close()
				hRom = eopen(clArgs[1],"r+b",True)
			except: return error("Could not create ROM file.",1)
		else: return error("Could not open ROM.",1)
	#endtry
	
	sRomFileName,sRomExt = re.match(r'(?:.*/|^)(.+?)(?:\.(.*))?$',clArgs[1]).groups()
	
	# TODO: Use __import__ instead
	# Load module
	try:
		hMod = eopen("%sstd.py" % sBaseDir,"rb",True)
		exec(hMod.read()) in globals() 
		hMod.close()
		hMod = eopen("%s%s.py" % (sBaseDir,clArgs.format[0] or sRomExt),"rb",True)
		exec(hMod.read()) in globals() 
		hMod.close()
	except:
		error("Could not load handler module.",2)
		raise
	#endif
	
	# Get info from the ROM
	sRomId,sRomName = GetROMInfo(hRom)
	
	# Open descriptor
	try:
		if clArgs.template: hRpl = eopen(clArgs[2],"w")
		else: hRpl = eopen(clArgs[2],"r")
	except: return error("Could not open descriptor.",3)
	
	sFocus = clArgs[3] if len(clArgs) > 3 else None
	
	try:
		# Make a template?
		if clArgs.template:
			hRpl.write(dedent("""\
				ROM {
					id: "%s"
					name: "%s"
				}
				tilemap {
					base: $xxxxxx
					file: %s-tiles.bmp
					tile {
						position: [0,0]
						index: 0
					}
				}
				spritemap {
					base: $xxxxxx
					file: %s-sprites.bmp
					sprite {
						position: [0,0]
						index: 0
					}
				}
				""" % (sRomId,sRomName,sRomFileName,sRomFileName)
			))
		elif clArgs.export or clArgs["import"]:
			# Copy std into main
			for x in dStdAllowed:
				if x in dAllowed:
					for y in dStdAllowed[x]:
						if y not in dAllowed[x]: dAllowed[x][y] = dStdAllowed[x][y]
					#endfor
				else: dAllowed[x] = dStdAllowed[x]
			#endfor
			for x in dStdCustomType:
				if x not in dCustomType: dCustomType[x] = dStdCustomType[x]
			#endfor
			
			rpl = RPL(dAllowed,dCustomType,clArgs.define,hRpl)
			if not rpl: raise Exception(4)
			
			if not clArgs.romless:
				# Find the ROM struct and verify data
				if "ROM" in rpl:
					rplROM = rpl.ROM
					if sRomId != rplROM["id"] and sRomId not in rplROM["id"]:
						error("Game ID does not match. Got \"%s\" Expected%s: %s" % (
							sRomId," one of" if type(rplROM["id"]) is list else "",rplROM["id"]
						))
						sYN = ""
						while not re.match(r'[yn]|yes|no',sYN,re.I):
							sYN = raw_input("Continue (y/n)? ")
						#endwhile
						if re.match(r'no?',sYN,re.I): raise Exception(5)
					#endif
					if rplROM["name"] is not None and sRomName != rplROM["name"] and sRomName not in rplROM["name"]:
						error("Game name does not match. Got \"%s\" Expected%s: %s" % (
							sRomId," one of" if type(rplROM["name"]) is list else "",rplROM["name"]
						))
						sYN = ""
						while not re.match(r'[yn]|yes|no',sYN,re.I):
							sYN = raw_input("Continue (y/n)? ")
						#endwhile
						if re.match(r'no?',sYN,re.I): raise Exception(5)
					#endif
				else: error("Warning: No verification performed.")
			#endif
			
			# For exporting
			def TransformEX(info,im):
				# Flips
				try:
					if info.flip: im = im.transpose(Image.FLIP_TOP_BOTTOM)
				except: pass
				try:
					if info.mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
				except: pass
				
				try:
					# Rotate
					iRotate = info.rotate
					if iRotate != 0:
						im = im.transpose([
							Image.ROTATE_270,
							Image.ROTATE_180,
							Image.ROTATE_90
						][iRotate-1])
					#endif
				except: pass
				
				return im
			#enddef
			
			# For importing
			def TransformIM(info,im):
				# Rotate
				try:
					iRotate = info.rotate
					if iRotate != 0:
						im = im.transpose([
							Image.ROTATE_90,
							Image.ROTATE_180,
							Image.ROTATE_270
						][iRotate-1])
					#endif
				except: pass
				
				# Flips
				try:
					if info.mirror: im = im.transpose(Image.FLIP_LEFT_RIGHT)
				except: pass
				try:
					if info.flip: im = im.transpose(Image.FLIP_TOP_BOTTOM)
				except: pass
				
				return im
			#enddef
			
			dFiles={}
			dTypeCount={}
			def xxport(st,bFocusChild=False):
				if st._name is None:
					if st._type not in dTypeCount: dTypeCount[st._type] = 0
					else: dTypeCount[st._type] += 1
					st._name = st._type + str(dTypeCount[st._type])
				#endif
				#print "<%s %s>" % (st._type,st._name)
				bFocusOK = not sFocus or st._name == sFocus
				if bFocusOK or bFocusChild or st._type in lIgnoreFocus:
					sFn = stdhandle_create(hRom,st,dFiles) or handle_create(hRom,st,dFiles)
					#print sFn
					if sFn is not None:
						#print(sFn)
						if clArgs.export:
							if not stdhandle_export(hRom,st,TransformEX,dFiles[sFn]):
								handle_export(hRom,st,TransformEX,dFiles[sFn])
							#endif
						else:
							#print("Importing...")
							if not stdhandle_import(hRom,st,TransformEX,dFiles[sFn]):
								#print("With module..")
								handle_import(hRom,st,TransformIM,dFiles[sFn])
							#endif
						#endif
					#endif
				#endif
				for i in st.children(): xxport(i,bFocusOK or bFocusChild)
			#enddef
			
			for st in rpl: xxport(st)
			
			# Save/close all files
			for sI in dFiles:
				try:
					dFiles[sI].save # Ensure it has a save method..kinda
					sNormI = normpath(sI)
					try: os.mkdir(os.path.dirname(sNormI))
					except: pass
					dFiles[sI].save(sNormI)
					#...dFiles[sI].close()?
				except: pass
			#endfor
		else:
			print("Nothing to do.")
		#endif
	except Exception as x:
		raise
		hRom.close()
		hRpl.close()
		if type(x[0]) is int: return x[0]
		else: raise
	#endif
sys.exit(main())
