#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Python import is SO bad.. Though this is only slightly better.
import imp, sys, os.path as path
def loadmod(n,p): return imp.load_module(n,*(imp.find_module(n,[path.join(path.dirname(path.abspath(sys.argv[0])),p) if __name__ == "__main__" else path.join(path.dirname(path.abspath(__file__)),p)])))

# Helper functions:
def checklen(data, exLen):
	if len(data) != exLen:
		return err('Unexpected length in "%s" (got %i)' % (
			data.name, len(data)
		), False)
	else: return True
#enddef

def subcheck(data, name, exType, exVal, typeOnly=False):
	tName, val = data.typeName, data.get()
	if tName != exType:
		return err('Unexpected datatype for "%s" (got "%s")' % (
			name, tName
		), False)
	elif typeOnly: return True
	elif val != exVal:
		return err('Unexpected value for "%s" (got "%s")' % (
			name, val
		), False)
	#endif
	return True
#enddef

def check(data, key, exType, exVal):
	return subcheck(data[key], "%s.%s" % (data.name(),key), exType, exVal)

def subcomp(l1, l2, heir):
	global rpl
	if len(l1) != len(l2):
		return err('Incompatible lengths in "%s" (%i vs %i)' % (
			heir, len(l1), len(l2)
		))
	#endif
	for i,x in enumerate(l1):
		n = heir + ("[%i]" % i)
		isList = isinstance(x, rpl.List)
		if not subcheck(x, n, *(l2[i]), typeOnly=isList): return False
		if (isList and not subcomp(x.get(), l2[i][1], n)): return False
	#endfor
	return True
#enddef

def comp(data, key, exType, ex):
	tName, val = data[key].typeName, data[key].get()
	if tName != exType:
		return err('Unexpected datatype for "%s.%s" (got "%s")' % (
			data.name(), key, tName
		), False)
	#endif
	return subcomp(val, ex, "%s.%s" % (data.name(),key))
#enddef

# Logging functions
from time import time
def log(msg):
	global start
	print("%.3fs: %s" % (time()-start, msg))
#enddef

def err(msg, errnum=None):
	global start
	sys.stderr.write("%.3fs: %s\n" % (time()-start, msg))
	return errnum
#enddef

start = time()
rpl = None
def main():
	global rpl
	# Load crap
	rpldir = path.join("..", "rpl")
	log("Beginning parse tests...")
	rpl = loadmod("rpl", rpldir)
	log("Loaded rpl.rpl")

	log("# Test 1: rpl (basic) #")
	basic = rpl.RPL()
	basic.parse(path.join("parse", "rpl.rpl"))
	log("Loaded and parsed")
	for x in basic:
		if x.name() == "AndAnotherStatic":
			if (not checklen(x, 1)
			or not check(x, "just", "literal", "because")
			): return 1
		elif x.name() == "static0":
			if (not checklen(x, 8)
			or not check(x, "string", "string", "hi")
			or not check(x, "literal", "literal", "bye")
			or not check(x, "number", "number", 1)
			or not check(x, "hexnum", "hexnum", 0x2222)
			or not check(x, "multi", "string", "abcdefghijklmnopqrstuvwxyz")
			): return 1

			comp(x, "range", "range", map(
				lambda(x): ("number",x),
				[1,2,3,4,5,2,2,2,2,5,4,3]
			) + [("literal","x"), ("number", 1), ("hexnum", 0xa)])

			comp(x, "list", "list", [
				("string", "str"), ("literal", "lit"), ("number", 1),
				("hexnum", 0xbabe), ("range",map(lambda(x): ("number",x),
				[1,2,3]))
			])

			for y in x:
				if y.name() == "sub":
					if (not checklen(y, 1)
					or not check(y, "lit", "literal", ":D")
					): return 1
				else: return err('Unexpected sub "%s"' % y.name(), 1)
			#endfor
			#
		else: return err('Unexpected static "%s"' % x.name(), 1)
	#endfor
	log("Test 1 end")

	log("# Test 2: type checking #")
	def typeCheck(key, syn, data, expect):
		if rpl.RPLTypeCheck(basic, key, syn).verify(data) != expect:
			return err('Failed test: "%s"' % key, False)
		#endif
		return True
	#enddef

	Str, Lit, Num = rpl.String("hi"), rpl.Literal("hi"), rpl.Number(1)
	def RL(*x): return rpl.List(list(x))
	if (not typeCheck("StrStrTest", "string", Str, True)
	or  not typeCheck("StrLitTest", "string", Lit, True)
	or  not typeCheck("StrNumTest", "string", Num, False)
	or  not typeCheck("OrNumTest", "string|number", Num, True)
	or  not typeCheck("ListNumTest", "[number]", Num, False)
	or  not typeCheck("ListListTest", "[number]", RL(Num), True)
	or  not typeCheck("ListBadListTest", "[number]", RL(Str), False)
	or  not typeCheck("LONumTest", "[string|number]", Num, False)
	or  not typeCheck("LOListTest", "[string|number]", RL(Num), True)
	or  not typeCheck("SublistTest", "[number,[number],number]", RL(Num,RL(Num),Num), True)
	or  not typeCheck("SublistBadTest", "[number,[number],number]", RL(Num,RL(Str),Num), False)
	or  not typeCheck("OLTest1", "string|[number]", Str, True)
	or  not typeCheck("OLTest2", "string|[number]", RL(Num), True)
	or  not typeCheck("OLBadTest", "string|[number]", Num, False)
	or  not typeCheck("OLTest1", "[number|[string],number]", RL(Num,Num), True)
	or  not typeCheck("OLTest1", "[number|[string],number]", RL(RL(Str),Num), True)
	or  not typeCheck("SSSSSLTest", "[[[[[string]]]]]", RL(RL(RL(RL(RL(Str))))), True)
	or  not typeCheck("Repeat1Test1", "[number]*", Num, True)
	or  not typeCheck("Repeat1Test2", "[number]*", RL(Num), True)
	or  not typeCheck("Repeat1Test3", "[number]*", RL(Num,Num), True)
	or  not typeCheck("Repeat1Test4", "[number]*", Str, False)
	or  not typeCheck("Repeat2Test1", "[number]+", Num, False)
	or  not typeCheck("Repeat2Test2", "[number]+", RL(Num), True)
	or  not typeCheck("Repeat2Test3", "[number]+", RL(Num,Num), True)
	or  not typeCheck("Repeat2Test4", "[number|string|list]+", RL(Str), True)
	or  not typeCheck("ROTest1", "[number]*|string", Num, True)
	or  not typeCheck("ROTest2", "[number]*|string", RL(Num), True)
	or  not typeCheck("ROTest3", "[number]*|string", Str, True)
	or  not typeCheck("HeirTest1", "range", rpl.Range([1,2]), True)
	# Honeslty I'm not super sure I like this one
	or  not typeCheck("HeirTest2", "range", RL(1,2), False)
	): return 2
	log("Test 2 end")

	return 0
#enddef
sys.exit(main())
