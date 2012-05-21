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

_timedTests = []

def timedTest(fn):
	def wrapper(self):
		start = time()
		fn(self)
		_timedTests.append((fn.__name__, time() - start))
	#enddef

	return wrapper
#enddef

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
		return self.subCheck(data[key], "%s.%s" % (data.name(), key), exType, exVal)

	def subComp(self, l1, l2, heir):
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
		self.subComp(val, ex, "%s.%s" % (data.name(), key))
	#enddef
#endclass

class TestParse(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.basic = rpl.RPL()
		cls.basic.parse(os.path.join("tests", "rpls", "rpl.rpl"))
	#enddef

	def test_AndAnotherStatic(self):
		AndAnotherStatic = TestParse.basic.root["AndAnotherStatic"]
		self.checkLen(AndAnotherStatic, 1)
		self.check(AndAnotherStatic, "just", "literal", "because")
	#enddef

	def test_static0(self):
		static0 = TestParse.basic.root["static0"]
		self.checkLen(static0, 8)
		self.check(static0, "string", "string", "hi")
		self.check(static0, "literal", "literal", "bye")
		self.check(static0, "number", "number", 1)
		self.check(static0, "hexnum", "hexnum", 0x2222)
		self.check(static0, "multi", "string", "abcdefghijklmnopqrstuvwxyz")

		self.comp(static0, "range", "range", map(
			lambda(x): ("number", x),
			[1, 2, 3, 4, 5, 2, 2, 2, 2, 5, 4, 3]
		) + [("literal", "x"), ("number", 1), ("hexnum", 0xa)])

		self.comp(static0, "list", "list", [
			("string", "str"), ("literal", "lit"), ("number", 1),
			("hexnum", 0xbabe), ("range", map(lambda(x): ("number", x),
			[1, 2, 3]))
		])

		for y in static0:
			self.assertEqual(y.name(), "sub", 'Unexpected sub "%s"' % y.name())
			self.checkLen(y, 1)
			self.check(y, "lit", "literal", ":D")
		#endfor
	#enddef
#endclass

def RL(*args): return rpl.List(list(args))

STR = rpl.String("hi")
LIT = rpl.Literal("hi")
NUM = rpl.Number(1)

class TypeCheckTestCase(object):
	def __init__(self, key, syn, data, expect):
		self.key = key
		self.syn = syn
		self.data = data
		self.expect = expect
	#enddef
#endclass

TYPE_CHECK_TEST_CASES = [
	TypeCheckTestCase("StrStr", "string", STR, "string"),
	TypeCheckTestCase("StrLit", "string", LIT, "literal"),
	TypeCheckTestCase("StrNum", "string", NUM, None),
	TypeCheckTestCase("OrNum", "string|number", NUM, "number"),
	TypeCheckTestCase("ListNum", "[number]", NUM, None),
	TypeCheckTestCase("ListList", "[number]", RL(NUM), "list"),
	TypeCheckTestCase("ListBadList", "[number]", RL(STR), None),
	TypeCheckTestCase("LONum", "[string|number]", NUM, None),
	TypeCheckTestCase("LOList", "[string|number]", RL(NUM), "list"),
	TypeCheckTestCase("Sublist", "[number,[number],number]", RL(NUM, RL(NUM), NUM), "list"),
	TypeCheckTestCase("SublistBad", "[number,[number],number]", RL(NUM, RL(STR), NUM), None),
	TypeCheckTestCase("OL_1", "string|[number]", STR, "string"),
	TypeCheckTestCase("OL_2", "string|[number]", RL(NUM), "list"),
	TypeCheckTestCase("OLBad", "string|[number]", NUM, None),
	TypeCheckTestCase("OL_3", "[number|[string],number]", RL(NUM, NUM), "list"),
	TypeCheckTestCase("OL_4", "[number|[string],number]", RL(RL(STR), NUM), "list"),
	TypeCheckTestCase("SSSSSL", "[[[[[string]]]]]", RL(RL(RL(RL(RL(STR))))), "list"),
	TypeCheckTestCase("Repeat1_1", "[number]*", NUM, "list"),
	TypeCheckTestCase("Repeat1_2", "[number]*", RL(NUM), "list"),
	TypeCheckTestCase("Repeat1_3", "[number]*", RL(NUM, NUM), "list"),
	TypeCheckTestCase("Repeat1_4", "[number]*", STR, None),
	TypeCheckTestCase("Repeat2_1", "[number]+", NUM, None),
	TypeCheckTestCase("Repeat2_2", "[number]+", RL(NUM), "list"),
	TypeCheckTestCase("Repeat2_3", "[number]+", RL(NUM, NUM), "list"),
	TypeCheckTestCase("Repeat3", "[number|string|list]+", RL(STR), "list"),
	TypeCheckTestCase("Repeat4_1", "[number,string]*", NUM, "list"),
	TypeCheckTestCase("Repeat4_2", "[number,string]*", STR, "list"),
	TypeCheckTestCase("Repeat4_3", "[number,string]*", RL(NUM, STR), "list"),
	TypeCheckTestCase("Repeat4_4", "[number,string]*", RL(STR, NUM), None),
	TypeCheckTestCase("Repeat5_1", "[number,string]!", NUM, "list"),
	TypeCheckTestCase("Repeat5_2", "[number,string]!", STR, "list"),
	TypeCheckTestCase("Repeat5_3", "[number,string]!", RL(NUM, STR), "list"),
	TypeCheckTestCase("Repeat5_4", "[number,string]!", RL(STR, NUM), None),
	TypeCheckTestCase("Repeat5_5", "[number,string]!", RL(NUM, STR, NUM, STR), None),
	TypeCheckTestCase("Repeat6_1", "[number]~", NUM, "number"),
	TypeCheckTestCase("Repeat6_2", "[number]~", RL(NUM), "list"),
	TypeCheckTestCase("Repeat7_1", "[number].", NUM, "number"),
	TypeCheckTestCase("Repeat7_2", "[number].", RL(NUM), "list"),
	TypeCheckTestCase("Repeat8_1", "[number|^]", RL(RL(NUM)), "list"),
	TypeCheckTestCase("Repeat8_2", "[^|number]", RL(RL(NUM)), "list"),
	TypeCheckTestCase("Repeat8_3", "[^|number]", RL(RL(STR)), None),
	TypeCheckTestCase("Repeat8_4", "[number|^]", RL(RL(RL(NUM))), "list"),
	# Matest_ke sure_doesn't infinitely recurse or anything here
	TypeCheckTestCase("Repeat8_5", "[number|^]", RL(RL(RL(STR))), None),
	TypeCheckTestCase("Repeat8_6", "[number|^]", RL(RL(RL(RL(RL(RL()))))), None),
	TypeCheckTestCase("Repeat9_1", "[string,number]!0", STR, "list"),
	TypeCheckTestCase("Repeat9_2", "[string,number]!0", NUM, None),
	TypeCheckTestCase("Repeat10_1", "[string,number]+", RL(STR, NUM), "list"),
	TypeCheckTestCase("Repeat10_2", "[string,number]+", RL(STR, NUM, STR, NUM), "list"),
	TypeCheckTestCase("Repeat10_3", "[string,number]+", RL(STR, NUM, STR), None),
	TypeCheckTestCase("Repeat11_1", "[string,number]+1", RL(STR), "list"),
	TypeCheckTestCase("Repeat11_2", "[string,number]+1", RL(STR, NUM), "list"),
	TypeCheckTestCase("Repeat11_3", "[string,number]+1", RL(STR, NUM, STR, NUM), None),
	TypeCheckTestCase("Repeat11_4", "[string,number]+1", RL(STR, NUM, NUM), "list"),
	TypeCheckTestCase("Repeat11_5", "[string,number]+1", RL(NUM), None),
	TypeCheckTestCase("RO_1", "[number]*|string", NUM, "list"),
	TypeCheckTestCase("RO_2", "[number]*|string", RL(NUM), "list"),
	TypeCheckTestCase("RO_3", "[number]*|string", STR, "string"),
	TypeCheckTestCase("Heir_1", "range", rpl.Range([NUM, NUM]), "range"),
	TypeCheckTestCase("Heir_2", "range", RL(NUM, NUM), "range"),
]

def injectTypeCheckTests(cls):
	"""
	Dynamically add the type check tests in TYPE_CHECK_TEST_CASES to a class.

	For use as a decorator, simply add @injectTypeCheckTests to the class.
	For every test in the test case list, it creates a method named test_foo,
	where foo is the key field of the test case object. Assumes that the given
	class has a method typeCheck which takes the test case parameters.
	"""
	import new
	def createTestMethod(test):
		def testFn(self):
			self.typeCheck(test.key, test.syn, test.data, test.expect)
		m = new.instancemethod(testFn, None, cls)
		setattr(cls, 'test_%s' % test.key, m)

	for test in TYPE_CHECK_TEST_CASES:
		createTestMethod(test)

	return cls
#enddef

@injectTypeCheckTests
class TestTypeCheck(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.basic = rpl.RPL()
		cls.basic.parse(os.path.join("tests", "rpls", "rpl.rpl"))
	#enddef

	def typeCheck(self, key, syn, data, expect):
		result = rpl.RPLTypeCheck(TestTypeCheck.basic, key, syn).verify(data)
		self.assertTrue((expect is None and result is None)
			or (result is not None and result.typeName == expect))
	#enddef
#endclass

class TestReferences(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.refers = rpl.RPL()
		cls.refers.parse(os.path.join("tests", "rpls", "references.rpl"))
	#enddef

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
	#enddef
#endclass

class TestExport(unittest.TestCase):
	@timedTest
	def test_export(self):
		astd = std.Standard()
		astd.parse(os.path.join("tests", "rpls", "data.rpl"))
		folder = os.path.join("tests", "rpls", "data")
		astd.Def("file", "test.rpl")
		astd.exportData(os.path.join(folder, "data.bin"), folder)
		# TODO: Compare test.rpl with data.rpl
	#enddef
#endclass

class TestImport(unittest.TestCase):
	@timedTest
	def test_import(self):
		astd = std.Standard()
		astd.parse(os.path.join("tests", "rpls", "data.rpl"))
		astd.Def("file", "data.rpl")
		folder = os.path.join("tests", "rpls", "data")
		astd.importData(os.path.join(folder, "test.bin"), folder)
		# TODO: Compare test.bin with data.bin
	#enddef
#endclass

if __name__ == '__main__':
	try:
		unittest.main()
	finally:
		for test, time in _timedTests:
			print 'time for %s: %.3fs' % (test, time)
