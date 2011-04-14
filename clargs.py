#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Command Line Arguments library v1 by Wa (logicplace.com)
Make command line arguments easy, efficient, and standardized!
Get the latest version at: http://logicplace.com/pc/projects/clargs.py

Clargs will accept standard linux forms of command line entry, including one-
letter flag lists and full word flags followed by any arguments they need.
See example below for..an example..

Initialize yours clargs object with what kind of data can be passed on the
command line. You can pass either a dict or list to do this, it's just
preference! Optionally, you can pass a reference section to tell clargs what
you want to define, and in what order.
These are the sections you can define (in their default ordering):
* short: The one character name of the flag
* full: The full name of the flag
* argc: How many arguments this flag requires. Can also map to other flags, see
        below.
* default: The default value for this, if the user doesn't give one.
* desc: The description of what it does. This is used in the help file.

You can map arguments to each other by passing either a string or a list in the
argc field. If passing a string, it is a string of the short names of the flags
it maps to. If it's a list, it's a list of strings that are either the short or
long name. Note that this listing is in order, and the arguments passed will be
required in that order. I suggest you mention that order in its help entry.

I tried to make typing and usage as open and logical as possible in spirit of
python! You can pass a list or a dict of lists or dicts. Here's a rundown of
how each mode works. The following are all the same, all include the optional
reference section when possible. Any differences are noted!
Dict/List {
	"_ref":  ["short","full", "argc","default","desc"], # Note that this is the default _ref
	"alpha": ["a",    "alpha",1,     "A",      "Define the first letter of the alphabet."],
	"beta":  ["b",    None,   0,     True,     "Whether the second letter exists or not."],
	"gamma": [None,   "gamma",1,     "C",      "Define the third letter of the alphabet."]
}

Dict/Dict
{
	"alpha": {
		"short": "a",
		"full": "alpha",
		"argc": 1,
		"default": "A",
		"desc": "Define the first letter of the alphabet."
	},
	"beta": {
		"short": "b",
		"argc": 0,
		"default": True,
		"desc": "Whether the second letter exists or not."
	},
	"gamma": {
		"full": "gamma",
		"argc": 1,
		"default": "C",
		"desc": "Define the third letter of the alphabet."
	}
}

List/List
[
	["_ref",
	 "short","full", "argc","default","desc"], # Note that this is the default _ref
	["a",    "alpha",1,     "A",      "Define the first letter of the alphabet."],
	# Name is b instead of beta
	["b",    None,   0,     True,     "Whether the second letter exists or not."],
	[None,   "gamma",1,     "C",      "Define the third letter of the alphabet."]
]

List/Dict
[
	{
		"short": "a",
		"full": "alpha",
		"argc": 1,
		"default": "A",
		"desc": "Define the first letter of the alphabet."
	},
	# Name is b instead of beta
	{
		"short": "b",
		"argc": 0,
		"default": True,
		"desc": "Whether the second letter exists or not."
	},
	{
		"full": "gamma",
		"argc": 1,
		"default": "C",
		"desc": "Define the third letter of the alphabet."
	}
]

Note: argc being None is synonymous with argc being 0
Note: You may pass a list of possible flag names in both short and full
      eg. ["h","?"],"help"
