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
	if tName == "reference": tName = data.get(retCl=True).typeName
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
	if tName == "reference": tName = data[key].get(retCl=True).typeName
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
rpl, std = None, None
def main():
	global rpl, std
	# Load crap
	rpldir = path.join("..", "rpl")
	log("Beginning parse tests...")
	rpl = loadmod("rpl", rpldir)
	log("Loaded rpl.rpl")

	log("# Test 1: rpl (basic) #")
	basic = rpl.RPL()
	basic.parse(path.join("rpls", "rpl.rpl"))
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
		tmp = rpl.RPLTypeCheck(basic, key, syn).verify(data)
		if ((expect is None and tmp is None) 
		or (tmp is not None and tmp.typeName == expect)):
			return True
		#endif
		return err('Failed test: "%s"' % key, False)
	#enddef

	Str, Lit, Num = rpl.String("hi"), rpl.Literal("hi"), rpl.Number(1)
	def RL(*x): return rpl.List(list(x))
	if (not typeCheck("StrStrTest", "string", Str, "string")
	or  not typeCheck("StrLitTest", "string", Lit, "literal")
	or  not typeCheck("StrNumTest", "string", Num, None)
	or  not typeCheck("OrNumTest", "string|number", Num, "number")
	or  not typeCheck("ListNumTest", "[number]", Num, None)
	or  not typeCheck("ListListTest", "[number]", RL(Num), "list")
	or  not typeCheck("ListBadListTest", "[number]", RL(Str), None)
	or  not typeCheck("LONumTest", "[string|number]", Num, None)
	or  not typeCheck("LOListTest", "[string|number]", RL(Num), "list")
	or  not typeCheck("SublistTest", "[number,[number],number]", RL(Num,RL(Num),Num), "list")
	or  not typeCheck("SublistBadTest", "[number,[number],number]", RL(Num,RL(Str),Num), None)
	or  not typeCheck("OLTest1", "string|[number]", Str, "string")
	or  not typeCheck("OLTest2", "string|[number]", RL(Num), "list")
	or  not typeCheck("OLBadTest", "string|[number]", Num, None)
	or  not typeCheck("OLTest1", "[number|[string],number]", RL(Num,Num), "list")
	or  not typeCheck("OLTest1", "[number|[string],number]", RL(RL(Str),Num), "list")
	or  not typeCheck("SSSSSLTest", "[[[[[string]]]]]", RL(RL(RL(RL(RL(Str))))), "list")
	or  not typeCheck("Repeat1Test1", "[number]*", Num, "list")
	or  not typeCheck("Repeat1Test2", "[number]*", RL(Num), "list")
	or  not typeCheck("Repeat1Test3", "[number]*", RL(Num,Num), "list")
	or  not typeCheck("Repeat1Test4", "[number]*", Str, None)
	or  not typeCheck("Repeat2Test1", "[number]+", Num, None)
	or  not typeCheck("Repeat2Test2", "[number]+", RL(Num), "list")
	or  not typeCheck("Repeat2Test3", "[number]+", RL(Num,Num), "list")
	or  not typeCheck("Repeat3Test", "[number|string|list]+", RL(Str), "list")
	or  not typeCheck("Repeat4Test1", "[number,string]*", Num, "list")
	or  not typeCheck("Repeat4Test2", "[number,string]*", Str, "list")
	or  not typeCheck("Repeat4Test3", "[number,string]*", RL(Num,Str), "list")
	or  not typeCheck("Repeat4Test4", "[number,string]*", RL(Str,Num), None)
	or  not typeCheck("Repeat5Test1", "[number,string]!", Num, "list")
	or  not typeCheck("Repeat5Test2", "[number,string]!", Str, "list")
	or  not typeCheck("Repeat5Test3", "[number,string]!", RL(Num,Str), "list")
	or  not typeCheck("Repeat5Test4", "[number,string]!", RL(Str,Num), None)
	or  not typeCheck("Repeat5Test5", "[number,string]!", RL(Num,Str,Num,Str), None)
	or  not typeCheck("Repeat6Test1", "[number]~", Num, "number")
	or  not typeCheck("Repeat6Test2", "[number]~", RL(Num), "list")
	or  not typeCheck("Repeat7Test1", "[number].", Num, "number")
	or  not typeCheck("Repeat7Test2", "[number].", RL(Num), "list")
	or  not typeCheck("Repeat8Test1", "[number|^]", RL(RL(Num)), "list")
	or  not typeCheck("Repeat8Test2", "[^|number]", RL(RL(Num)), "list")
	or  not typeCheck("Repeat8Test3", "[^|number]", RL(RL(Str)), None)
	or  not typeCheck("Repeat8Test4", "[number|^]", RL(RL(RL(Num))), "list")
	# Make sure it doesn't infinitely recurse or anything here
	or  not typeCheck("Repeat8Test5", "[number|^]", RL(RL(RL(Str))), None)
	or  not typeCheck("Repeat8Test6", "[number|^]", RL(RL(RL(RL(RL(RL()))))), None)
	or  not typeCheck("Repeat9Test1", "[string,number]!0", Str, "list")
	or  not typeCheck("Repeat9Test2", "[string,number]!0", Num, None)
	or  not typeCheck("Repeat10Test1", "[string,number]+", RL(Str,Num), "list")
	or  not typeCheck("Repeat10Test2", "[string,number]+", RL(Str,Num,Str,Num), "list")
	or  not typeCheck("Repeat10Test3", "[string,number]+", RL(Str,Num,Str), None)
	or  not typeCheck("Repeat11Test1", "[string,number]+1", RL(Str), "list")
	or  not typeCheck("Repeat11Test2", "[string,number]+1", RL(Str,Num), "list")
	or  not typeCheck("Repeat11Test3", "[string,number]+1", RL(Str,Num,Str,Num), None)
	or  not typeCheck("Repeat11Test4", "[string,number]+1", RL(Str,Num,Num), "list")
	or  not typeCheck("Repeat11Test5", "[string,number]+1", RL(Num), None)
	or  not typeCheck("ROTest1", "[number]*|string", Num, "list")
	or  not typeCheck("ROTest2", "[number]*|string", RL(Num), "list")
	or  not typeCheck("ROTest3", "[number]*|string", Str, "string")
	or  not typeCheck("HeirTest1", "range", rpl.Range([Num,Num]), "range")
	or  not typeCheck("HeirTest2", "range", RL(Num,Num), "range")
	): return 2
	log("Test 2 end")

	#log("# Test 3: write tests #")
	# TODO: Make this..
	#log("Test 3 end")

	log("# Test 4: References #")
	refers = rpl.RPL()
	refers.parse(path.join("rpls", "references.rpl"))
	log("Loaded and parsed")
	x = refers.child("tests")
	if (not check(x, "test1", "number", 1)
	or not comp(x, "test2", "list", [ ("literal", "+"), ("literal", "more"),
		("literal", "voluptuous"), ("list", [ ("literal", "he"), ("literal", "he"),
		("literal", "he") ]) ] )
	or not check(x, "test3", "literal", "+")
	or not check(x, "test4", "literal", "more")
	or not check(x, "test5", "literal", "voluptuous")
	or not comp(x, "test6", "list", [ ("literal", "he"), ("literal", "he"),
		("literal", "he") ])
	or not check(x, "test7", "literal", "he")
	or not check(x, "test8", "number", 1330494503)
	or not check(x, "test9", "number", 1)
	or not check(x, "test10", "number", 1)
	or not check(x, "test11", "number", 3)
	): return 4
	x = refers.child("ImaGParent").child("ImaParent").child("ImaToysRUsKid")
	if (not check(x, "test1", "number", 3)
	or not check(x, "test2", "number", 2)
	): return 4
	log("Test 4 end")

	log("Beginning meatier tests...")
	std = loadmod("std", rpldir)
	log("Loaded rpl.std")
	log("# Test 10: Data #")
	astd = std.Standard()
	astd.parse(path.join("rpls", "data.rpl"))
	folder = path.join("rpls", "data")
	astd.Def("file", "test.rpl")
	astd.exportData(path.join(folder, "data.bin"), folder)
	# TODO: Compare test.rpl with data.rpl
	log("Export successful")
	astd.Def("file", "data.rpl")
	astd.importData(path.join(folder, "test.bin"), folder)
	# TODO: Compare test.bin with data.bin
	log("Import successful")
	log("Test 10 end")

	return 0
#enddef
sys.exit(main())
