#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
RPL Parser class by Wa (logicplace.com) - v7
Part of gfxchgr.py
"""

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
	
	def __init__(self,ref,tPos):
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
	
	def name(self): return self.struct
	
	def syntax(self,sErr):
		error("Error in line %i char %i: %s" % (self.pos[0],self.pos[1],sErr))
		if bShowData: error("  <reference %s>" % str(self))
	#enddef
	
	def ref(self,info):
		if self.key:
			if self.key not in info: error("Key %s not allowed in %s." % (self.key,self.struct))
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
	
	# Type syntax:
	# [] for "list"
	# | for "or"
	# + after a list for "one or more sets of this content in a row"
	#  eg. [string,int]+ for [string,int] or [string,int,string,int] etc
	# * after a list for either allowing the content to stand on its own or act like a +
	#  eg. [string]* could be string or [string] or [string,string]
	#  Note: does not work with multiple entries in the list
	# ? after a type entry in a list makes that entry option.
	#  Note: Lists may only have optional entries at the end of them. There can be multiples
	#   multiples but the user must enter all up to the one they want.
	tokenizeType = re.compile(
		r'([a-z]+|\[.*\])'
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

	def __init__(self,dAllow,dCustomType,vFile=None):
		self.structs = []
		self.root = []
		self.dataonly = None
		self.data = []
		self.allowed = dAllow
		self.types = dCustomType
		self.cur = -1
	
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
		
		def verifData(sType):
			if len(lParents) > 0:
				iTmp = -1
				lIndexes = []
				try:
					while type(lParents[iTmp]) is list:
						lIndexes = [len(lParents[iTmp])-1] + lIndexes
						iTmp -= 1
					#endwhile
				except: return False # shouldn't happen..
				#if len(lIndexes) > 0: lIndexes[-1] += 1 # Where this one will be inserted
				
				sParentType = lParents[iTmp]["_type"]
				vAllowedType = self.allowed[sParentType][sCurrentKey][0]
				if type(vAllowedType) is list:
					try:
						for iDid in range(len(lIndexes[0:-1])):
							if type(vAllowedType) is str:
								if "[" not in vAllowedType: return syntax("Key does not allow a list at this depth.")
								break
							#endif
							vAllowedType = vAllowedType[lIndexes[iDid]]
						#endfor
					except: return syntax("Out of list bounds.")
				#endif
				if type(vAllowedType) is list:
					if sType == "list": return True
					else: return syntax("Requires a list here.")
				#endif
				
				lTokens = self.tokenizeType.findall(vAllowedType)
				for sT in lTokens:
					# TODO: Finish
					#if sT == "[":
					pass
				#endfor
			#endif
		#enddef
		
		def addData(sData,sType):
			if len(self.structs) == 0:
				if len(lParents) == 0: self.data.append(sData)
				else: lParents[-1].append(sData)
			elif type(lParents[-1]) is list:
				lParents[-1].append(sData)
			elif sCurrentKey and not sCurrentKey in lParents[-1]:
				lParents[-1][sCurrentKey] = sData
			elif sCurrentKey in lParents[-1] and type(lParents[-1][sCurrentKey]) is list:
				lParents[-1][sCurrentKey].append(sData)
			else:
				return syntax(tok,"Unused %s." % sType,rplfile)
			#endif
			return sData
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
						if lStructHead[0] not in self.allowed[sParentType]\
						or self.allowed[sParentType][lStructHead[0]][0] != "struct":
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
				if sKey not in self.allowed[sParentType]\
				or self.allowed[sParentType][sKey][0] == "struct":
					return syntax("%s has no key %s." % (
						sParentType,sKey),False
					)
				#endif
				sCurrentKey = sKey
			elif sRef:
				addData(RPLRef(sRef,filepos()),"reference")
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
				for sRange in lRanges:
					lBounds = sRange.split("-")
					lMulti = sRange.split("*")
					if len(lBounds) == 2:
						iL,iR = int(lBounds[0]),int(lBounds[1])
						if iL < iR: lNum += range(iL,iR+1)
						else: lNum += range(iL,iR-1,-1)
					elif len(lMulti) == 2:
						iV,iM = int(lMulti[0]),int(lMulti[1])
						lNum += [iV]*iM
					else: lNum.append(int(lBounds[0]))
				#endfor
			
				if len(lNum) == 1: addData(lNum[0],"number")
				else: addData(lNum,"range")
				sCurrentKey = None
			#endif
			
			if not sLit and sPotentialStruct:
				return syntax("Literal with no purpose: %s"%sPotentialStruct,False)
			#endif
		#endfor
		
		self.dataonly = bool(len(self.data))
	#enddef
	
	def __getitem__(self,idx):
		if type(idx) is int:
			if self.dataonly: return RPLStruct(self,{"_data":self.data[idx]})
			else: return RPLStruct(self,self.root[idx])
		elif idx == "ROM":
			for i in self.root:
				if i["_type"] == "ROM": return RPLStruct(self,i)
			#endfor
			raise IndexError("ROM not found.")
		else: raise IndexError("Must be number or 'ROM'")
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
			if idx not in tmp: raise IndexError("%s not allowed in %s."%(idx,self.struct["_type"]))
		#endif
		if data is None:
			try:
				check = self.struct
				default = None
				while idx not in check:
					t2 = self.rpl.allowed[check["_type"]]
					if default is None and idx in t2 and type(t2[idx]) is list and len(t2[idx]) >= 3: default = t2[idx][2]
					check = check["_parent"]
				#endwhile
				data = check[idx]
		
				# Check if it's a reference
				try:
					sName = data.name()
					#print "Name:"+sName
					bFound = False
					for i in self.rpl.structs:
						if i["_name"] == sName:
							#print "Found! %s" % i
							bFound = True
							data = data.ref(RPLStruct(self.rpl,i))
							break
						#endif
					#endfor
					#print "Type:%s"%type(data)
					if not bFound:
						data.syntax("No struct by that name found.")
						return None
					#endif
			
					# TODO: Validate type 
				except: pass
			except:
				data = default
			#endtry
		#endif
		
		#print self.struct["_type"],data
		if tmp is not None:
			if type(tmp[idx]) is str and tmp[idx] in self.rpl.types: data = self.rpl.types[tmp[idx]][0](data,self)
			elif type(tmp[idx][0]) is str and tmp[idx][0] in self.rpl.types: data = self.rpl.types[tmp[idx][0]][0](data,self)
		elif self.struct["_type"] in self.rpl.types: data = self.rpl.types[self.struct["_type"]][0](data,self)
		
		if type(data) in [str,unicode]: data = self.unescape(str(data))
		
		#print data
		
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