Note: If no description is given, there won't be an entry in the help
Note: Using a list/* type indicates the order of entries in the help
Note: Using an argc of 0 implies the flag is treated as a boolean.
      Using True as the default value of a boolean means that it will be set to
      False when it's passed by the user, instead of True.
Note: If you give a default value it will be noted in the help.
Note: If argc is more than 1, I suggest you pass a list as the default value

To declare your object use:

from clargs import clargs
clArgs = clargs(
	# Use one from above
).parse()

You can pass the arguments list to parse in parse(), but sys.argv is used by
default.

To retrieve information about what was passed you can do any of the following.
"alpha" in clArgs # True if the user passed this flag (eg. --alpha or -a)
clArgs.alpha # Returns the value of alpha as a list
clArgs.beta # or (Depending on which method you use from above)
clArgs.b # Returns the value as a bool
clArgs["alpha"] # Same as above
clArgs[0] # Returns the script name
clArgs[1] # Returns the first value submitted that's not associated with a flag
clArgs[n] # Same as above, but for the nth value
str(clArgs) # Returns the formatted help documentation
bool(clArgs) # Returns whether it's parsed the command line or not
for x in clArgs # Iterates through all flag names
dict(clArgs) # BROKEN. Should return a dict version of the arguments
"""

import sys
from os.path import basename

class clargs:
	"""Manage command line argument passing"""
	def __init__(self,vReg,lArgs=sys.argv):
		self.__mini = {}
		self.__full = {}
		self.__reg = {}
		self.args = lArgs
		self.__a = {}
		self.etc = []
		self.__helpOrder = []

		bDict = type(vReg) is dict
		if not bDict and type(vReg) is not list:
			raise TypeError,"Argument registry must be a list or dict"
		#endif
		
		dN2I = {"short":4,"full":4,"argc":4,"default":4,"desc":4}
		lToIter = None
		if bDict and "_ref" in vReg: lToIter = vReg["_ref"]
		elif not bDict and type(vReg[0]) is list and vReg[0][0] == "_ref": lToIter = vReg[0][1:]
		
		if lToIter:
			for iX in range(len(lToIter)):
				sX=lToIter[iX]
				if sX in dN2I: dN2I[sX] = iX
			#endfor
		else:
			dN2I = {"short":0,"full":1,"argc":2,"default":3,"desc":4}
		#endif
		
		for vI in vReg:
			sName = None
			if bDict:
				if vI == "_ref": continue
				sName = vI
				vI = vReg[vI]
			#endif
			
			if type(vI) is list:
				if vI[0] == "_ref": continue
				vShort,vLong,vArgc,vDef,vDesc = dN2I["short"],dN2I["full"],dN2I["argc"],dN2I["default"],dN2I["desc"]
				iDiff = 5-len(vI)
				if iDiff > 0: vI += [None] * iDiff
			elif type(vI) is dict:
				vShort,vLong,vArgc,vDef,vDesc = "short","full","argc","default","desc"
				if vShort not in vI: vI[vShort] = None
				if vLong not in vI: vI[vLong] = None
				if vArgc not in vI: vI[vArgc] = None
				if vDef not in vI: vI[vDef] = None
				if vDesc not in vI: vI[vDesc] = None
			else: raise TypeError,"Elements in argument registry must be a list of lists or dicts."
			
			if len(vI[vShort]) == 0: vI[vShort] = None
			if len(vI[vLong]) == 0: vI[vLong] = None
			if vI[vArgc] is None: vI[vArgc] = 0
			if vI[vDesc] is None: vI[vDesc] = ""
			
			if vI[vLong] is not None:
				if type(vI[vLong]) is not list: vI[vLong] = [vI[vLong]]
				sName = sName or vI[vLong][0]
				for sI in vI[vLong]: self.__full[sI] = sName
			#endif
			if vI[vShort] is not None:
				if type(vI[vShort]) is not list: vI[vShort] = [vI[vShort]]
				sName = sName or vI[vShort][0]
				for sI in vI[vShort]:
					if len(sI) != 1:
						raise Exception,(1,"Short names must only be one character long")
					#endif
					self.__mini[sI] = sName
				#endfor
			#endif
			
			if sName is not None:
				self.__reg[sName] = [vI[vArgc],vI[vDesc],vI[vDef]]
				self.__helpOrder.append(sName)
				#if vI[vDef] is not None: self.__a[sName] = vI[vDef]
				#elif vI[vArgc] == 0: self.__a[sName] = False
			#endif
		#endfor
	#enddef
	
#	def append(self,vTemp=None,full=None,argc=None,default=None,desc=None,name=None,short=None):
#		if vTemp and not (short and full and argc and default and desc):
#			if vTemp
#		elif not mini:
#			mini = vTemp
#		else: raise ValueError,"Too many arguments"
#		
#	#enddef
	
	def parse(self,lArgs=None):
		if lArgs is None: lArgs = self.args
		self.__a = {}
		self.etc = [lArgs[0]]
		lPos = [1,len(lArgs)]
		
		def GetArgs(iCount):
			iEnd = lPos[0]+iCount
			if iEnd > lPos[1]: raise Exception,(2,"Not enough arguments passed for flags used")
			lRet = lArgs[lPos[0]:iEnd]
			lPos[0] = iEnd
			return lRet[0] if iCount == 1 else tuple(lRet)
		#enddef
		
		def SetVals(sName):
			vArgc = self.__reg[sName][0]
			if type(vArgc) in [str,list]: # TODO: Support unicode
				for x in vArgc:
					if x in self.__full: x = self.__full[x]
					elif x in self.__mini: x = self.__mini[x]
					else: raise KeyError,"Trying to map to non-existant argument \"%s\"" % x
					SetVals(x)
				#endif
			else: 
				if vArgc == 0: self.__a[sName] = not self.__reg[sName][2]
				else:
					if sName not in self.__a: self.__a[sName] = []
					self.__a[sName].append(GetArgs(vArgc))
				#endif
			#endif
		#enddef
		
		while lPos[0] < lPos[1]:
			sCom = GetArgs(1)
			if sCom[0:2] == "--" or sCom[0] == "/":
				# Trim flag
				if sCom[0:2] == "--": sComN = sCom[2:]
				else: sComN = sCom[1:]
				
				if sComN in self.__full: sName = self.__full[sComN]
				elif sComN in self.__mini: sName = self.__mini[sComN]
				else: raise KeyError,"No argument \"%s\"" % sComN
				SetVals(sName)
			elif sCom[0] == "-":
				for sC in sCom[1:]:
					if sC not in self.__mini: raise KeyError,"No argument \"%s\"" % sC
					sName = self.__mini[sC]
					SetVals(sName)
				#endfor
			else:
				self.etc.append(sCom)
			#endif
		#endwhile
		
		return self
	#enddef
	
	def __getitem__(self,vKey):
		if vKey == 0: return basename(self.args[0])
		if self.etc: 
			if type(vKey) == int: return self.etc[vKey]
		elif not self.__a: raise Exception,(4,"Not parsed yet")
		return self.__getattr__(str(vKey))
	#enddef
	
	def __getattr__(self,sKey):
		if not self.__a and not self.etc: raise Exception,(4,"Not parsed yet")
		if sKey in self.__a: return self.__a[sKey]
		elif self.__reg[sKey][0] == 0: return bool(self.__reg[sKey][2])
		else: return [self.__reg[sKey][2]]
	#enddef
	
	def __str__(self):
		# Help
		iMaxLen = 0
		dName2Opts = {}
		for sI in self.__full:
			sName = self.__full[sI]
			if not sName in dName2Opts: dName2Opts[sName] = [[],[]]
			dName2Opts[sName][1].append(sI)
			iMaxLen = max(len(sI),iMaxLen)
		#endfor
		for sI in self.__mini:
			sName = self.__mini[sI]
			if not sName in dName2Opts: dName2Opts[sName] = [[],[]]
			dName2Opts[sName][0].append(sI)
		#endfor
		
		iMax = 80 # Get cli max later
		iLeft = 3+iMaxLen+2 # " S Long...  "
		iRight = iMax-iLeft
		sLines = ""
		for sIdx in self.__helpOrder:
			if self.__reg[sIdx][1] != "": # Has a description
				lDesc = []
				sDesc = self.__reg[sIdx][1]
				if self.__reg[sIdx][2] is not None: sDesc += " (Default: %s)"%self.__reg[sIdx][2]
				while sDesc != "":
					iTo = min(len(sDesc),iRight)
					if iTo == iRight:
						# Wrap
						iTo = (lambda i: iTo if i==-1 else i+1)(
							max(map((lambda i: sDesc.rfind(i,max(iTo-15,0),iTo))," ,-.:;+!?'\""))
						)
					#endif
					lDesc.append(sDesc[0:iTo])
					sDesc = sDesc[iTo:]
				#endwhile
				lShort = dName2Opts[sIdx][0]
				lLong = dName2Opts[sIdx][1]
				iDescLen = len(lDesc)
				iShortLen = len(lShort)
				iLongLen = len(lLong)
				for iI in range(max(iDescLen,iShortLen,iLongLen)):
					sLines += " %s %-*s  %s\n" % (
						lShort[iI] if iI < iShortLen else " ",
						iMaxLen,lLong[iI] if iI < iLongLen else "",
						lDesc[iI] if iI < iDescLen else ""
					)
				#endfor
			#endif
		#endfor
		return sLines
	#enddef
	
	def __repr__(self):
		if not self.__a and not self.etc: return "<clargs>"
		return "<clargs %s>" % str(self.__a)
	#enddef
	
	def __nonzero__(self):
		return bool(self.__a or self.etc)
	#enddef
	
	def __contains__(self,sKey):
		if not self.__a and not self.etc: raise Exception,(4,"Not parsed yet")
		return sKey in self.__a
	#enddef
	
	def __iter__(self):
		"""dict(clargs) borked, fix later"""
		return iter(self.__reg)
	#enddef
	
	def __len__(self):
		return len(self.etc)
	#endif
	
#endclass
