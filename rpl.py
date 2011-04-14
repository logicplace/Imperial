#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
RPL Parser class by Wa (logicplace.com) - v8
Part of gfxchgr.py
"""

# TODO: Fix bug that a literal at the end of an array must directly be followed with ] or ,
#       (Should allow you to not have anything and put ] on the next line)

import re
import codecs
from sys import stderr

def error(s,r=False):
	stderr.write(str(s)+"\n")
	return r
#enddef

class RPLRef:
	spec = re.compile(
		r'@?([^.]+)(?:\.([^\[]*))?((?:\[[0-9]+\])*)'
	)
	
	def __init__(self,rpl,ref,tPos):
		self.rpl = rpl
		self.idxs = []
		self.struct,self.key,sIdx = self.spec.match(ref).groups()
		if sIdx: self.idxs = sIdx[1:-1].split("][")
		self.pos = tPos
	#enddef
	
	def __repr__(self):
		return "<RPLRef '%s'>" % str(self)
	#enddef
	
	def __str__(self):
		ret = "@%s" % self.struct
		if self.key: ret += "."+self.key
		if self.idxs: ret += "[%s]" % "][".join(self.idxs)
		return ret
	#enddef
	
	def syntax(self,sErr):
		error("Error in line %i char %i: %s" % (self.pos[0],self.pos[1],sErr))
		if bShowData: error("  <reference %s>" % str(self))
	#enddef
	
	def v(self):
		info = self.rpl[self.struct]
		if self.key:
			if self.key not in info:
				error("Key %s not allowed in %s." % (self.key,self.struct))
				return None
			#endif
			data = info[self.key]
		else:
			data = info.basicVal()
		#endif
		
		for i in range(len(self.idxs)):
			x = self.idxs[i]
			if type(data) is not list: error("Error: Data is not deep enough for this request (%i)" % i)
			if x >= len(data): error("Error: Data is not wide enough for this request (%i)" % x)
			data = data[x]
		#endif
		return data
	#enddef
#endclass

class RPL:
	# Tokenize
	tokenize = re.compile(
		 r'[ \t\r\n]*(?:'          # Whitespace
		+r'"([^"\r\n]*)"|'         # String
		+r'\$([0-9a-fA-F]+)|'      # Hexadecimal number
		+r'([0-9\-:]+)|'           # Number or range (verify syntactically correct range later)
		+r'([a-z]+[0-9]*):|'       # Key
		+r'([{}\[\],])|'           # Flow Identifier
		+r'@([^{}\[\],.\$"#\r\n]+(?:\.[a-z]+[0-9]*)?(?:\[[0-9]+\])*)|' # Reference
		+r'([^{}\[\],\$"#\r\n]+)|' # Unquoted string or struct name/type
		+r'#.*$)'                  # Comment
	,re.M)
	
	number = re.compile(
		r'(?:[0-9]+|[xi](?=:))'   # Must start with a number, or an x or i followed by a :
		+r'(?:'                   # Range split group
		+r'(?:[\-*][0-9]+)?'      # Can match a range or times here
		+r':(?:[0-9]+|[xi](?=:))' # Must match a split, can either be a number or x/i followed by a :
		+r')*'
		+r'(?:[\-*][0-9]+)?'      # To be sure we're able to end in a range
	)
	
	static = {
		 "false":   0
		,"true":    1
		,"black":   0x000000
		,"white":   0xffffff
		,"red":     0xff0000
		,"blue":    0x00ff00
		,"green":   0x0000ff
		,"yellow":  0xffff00
		,"magenta": 0xff00ff
		,"pink":    0xff00ff
		,"cyan":    0x00ffff
		,"gray":    0xa5a5a5
		,"byte":    1
		,"short":   2
		,"long":    4
		,"double":  8
		,"LU":      "LRUD"
		,"LD":      "LRDU"
		,"RU":      "RLUD"
		,"RD":      "RLDU"
		,"UL":      "UDLR"
		,"UR":      "UDRL"
		,"DL":      "DULR"
		,"DR":      "DURL"
	}

	def __init__(self,dAllow,dCustomType,lDefines,vFile=None):
		self.structs = []
		self.root = []
		self.dataonly = None
		self.data = []
		self.allowed = dAllow
		self.types = dCustomType
		self.cur = -1
		self.defs = lDefines
	
		if vFile is not None:
			if type(vFile) is str: vFile = codecs.open(vFile,encoding='utf-8',mode="r")
			self.parse(vFile)
		#endif
	#enddef
	
	def parse(self,hFile):
		self.file = hFile
		lParents = []
		sPotentialStruct = None
		sCurrentKey = None
		rplfile = hFile.read()
		
		def addData(vData,sType,tFilepos=None):
			lData = [vData,sType,tFilepos or filepos()]
			if len(self.structs) == 0:
				if len(lParents) == 0: self.data.append(lData)
				else: lParents[-1].append(lData)
			elif type(lParents[-1]) is list:
				lParents[-1].append(lData)
			elif sCurrentKey and not sCurrentKey in lParents[-1]:
				lParents[-1][sCurrentKey] = lData
			elif sCurrentKey in lParents[-1] and type(lParents[-1][sCurrentKey]) is list:
				lParents[-1][sCurrentKey].append(lData)
			else:
				return syntax(tok,"Unused %s." % sType,rplfile)
			#endif
			return vData
		#enddef
		
		def filepos():
			iPos = tok.start()
			iLineNum = rplfile.count("\n",0,iPos)
			iCharNum = iPos-rplfile.rfind("\n",0,iPos)
			return iLineNum,iCharNum
		#enddef
		
		def syntax(sErr,bShowData=True):
			tTok = tok.groups()
			if   tTok[0]: sType,sTok = "string",tTok[0]
			elif tTok[1]: sType,sTok = "hexnum",tTok[1]
			elif tTok[2]: sType,sTok = "number",tTok[2]
			elif tTok[3]: sType,sTok = "key",tTok[3]
			elif tTok[4]: sType,sTok = "flow",tTok[4]
			elif tTok[5]: sType,sTok = "reference",tTok[5]
			elif tTok[6]: sType,sTok = "literal",tTok[6]
			
			iLineNum,iCharNum = filepos()
	
			error("Error in line %i char %i: %s" % (iLineNum,iCharNum,sErr))
			if bShowData: error("  <%s %s>" % (sType,sTok))
			return False
		#enddef
		
		# Handle CLI defines
		if self.defs:
			dSt = {
				"_type": "static"
				,"_name": "Defs"
				,"_parent": None
			}
			
			self.structs.append(dSt)
			self.root.append(dSt)
			lParents.append(dSt)
			for x in self.defs:
				sCurrentKey,x = x
				lVal,lType = tuple((x.rsplit(":",1)+["string"])[0:2])
				addData(lVal,lType,(0,0))
			#endfor
			sCurrentKey = None
			lParents.pop()
		#endif
		
		for tok in self.tokenize.finditer(rplfile):
			sStr,sHex,sNum,sKey,sFlow,sRef,sLit = tok.groups()
			
			if sLit:
				sLit = sLit.rstrip()
				if len(lParents) == 0 or sCurrentKey is None:
					sPotentialStruct = sLit
				else:
					if sLit in self.static: sLit = self.static[sLit]
					addData(sLit,"literal")
					sCurrentKey = None
				#endif
			elif sFlow:
				if sFlow == "{": # Open struct
					if sPotentialStruct:
						# No more than "TYPE NAME {" !
						lStructHead = sPotentialStruct.split(" ")
						sPotentialStruct = None
						if len(lStructHead) > 2:
							return syntax("Expects only type and name for struct declaration.")
						#endif
						
						if sKey is not None:
							return syntax("Cannot have a struct in a key or list.")
						#endif
						
						if len(self.data) != 0:
							return syntax("Cannot have a struct in a data file.")
						#endif
						
						# Validate struct
						sParentType = lParents[-1]["_type"] if len(lParents) > 0 else "root"
						if ("*" not in self.allowed[sParentType] \
						or self.allowed[sParentType]["*"][0] not in ["struct","all"]) \
						and (lStructHead[0] not in self.allowed[sParentType] \
						or self.allowed[sParentType][lStructHead[0]][0] not in ["struct","all"]):
							return syntax("%s isn't allowed as a substruct of %s." % (
								lStructHead[0],sParentType),False
							)
						#endif
						
						dSt = {
							"_type": lStructHead[0]
							,"_name": lStructHead[1] if len(lStructHead) == 2 else None
							,"_parent": lParents[-1] if len(lParents) > 0 else None
						}
						
						self.structs.append(dSt)
						if len(lParents) == 0: self.root.append(dSt)
						lParents.append(dSt)
					#endif
				elif sFlow == "}": # End struct
					if len(lParents) > 0 and type(lParents[-1]) is dict:
						if sCurrentKey is not None:
							return syntax("Key with no value. (Above here!)",False)
						#endif
						lParents.pop()
					else: return syntax("} without a {.")
				elif sFlow == "[": # Begin list
					tmp = addData([],"list")
					if tmp is False: return False
					lParents.append(tmp)
				elif sFlow == "]": # End list
					if len(lParents) > 0 and type(lParents[-1]) is list:
						if sPotentialStruct:
							addData(sPotentialStruct,"literal")
							sPotentialStruct = None
						#endif
						lParents.pop()
					else:
						return syntax("] without a [.")
					#endif
				elif sFlow == ",": # Separator
					if sPotentialStruct:
						addData(sPotentialStruct,"literal")
						sPotentialStruct = None
					#endif
				#endif
			elif sKey:
				if len(lParents) == 0 or type(lParents[-1]) is not dict:
					return syntax("Key can only be in a struct.")
				#endif
				
				# Validate key
				sParentType = lParents[-1]["_type"]
				if "*" not in self.allowed[sParentType]\
				and (sKey not in self.allowed[sParentType]\
				or self.allowed[sParentType][sKey][0] == "struct"):
					return syntax("%s has no key %s." % (
						sParentType,sKey),False
					)
				#endif
				sCurrentKey = sKey
			elif sRef:
				addData(RPLRef(self,sRef,filepos()),"reference")
				sCurrentKey = None
			elif sStr:
				addData(sStr,"string")
				sCurrentKey = None
			elif sHex:
				addData(int(sHex,16),"hexnum")
				sCurrentKey = None
			elif sNum:
				if not self.number.match(sNum): syntax("Invalid range formatting.")
			
				# Parse number
				lNum = []
				lRanges = sNum.split(":")
				iLine,iChr = filepos()
				for sRange in lRanges:
					lBounds = sRange.split("-")
					lMulti = sRange.split("*")
					if len(lBounds) == 2:
						iL,iR = int(lBounds[0]),int(lBounds[1])
						if iL < iR: lTmpRng = range(iL,iR+1)
						else: lTmpRng = range(iL,iR-1,-1)
						lNum += map((lambda(x): [x,"number",(iLine,iChr)]),lTmpRng)
					elif len(lMulti) == 2:
						iV,iM = int(lMulti[0]),int(lMulti[1])
						lNum += map((lambda(x): [x,"number",(iLine,iChr)]),[iV]*iM)
					else: lNum.append(int(lBounds[0]))
					iChr += len(sRange)+1
				#endfor
			
				if len(lNum) == 1: addData(lNum[0],"number")
				else: addData(lNum,"range")
				sCurrentKey = None
			#endif
			
			if not sLit and sPotentialStruct:
				return syntax("Literal with no purpose: %s"%sPotentialStruct,False)
			#endif
		#endfor
		
		#print self.structs
		
		self.dataonly = bool(len(self.data))
	#enddef
	
	# TODO: Make this use RPLData instead
	def __getitem__(self,idx):
		if type(idx) is int:
			if self.dataonly: return RPLStruct(self,{"_data":self.data[idx]})
			else: return RPLStruct(self,self.root[idx])
		elif idx == "ROM":
			for x in self.root:
				if x["_type"] == "ROM": return RPLStruct(self,x)
			#endfor
			raise IndexError("ROM not found.")
		else:
			for x in self.structs:
				if x["_name"] == idx: return RPLStruct(self,x)
			#endfor
			raise IndexError("Struct \"%s\" not found." % idx)
		#endif
	#enddef
	
	def __getattr__(self,idx): return self.__getitem__(idx)
	
	def __iter__(self): return self
	
	def next(self):
		self.cur += 1
		try: return self.__getitem__(self.cur)
		except:
			self.cur = -1
			raise StopIteration
		#endtry
	#enddef
	
	def __nonzero__(self): return self.dataonly is not None
	def close(self): self.file.close()
	
	def __contains__(self,idx):
		for i in self.structs:
			if i["_type"] == idx: return True
		#endfor
	#enddef
#endclass

# TODO: Make this return RPLData, which also now handles conversion..
class RPLStruct:
	hexesc = re.compile(r'\$([0-9a-fA-F]{2})')
	
	def __init__(self,rpl,struct):
		self.rpl=rpl
		self.struct=struct
	#enddef
	
	def children(self):
		lRet = []
		for i in self.rpl.structs:
			if i["_parent"] == self.struct: lRet.append(RPLStruct(self.rpl,i))
		#endfor
		return lRet
	#enddef
	
	def parent(self): return RPLStruct(self.rpl,self.struct["_parent"])
	
	def createChild(self,sType,sName,dInfo):
		# Convert to tokens
		def Recurse(d):
			if type(d) is list:
				lTmp = []
				for x in d: lTmp.append(Recurse(x))
				return [lTmp,"list",(0,0)];
			elif type(d) in [str,unicode]: return [d,"string",(0,0)];
			elif type(d) in [int,long]: return [d,"number",(0,0)];
		#enddef
		for x in dInfo:
			dInfo[x] = Recurse(dInfo[x])
		#endif
		dInfo["_type"] = sType
		dInfo["_name"] = sName
		dInfo["_parent"] = self.struct
		self.rpl.structs.append(dInfo)
		return RPLStruct(self.rpl,dInfo)
	#enddef
	
	def basicVal(self):
		if "_basic" in self.struct: return self._basic
		else: return self._name
	#enddef
	
	def unescape(self,sStr):
		return self.hexesc.sub((lambda(x):chr(int(x.group(1),16))),sStr).replace("$$","$")
	#enddef
	
	def ty(self,t): self.struct["_type"] = t
	def d(self,t):
		if "_data" in self.struct: 
			self.struct["_type"] = t
			return self._data
		#endif
	#enddef
	
	def __getitem__(self,idx):
		if type(idx) is int:
			if "_data" in self.struct:
				if type(self.struct["_data"]) is list: return RPLStruct(self.rpl,{"_data":self.struct["_data"][idx]})
			else: raise IndexError("Index out of bounds")
		#endif
		tmp,data = None,None
		if idx == "_data":
			data = self.struct["_data"]
		elif idx[0] == "_":
			if idx in self.struct:
				data = self.struct[idx]
				if type(data) in [str,unicode]: return self.unescape(data)
				else: return data
			else: raise IndexError("Private field %s does not exist." % idx)
		else:
			tmp = self.rpl.allowed[self.struct["_type"]]
			allowedIdx = idx
			if idx not in tmp:
				if "*" in tmp: allowedIdx = "*"
				else: raise IndexError("%s not allowed in %s."%(idx,self.struct["_type"]))
			#endif
			try:
				check = self.struct
				default = None
				tmpCh = [idx,"*"]
				while idx not in check:
					t2 = self.rpl.allowed[check["_type"]]
					for ii in tmpCh:
						if default is None and ii in t2 \
						and type(t2[ii]) is list \
						and len(t2[ii]) >= 3:
							default = t2[ii][2]
							break
						#endif
					#endfor
					if not check["_parent"]: break
					check = check["_parent"]
					tmpCh = [idx]
				#endwhile
				data = RPLData(self,check[idx],tmp[allowedIdx][0]).v()
		
#				# Check if it's a reference
#				try:
#					sName = data.name()
#					#print "Name:"+sName
#					bFound = False
#					for i in self.rpl.structs:
#						if i["_name"] == sName:
#							#print "Found! %s" % i
#							bFound = True
#							data = data.ref(RPLStruct(self.rpl,i))
#							break
#						#endif
#					#endfor
#					#print "Type:%s"%type(data)
#					if not bFound:
#						data.syntax("No struct by that name found.")
#						return None
#					#endif
#			
#					# TODO: Validate type 
#				except: pass
			except:
				data = default
			#endtry
		#endif
		
		#print self.struct["_type"],data
#		if tmp is not None:
#			if type(tmp[allowedIdx]) is str and tmp[allowedIdx] in self.rpl.types:
#				data = self.rpl.types[tmp[allowedIdx]][1](data,self)
#			elif type(tmp[allowedIdx][0]) is str and tmp[allowedIdx][0] in self.rpl.types:
#				data = self.rpl.types[tmp[allowedIdx][0]][1](data,self)
#			#endif
#		elif self.struct["_type"] in self.rpl.types: data = self.rpl.types[self.struct["_type"]][1](data,self)
#		
#		if type(data) in [str,unicode]: data = self.unescape(str(data))
		
		#print idx,data
		
		return data
	#enddef
	def __getattr__(self,idx):
		if idx in ["rpl","struct"]: raise AttributeError("Wut?")
		return self.__getitem__(idx)
	#endif
	
	def __setitem__(self,idx,value): self.struct[idx] = value
	def __setattr__(self,idx,value):
		if idx in ["rpl","struct"]: self.__dict__[idx] = value
		else: self.struct[idx] = value
	#enddef
	
	def __iter__(self):
		it = {}
		for i in self.struct:
			if i[0] != "_": it[i] = self.struct[i]
		#endfor
		return iter(it)
	#enddef
	
	def __contains__(self,idx):
		try:
			self.__getitem__(idx)
			return True
		except: return False
	#enddef
	
	def __repr__(self): return repr(self.struct)
	def __str__(self): return str(self.struct)
	
	def __len__(self):
		if "_data" in self.struct:
			if type(self.struct["_data"]) is list: return len(self.struct["_data"])
			else: return 1
		#endif
	#enddef
#endclass

class RPLData:
	relist = re.compile(r'\[[^\[\]]\][*+]?')
	
	hexesc = re.compile(r'\$([0-9a-fA-F]{2})')
	def unescape(self,sStr):
		return self.hexesc.sub((lambda(x):chr(int(x.group(1),16))),sStr).replace("$$","$")
	#enddef
	
	# Data = [data,type,(lineNum,charNum)]
	#
	# Type syntax:
	# [] for "list"
	# | for "or"
	# + after a list for "one or more sets of this content in a row"
	#  eg. [string,number]+ for [string,number] or [string,number,string,number] etc
	# * after a list for either allowing the content to stand on its own or act like a +
	#  eg. [string]* could be string or [string] or [string,string] etc
	#  Note: does not work with multiple entries in the list
	# ? after a type entry in a list makes that entry optional.
	#  Note: Lists may only have optional entries at the end of them. There can be
	#   multiples but the user must enter all up to the one they want.

	def __init__(self,rplst,data,types=None):
		self.rplst = rplst
		self.data = None
		
		if data is None: return 
		
		lErrors = []
		
		def StripList(a):
			# Strip list crap
			if a[0] == "[":
				return a[1:a.rfind("]")]
			else: return a
			#endif
		#enddef
		
		# Verify data types and adjust to custom types
		def Recurse(d,t):
			if type(d[1]) is list: return True # Already parsed
			
			# Split at top level |s
			iLvl = 0
			lT = [""]
			for x in t:
				if x == "[": iLvl += 1
				elif x == "]": iLvl -= 1
				if iLvl == 0 and x == "|": lT.append("")
				else: lT[-1] += x
				#endif
			#endfor
			
			#print "===== d =====\n",d,"\n===== lT =====\n",lT
			
			if iLvl != 0: return self.error(d,"Missing %i ending ]s in type definition." % iLvl)
			
			for x in lT:
				# Set interpreted type to y
				bSetX = True
				tmpx = StripList(x)
				# TODO: Fix [string|[string,number]]*
				if x[0] == "[" and (x[-1] != "*" or type(d[0]) is list):
					y = "list"
					bSetX = False
				elif not tmpx in ["number","string","all"]:
					if tmpx in rplst.rpl.types: y = rplst.rpl.types[tmpx][0]
					else: return self.error(d,"Custom type \"%s\" is not defined." % tmpx)
				else: y = tmpx
				
				if d[1] == "hexnum": d[1] = "number"
				elif d[1] == "literal": d[1] = "string"
				elif d[1] == "range": d[1] = "list"
				
				if y == "all": return True
				
				if y == d[1]:
					if y == "list": # Check contents
						# Split at top level ,s
						lL = [""]
						iLvl = 0
						for c in x:
							if c == "]": iLvl -= 1
							if iLvl == 1 and c == ",": lL.append("")
							elif iLvl >= 1: lL[-1] += c
							if c == "[": iLvl += 1
						#endfor
						
						# Adjust length for checking
						# TODO: Support optional elements
						if x[-1] in "+*":
							iLenL = len(lL)
							iDiff = len(d[0])-iLenL
							iMany = int(iDiff/iLenL)
							if iDiff < 0:
								lErrors.append([d,"Expecting at least %i elements." % iLenL])
								continue
							elif iDiff/iLenL != iMany:
								lErrors.append([d,"Expecting a multiple of %i elements." % iLenL])
								continue
							#endif
							
							lL += lL*iMany
						else:
							iLenL = len(lL)
							if iLenL != len(d[0]):
								lErrors.append([d,"Expecting exactly %i elements." % iLenL])
								continue
							#endif
						#endif
						
						# Verify each entry by forking it off
						bDoCont = False
						for i in range(len(d[0])):
							if not Recurse(d[0][i],lL[i]):
								bDoCont = True
								break
							#endif
						#endfor
						if bDoCont: continue
					#endif
					if bSetX:
						# Convert data
						if x in rplst.rpl.types: d[0] = rplst.rpl.types[x][1](d[0],rplst)
						if type(d[0]) in [str,unicode]: data = self.unescape(str(d[0]))
						# Set type to interpreted and given type
						d[1] = [y,x]
					else: d[1] = [d[1],d[1]]
					#endif
					return True # Static type
				elif d[1] == "reference":
					#d[0] = RPLRef(rplst.rpl,d[0],d[2])
					d[1] = [x,"reference"]
					return True
				#endif
			#endfor
			
			return False # Nothing matched :(
		#enddef
		
		if types:
			if Recurse(data,types):
				self.data = data
			else:
				if len(lErrors) == 0:
					self.error(data,"Type mismatch, expecting: %s" % types)
#					tmp1 = types
#					while True:
#						tmp2 = tmp1
#						tmp1 = self.relist.sub("list",tmp1)
#						if tmp1 == tmp2: break
#					#endwhile
#					lTmp = tmp1.split("|")
#					if len(lTmp) == 1:
#						self.error(data,"Type mismatch, expecting: %s" % (lTmp[0]))
#					elif len(lTmp) == 2:
#						self.error(data,"Type mismatch, expecting: %s" % (lTmp[0]+" or "+lTmp[1]))
#					else:
#						self.error(data,"Type mismatch, expecting: %s" % (", ".join(lTmp[0:-1])+", or "+lTmp[-1]))
					#endif
				elif len(lErrors) == 1: self.error(lError[0][0],lError[0][1])
				else:
					self.error("Likely one of these errors (or potentially a type mismatch):")
					for x in lErrors: self.error(x[0],x[1])
				#endif
			#endif
		else: self.data = data
		#endif
	#enddef
	
	def simpleCompress(self,data):
		def Recurse(data):
			if type(data[0]) is list:
				lRet = []
				for x in data[0]:
					lRet.append(Recurse(x))
				#endfor
				return lRet
			else:
				return data[0]
			#endif
		#enddef
		return Recurse(data)
	#enddef
	
	def error(self,data,sErr,bShow=True):
		error("Error in line %i char %i: %s" % (data[2][0],data[2][1],sErr))
		if bShow:
			if data[1] is not None:
				if type(data[1]) is list:
					if data[1][0] != data[1][1]: sType = data[1][1]+":"+data[1][0]
					else: sType = data[1][0]
				else: sType = data[1]
			elif type(data[0]) in [str,unicode]: sType = "string"
			elif type(data[0]) is [int,long]: sType = "number"
			elif type(data[0]) is list: sType = "list"
			error("  <%s %s>"%(sType,self.simpleCompress(data)))
		#endif
		return False
	#enddef
	
	def v(self):
		if self.data is None: return None
		if type(self.data[1]) == list:
			def Recurse(d):
				if d[1][1] == "list":
					lRet = []
					for x in d[0]: lRet.append(Recurse(x))
					return lRet
				elif d[1][1] == "reference":
					val = d[0].v()
					tmpty = d[1][0]
					if tmpty not in ["string","number","list"]:
						if tmpty in rplst.rpl.types: val = rplst.rpl.types[tmpty][1](val,rplst)
						else: self.error(d,"Custom type \"%s\" not found." % tmpty)
						tmpty = rplst.rpl.types[tmpty][0]
					#endif
					if type(val) is str and tmpty != "string" \
					or type(val) in [int,long] and tmpty != "number" \
					or type(val) is list and tmpty != "list":
						self.error(d,"Value pointed to does not match expected type.")
					#endif
					return val
				else: return d[0]
			#enddef
			return Recurse(self.data)
		else: return self.simpleCompress(self.data)
	#enddef
	
	def __nonzero__(self): return self.data is not None
	def __iter__(self): return iter(self.v())
	def __str__(self): return str(self.v())
	def __int__(self): return int(self.v())
#endclass

