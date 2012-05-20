#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Test cases for RPL.

The easiest way to run this is via "python -m unittest discover" from the
project root directory. Alternatively, you can use "python -m tests.tests" to
run this file specifically, but the former command will discover any other test
files in the project.
"""

import os.path
import unittest
from time import time

from rpl import rpl, std

class RPLTestCase(unittest.TestCase):
	# Helper functions:
	def checkLen(self, data, exLen):
		self.assertEqual(len(data), exLen,
			'Unexpected length in "%s" (got %i)' % (data.name, len(data)))
	#enddef

	def subCheck(self, data, name, exType, exVal, typeOnly=False):
		tName, val = data.typeName, data.get()
		if tName == "reference": tName = data.get(retCl=True).typeName
		self.assertEqual(tName, exType,
			'Unexpected data type for "%s" (got "%s")' % (name, tName))
		
		if not typeOnly:
			self.assertEqual(val, exVal,
				'Unexpected value for "%s" (got "%s")' % (name, val))
		#endif
	#enddef

	def check(self, data, key, exType, exVal):
		return self.subCheck(data[key], "%s.%s" % (data.name(),key), exType, exVal)

	def subComp(self, l1, l2, heir):
		global rpl
		self.assertEqual(len(l1), len(l2),
			'Incompatible lengths in "%s" (%i vs %i)' % (heir, len(l1), len(l2)))
		for i, x in enumerate(l1):
			n = heir + ("[%i]" % i)
			isList = isinstance(x, rpl.List)
			self.subCheck(x, n, *(l2[i]), typeOnly=isList)
			if isList:
				self.subComp(x.get(), l2[i][1], n)
		#endfor
	#enddef

	def comp(self, data, key, exType, ex):
		tName, val = data[key].typeName, data[key].get()
		if tName == "reference": tName = data[key].get(retCl=True).typeName
		self.assertEqual(tName, exType,
			'Unexpected datatype for "%s.%s" (got "%s")' % (data.name(), key, tName))
		self.subComp(val, ex, "%s.%s" % (data.name(),key))
	#enddef

class TestParse(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.basic = rpl.RPL()
		cls.basic.parse(os.path.join("tests", "rpls", "rpl.rpl"))

	def test_AndAnotherStatic(self):
		AndAnotherStatic = TestParse.basic.root["AndAnotherStatic"]
		self.checkLen(AndAnotherStatic, 1)
		self.check(AndAnotherStatic, "just", "literal", "because")

	def test_static0(self):
		x = TestParse.basic.root["static0"]
		self.checkLen(x, 8)
		self.check(x, "string", "string", "hi")
		self.check(x, "literal", "literal", "bye")
		self.check(x, "number", "number", 1)
		self.check(x, "hexnum", "hexnum", 0x2222)
		self.check(x, "multi", "string", "abcdefghijklmnopqrstuvwxyz")

		self.comp(x, "range", "range", map(
			lambda(x): ("number",x),
			[1,2,3,4,5,2,2,2,2,5,4,3]
		) + [("literal","x"), ("number", 1), ("hexnum", 0xa)])

		self.comp(x, "list", "list", [
			("string", "str"), ("literal", "lit"), ("number", 1),
			("hexnum", 0xbabe), ("range",map(lambda(x): ("number",x),
			[1,2,3]))
		])

		for y in x:
			self.assertEqual(y.name(), "sub", 'Unexpected sub "%s"' % y.name())
			self.checkLen(y, 1)
			self.check(y, "lit", "literal", ":D")

def RL(*x): return rpl.List(list(x))

class TestTypeCheck(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.basic = rpl.RPL()
		cls.basic.parse(os.path.join("tests", "rpls", "rpl.rpl"))

	def setUp(self):
		self.Str = rpl.String("hi")
		self.Lit = rpl.Literal("hi")
		self.Num = rpl.Number(1)
	#enddef

	def typeCheck(self, key, syn, data, expect):
		result = rpl.RPLTypeCheck(TestTypeCheck.basic, key, syn).verify(data)
		self.assertTrue((expect is None and result is None)
			or (result is not None and result.typeName == expect))
	#enddef

	def test_StrStr(self): self.typeCheck("StrStrTest", "string", self.Str, "string")
	def test_StrLit(self): self.typeCheck("StrLitTest", "string", self.Lit, "literal")
	def test_StrNum(self): self.typeCheck("StrNumTest", "string", self.Num, None)
	def test_OrNum(self): self.typeCheck("OrNumTest", "string|number", self.Num, "number")
	def test_ListNum(self): self.typeCheck("ListNumTest", "[number]", self.Num, None)
	def test_ListList(self): self.typeCheck("ListListTest", "[number]", RL(self.Num), "list")
	def test_ListBadList(self): self.typeCheck("ListBadListTest", "[number]", RL(self.Str), None)
	def test_LONum(self): self.typeCheck("LONumTest", "[string|number]", self.Num, None)
	def test_LOList(self): self.typeCheck("LOListTest", "[string|number]", RL(self.Num), "list")
	def test_Sublist(self): self.typeCheck("SublistTest", "[number,[number],number]", RL(self.Num,RL(self.Num),self.Num), "list")
	def test_SublistBad(self): self.typeCheck("SublistBadTest", "[number,[number],number]", RL(self.Num,RL(self.Str),self.Num), None)
	def test_OL1(self): self.typeCheck("OLTest1", "string|[number]", self.Str, "string")
	def test_OL2(self): self.typeCheck("OLTest2", "string|[number]", RL(self.Num), "list")
	def test_OLBad(self): self.typeCheck("OLBadTest", "string|[number]", self.Num, None)
	def test_OL3(self): self.typeCheck("OL3", "[number|[string],number]", RL(self.Num, self.Num), "list")
	def test_OL4(self): self.typeCheck("OL4", "[number|[string],number]", RL(RL(self.Str),self.Num), "list")
	def test_SSSSSL(self): self.typeCheck("SSSSSLTest", "[[[[[string]]]]]", RL(RL(RL(RL(RL(self.Str))))), "list")
	def test_Repeat1_1(self): self.typeCheck("Repeat1Test1", "[number]*", self.Num, "list")
	def test_Repeat1_2(self): self.typeCheck("Repeat1Test2", "[number]*", RL(self.Num), "list")
	def test_Repeat1_3(self): self.typeCheck("Repeat1Test3", "[number]*", RL(self.Num, self.Num), "list")
	def test_Repeat1_4(self): self.typeCheck("Repeat1Test4", "[number]*", self.Str, None)
	def test_Repeat2_1(self): self.typeCheck("Repeat2Test1", "[number]+", self.Num, None)
	def test_Repeat2_2(self): self.typeCheck("Repeat2Test2", "[number]+", RL(self.Num), "list")
	def test_Repeat2_3(self): self.typeCheck("Repeat2Test3", "[number]+", RL(self.Num, self.Num), "list")
	def test_Repeat3(self): self.typeCheck("Repeat3Test", "[number|string|list]+", RL(self.Str), "list")
	def test_Repeat4_1(self): self.typeCheck("Repeat4Test1", "[number,string]*", self.Num, "list")
	def test_Repeat4_2(self): self.typeCheck("Repeat4Test2", "[number,string]*", self.Str, "list")
	def test_Repeat4_3(self): self.typeCheck("Repeat4Test3", "[number,string]*", RL(self.Num, self.Str), "list")
	def test_Repeat4_4(self): self.typeCheck("Repeat4Test4", "[number,string]*", RL(self.Str, self.Num), None)
	def test_Repeat5_1(self): self.typeCheck("Repeat5Test1", "[number,string]!", self.Num, "list")
	def test_Repeat5_2(self): self.typeCheck("Repeat5Test2", "[number,string]!", self.Str, "list")
	def test_Repeat5_3(self): self.typeCheck("Repeat5Test3", "[number,string]!", RL(self.Num, self.Str), "list")
	def test_Repeat5_4(self): self.typeCheck("Repeat5Test4", "[number,string]!", RL(self.Str,self.Num), None)
	def test_Repeat5_5(self): self.typeCheck("Repeat5Test5", "[number,string]!", RL(self.Num, self.Str, self.Num, self.Str), None)
	def test_Repeat6_1(self): self.typeCheck("Repeat6Test1", "[number]~", self.Num, "number")
	def test_Repeat6_2(self): self.typeCheck("Repeat6Test2", "[number]~", RL(self.Num), "list")
	def test_Repeat7_1(self): self.typeCheck("Repeat7Test1", "[number].", self.Num, "number")
	def test_Repeat7_2(self): self.typeCheck("Repeat7Test2", "[number].", RL(self.Num), "list")
	def test_Repeat8_1(self): self.typeCheck("Repeat8Test1", "[number|^]", RL(RL(self.Num)), "list")
	def test_Repeat8_2(self): self.typeCheck("Repeat8Test2", "[^|number]", RL(RL(self.Num)), "list")
	def test_Repeat8_3(self): self.typeCheck("Repeat8Test3", "[^|number]", RL(RL(self.Str)), None)
	def test_Repeat8_4(self): self.typeCheck("Repeat8Test4", "[number|^]", RL(RL(RL(self.Num))), "list")
	# Matest_ke sure_doesn't infinitely recurse or anything here
	def test_Repeat8_5(self): self.typeCheck("Repeat8Test5", "[number|^]", RL(RL(RL(self.Str))), None)
	def test_Repeat8_6(self): self.typeCheck("Repeat8Test6", "[number|^]", RL(RL(RL(RL(RL(RL()))))), None)
	def test_Repeat9_1(self): self.typeCheck("Repeat9Test1", "[string,number]!0", self.Str, "list")
	def test_Repeat9_2(self): self.typeCheck("Repeat9Test2", "[string,number]!0", self.Num, None)
	def test_Repeat10_1(self): self.typeCheck("Repeat10Test1", "[string,number]+", RL(self.Str, self.Num), "list")
	def test_Repeat10_2(self): self.typeCheck("Repeat10Test2", "[string,number]+", RL(self.Str, self.Num, self.Str, self.Num), "list")
	def test_Repeat10_3(self): self.typeCheck("Repeat10Test3", "[string,number]+", RL(self.Str, self.Num, self.Str), None)
	def test_Repeat11_1(self): self.typeCheck("Repeat11Test1", "[string,number]+1", RL(self.Str), "list")
	def test_Repeat11_2(self): self.typeCheck("Repeat11Test2", "[string,number]+1", RL(self.Str, self.Num), "list")
	def test_Repeat11_3(self): self.typeCheck("Repeat11Test3", "[string,number]+1", RL(self.Str, self.Num, self.Str, self.Num), None)
	def test_Repeat11_4(self): self.typeCheck("Repeat11Test4", "[string,number]+1", RL(self.Str, self.Num, self.Num), "list")
	def test_Repeat11_5(self): self.typeCheck("Repeat11Test5", "[string,number]+1", RL(self.Num), None)
	def test_RO1(self): self.typeCheck("ROTest1", "[number]*|string", self.Num, "list")
	def test_RO2(self): self.typeCheck("ROTest2", "[number]*|string", RL(self.Num), "list")
	def test_RO3(self): self.typeCheck("ROTest3", "[number]*|string", self.Str, "string")
	def test_Heir1(self): self.typeCheck("HeirTest1", "range", rpl.Range([self.Num, self.Num]), "range")
	def test_Heir2(self): self.typeCheck("HeirTest2", "range", RL(self.Num, self.Num), "range")

class TestReferences(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.refers = rpl.RPL()
		cls.refers.parse(os.path.join("tests", "rpls", "references.rpl"))

	def test_stuff(self):
		x = TestReferences.refers.child("tests")
		self.check(x, "test1", "number", 1)
		self.comp(x, "test2", "list", [ ("literal", "+"), ("literal", "more"),
			("literal", "voluptuous"), ("list", [ ("literal", "he"), ("literal", "he"),
			("literal", "he") ]) ] )
		self.check(x, "test3", "literal", "+")
		self.check(x, "test4", "literal", "more")
		self.check(x, "test5", "literal", "voluptuous")
		self.comp(x, "test6", "list", [ ("literal", "he"), ("literal", "he"),
			("literal", "he") ])
		self.check(x, "test7", "literal", "he")
		self.check(x, "test8", "number", 1330494503)
		self.check(x, "test9", "number", 1)
		self.check(x, "test10", "number", 1)
		self.check(x, "test11", "number", 3)

		x = TestReferences.refers.child("ImaGParent").child("ImaParent").child("ImaToysRUsKid")
		self.check(x, "test1", "number", 3)
		self.check(x, "test2", "number", 2)


if __name__ == '__main__':
	unittest.main()

""" Ignore these for now
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
"""
