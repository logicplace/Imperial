#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Position/Index Pairing class by Wa (logicplace.com) - v1
Part of gfxchgr.py
"""

class PosIdxPair:
	def __init__(self,lPos,vIdx,sDir):
		self.x = lPos[0] if type(lPos[0]) is list else [lPos[0]]
		self.y = lPos[1] if type(lPos[1]) is list else [lPos[1]]
		self.xlen = len(self.x)
		self.ylen = len(self.y)
		self.idx = vIdx if type(vIdx) is list else [vIdx]
		self.size = min(len(self.idx),self.xlen*self.ylen)
		self.dir = sDir
		
		self.cur = 0
	#enddef
	
	def __iter__(self): return self

	def next(self):
		i = self.cur
		if i >= self.size: raise StopIteration
		idx = self.idx[i]
		if   self.dir == "LRUD": x,y = i%self.xlen, int(i/self.xlen)
		elif self.dir == "RLUD": x,y = self.xlen-1-(i%self.xlen), int(i/self.xlen)
		elif self.dir == "LRDU": x,y = i%self.xlen, self.ylen-1-int(i/self.xlen)
		elif self.dir == "RLDU": x,y = self.xlen-1-(i%self.xlen), self.ylen-1-int(i/self.xlen)
		elif self.dir == "UDLR": x,y = int(i/self.ylen), i%self.ylen
		elif self.dir == "DULR": x,y = self.xlen-1-int(i/self.ylen), i%self.ylen
		elif self.dir == "UDLR": x,y = int(i/self.ylen), self.ylen-1-i%self.ylen
		elif self.dir == "DULR": x,y = self.xlen-1-int(i/self.ylen), self.ylen-1-i%self.ylen
		self.cur += 1
		return (self.x[x],self.y[y],idx)
	#enddef
#endclass
