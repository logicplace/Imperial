#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
Test cases for RPL.

NOTE: Timed test results only shown with "python -m tests.tests" Will fix later

The easiest way to run this is via "python -m unittest discover" from the
project root directory. Alternatively, you can use "python -m tests.tests" to
run this file specifically, but the former command will discover any other test
files in the project.
"""

import codecs
import os
import unittest
from time import time

from rpl import rpl, std, helper

_timedTests = []

def timedTest(fn):
	def wrapper(self):
		start = time()
		fn(self)
		_timedTests.append((
			self.__class__.__name__ + "." + fn.__name__,
			time() - start
		))
	#enddef

	return wrapper
#enddef

def read(fileName, mode):
	if type(fileName) is list: fileName = os.path.join(*fileName)
	if "b" in mode: f = open(fileName, mode)
	else: f = codecs.open(fileName, encoding="utf-8", mode="r")
	data = f.read()
	f.close()
	return data
#enddef

def list2english(lst, quote='"'):
	if not quote: quote = ''
	if len(lst) == 1: return quote + lst[0] + quote
	elif len(lst) == 2:
		return quote + lst[0] + quote + ' and ' + quote + lst[1] + quote
	else:
		return quote + (quote + ', ' + quote).join(lst[0:-1]) + quote + ' and ' + quote + lst[-1] + quote
	#endif
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
		#endif
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
			'Unexpected datatype for "%s.%s" Got: %s' % (data.name(), key, tName)
		)
		self.subComp(val, ex, "%s.%s" % (data.name(), key))
	#enddef
#endclass

class TestParse(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.basic = rpl.RPL()
		cls.basic.parse(os.path.join("tests", "rpls", "rpl.rpl"))
	#enddef

	def testRegressions(self):
		regression = TestParse.basic.root["regression"]
		self.comp(regression, "endoflistnospacenumber", "list", [
			("literal", "lit"), ("number", 1)
		])
	#enddef

	def testAndAnotherStatic(self):
		AndAnotherStatic = TestParse.basic.root["AndAnotherStatic"]
		self.checkLen(AndAnotherStatic, 1)
		self.check(AndAnotherStatic, "just", "literal", "because")
	#enddef

	def testStatic0(self):
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
	TypeCheckTestCase("ListList", "[number]", RL(NUM), ["number"]),
	TypeCheckTestCase("ListBadList", "[number]", RL(STR), None),
	TypeCheckTestCase("LONum", "[string|number]", NUM, None),
	TypeCheckTestCase("LOList", "[string|number]", RL(NUM), ["number"]),
	TypeCheckTestCase("Sublist", "[number,[number],number]", RL(NUM, RL(NUM), NUM), ["number", "list", "number"]),
	TypeCheckTestCase("SublistBad", "[number,[number],number]", RL(NUM, RL(STR), NUM), None),
	TypeCheckTestCase("OL_1", "string|[number]", STR, "string"),
	TypeCheckTestCase("OL_2", "string|[number]", RL(NUM), ["number"]),
	TypeCheckTestCase("OLBad", "string|[number]", NUM, None),
	TypeCheckTestCase("OL_3", "[number|[string],number]", RL(NUM, NUM), ["number", "number"]),
	TypeCheckTestCase("OL_4", "[number|[string],number]", RL(RL(STR), NUM), ["list", "number"]),
	TypeCheckTestCase("SSSSSL", "[[[[[string]]]]]", RL(RL(RL(RL(RL(STR))))), "list"),
	TypeCheckTestCase("Repeat1_1", "[number]*", NUM, ["number"]),
	TypeCheckTestCase("Repeat1_2", "[number]*", RL(NUM), ["number"]),
	TypeCheckTestCase("Repeat1_3", "[number]*", RL(NUM, NUM), ["number", "number"]),
	TypeCheckTestCase("Repeat1_4", "[number]*", STR, None),
	TypeCheckTestCase("Repeat2_1", "[number]+", NUM, None),
	TypeCheckTestCase("Repeat2_2", "[number]+", RL(NUM), ["number"]),
	TypeCheckTestCase("Repeat2_3", "[number]+", RL(NUM, NUM), ["number", "number"]),
	TypeCheckTestCase("Repeat3", "[number|string|list]+", RL(STR), ["string"]),
	TypeCheckTestCase("Repeat4_1", "[number,string]*", NUM, ["number"]),
	TypeCheckTestCase("Repeat4_2", "[number,string]*", STR, ["string"]),
	TypeCheckTestCase("Repeat4_3", "[number,string]*", RL(NUM, STR), ["number", "string"]),
	TypeCheckTestCase("Repeat4_4", "[number,string]*", RL(STR, NUM), None),
	TypeCheckTestCase("Repeat5_1", "[number,string]!", NUM, ["number"]),
	TypeCheckTestCase("Repeat5_2", "[number,string]!", STR, ["string"]),
	TypeCheckTestCase("Repeat5_3", "[number,string]!", RL(NUM, STR), ["number", "string"]),
	TypeCheckTestCase("Repeat5_4", "[number,string]!", RL(STR, NUM), None),
	TypeCheckTestCase("Repeat5_5", "[number,string]!", RL(NUM, STR, NUM, STR), None),
	TypeCheckTestCase("Repeat6_1", "[number]~", NUM, "number"),
	TypeCheckTestCase("Repeat6_2", "[number]~", RL(NUM), ["number"]),
	TypeCheckTestCase("Repeat7_1", "[number].", NUM, "number"),
	TypeCheckTestCase("Repeat7_2", "[number].", RL(NUM), ["number"]),
	TypeCheckTestCase("Repeat8_1", "[number|^]", RL(RL(NUM)), "list"),
	TypeCheckTestCase("Repeat8_2", "[^|number]", RL(RL(NUM)), "list"),
	TypeCheckTestCase("Repeat8_3", "[^|number]", RL(RL(STR)), None),
	TypeCheckTestCase("Repeat8_4", "[number|^]", RL(RL(RL(NUM))), "list"),
	# Make sure it doesn't infinitely recurse or anything here
	TypeCheckTestCase("Repeat8_5", "[number|^]", RL(RL(RL(STR))), None),
	TypeCheckTestCase("Repeat8_6", "[number|^]", RL(RL(RL(RL(RL(RL()))))), None),
	TypeCheckTestCase("Repeat9_1", "[string,number]!0", STR, ["string"]),
	TypeCheckTestCase("Repeat9_2", "[string,number]!0", NUM, None),
	TypeCheckTestCase("Repeat10_1", "[string,number]+", RL(STR, NUM), ["string", "number"]),
	TypeCheckTestCase("Repeat10_2", "[string,number]+", RL(STR, NUM, STR, NUM), ["string", "number", "string", "number"]),
	TypeCheckTestCase("Repeat10_3", "[string,number]+", RL(STR, NUM, STR), None),
	TypeCheckTestCase("Repeat11_1", "[string,number]+1", RL(STR), ["string"]),
	TypeCheckTestCase("Repeat11_2", "[string,number]+1", RL(STR, NUM), ["string", "number"]),
	TypeCheckTestCase("Repeat11_3", "[string,number]+1", RL(STR, NUM, STR, NUM), None),
	TypeCheckTestCase("Repeat11_4", "[string,number]+1", RL(STR, NUM, NUM), ["string", "number", "number"]),
	TypeCheckTestCase("Repeat11_5", "[string,number]+1", RL(NUM), None),
	TypeCheckTestCase("Repeat12_1", "[string,number,string|number]+1", RL(STR), None),
	TypeCheckTestCase("Repeat12_2", "[string,number,string|number]+1", RL(STR, NUM), ["string", "number"]),
	TypeCheckTestCase("Repeat12_3", "[string,number,string|number]+1", RL(STR, NUM, STR, NUM), ["string", "number", "string", "number"]),
	TypeCheckTestCase("Repeat12_4", "[string,number,string|number]+1", RL(STR, NUM, STR), ["string", "number", "string"]),
	TypeCheckTestCase("Repeat12_5", "[string,number,string|number]+1", RL(STR, NUM, NUM), ["string", "number", "number"]),
	TypeCheckTestCase("Repeat12_6", "[string,number,string|number]+1", RL(NUM), None),
	TypeCheckTestCase("RO_1", "[number]*|string", NUM, ["number"]),
	TypeCheckTestCase("RO_2", "[number]*|string", RL(NUM), ["number"]),
	TypeCheckTestCase("RO_3", "[number]*|string", STR, "string"),
	TypeCheckTestCase("Heir_1", "range", rpl.Range([NUM, NUM]), "range"),
	TypeCheckTestCase("Heir_2", "range", RL(NUM, NUM), "range"),
	TypeCheckTestCase("Discrete1_1", "string:(one, two, three)", rpl.String("one"), "string"),
	TypeCheckTestCase("Discrete1_2", "string:(one, two, three)", rpl.String("two"), "string"),
	TypeCheckTestCase("Discrete1_3", "string:(one, two, three)", rpl.String("three"), "string"),
	TypeCheckTestCase("Discrete1_4", "string:(one, two, three)", rpl.String("four"), None),
	TypeCheckTestCase("Discrete2_1", "string:(one, two)|number:(1, 2)", rpl.String("one"), "string"),
	TypeCheckTestCase("Discrete2_2", "string:(one, two)|number:(1, 2)", rpl.String("two"), "string"),
	TypeCheckTestCase("Discrete2_3", "string:(one, two)|number:(1, 2)", rpl.Number(1), "number"),
	TypeCheckTestCase("Discrete2_4", "string:(one, two)|number:(1, 2)", rpl.Number(2), "number"),
	TypeCheckTestCase("Discrete2_5", "string:(one, two)|number:(1, 2)", rpl.Number(5), None),
	TypeCheckTestCase("Bool1", "bool", rpl.String("true"), "bool"),
	TypeCheckTestCase("Bool2", "bool", rpl.String("1"), "bool"),
	TypeCheckTestCase("Bool3", "bool", rpl.String("on"), "bool"),
	TypeCheckTestCase("Bool4", "bool", rpl.Number(1), "bool"),
	TypeCheckTestCase("Bool5", "bool", rpl.String("false"), "bool"),
	TypeCheckTestCase("Bool6", "bool", rpl.String("0"), "bool"),
	TypeCheckTestCase("Bool7", "bool", rpl.String("off"), "bool"),
	TypeCheckTestCase("Bool8", "bool", rpl.Number(0), "bool"),
	TypeCheckTestCase("Bool9", "bool", rpl.String("butt"), None),
	TypeCheckTestCase("Bool10", "bool", rpl.Literal("true"), "bool"),
	TypeCheckTestCase("Size1", "size", rpl.String("byte"), "size"),
	TypeCheckTestCase("Size2", "size", rpl.String("short"), "size"),
	TypeCheckTestCase("Size3", "size", rpl.String("long"), "size"),
	TypeCheckTestCase("Size4", "size", rpl.String("double"), "size"),
	TypeCheckTestCase("Size5", "size", rpl.String("junk"), None),
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
		setattr(cls, 'test%s' % test.key, m)

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
		try: result = rpl.RPLTypeCheck(TestTypeCheck.basic, key, syn).verify(data)
		except rpl.RPLError: result = None
		if type(expect) is list:
			self.assertTrue(isinstance(result, rpl.List),
				'Expecting list but result was "%s"' % result.typeName
			)
			resultList = result.get()
			self.assertEqual(len(expect), len(resultList),
				'Expecting length of %i but result was length %i' % (
					len(expect), len(resultList)
				)
			)
			types = [x.typeName for x in resultList]
			self.assertEqual(expect, types,
				'Expecting type%s %s inside the list, but received type%s %s' % (
					's' if len(expect) > 1 else '',
					list2english(expect),
					's' if len(types) > 1 else '',
					list2english(types),
				)
			)
		else:
			self.assertTrue((expect is None and result is None)
				or (result is not None and result.typeName == expect),
				'Expecting "%s" but result was %s' % (
					expect, "an error" if result is None else '"%s"' % result.typeName
				)
			)
		#endif
	#enddef
#endclass

class TestReferences(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.refers = rpl.RPL()
		cls.refers.parse(os.path.join("tests", "rpls", "references.rpl"))
	#enddef

	def testStuff(self):
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

# Uhg, can't do this yet cause it'll only return the right data during the process
#class TestIOStatic(unittest.TestCase):
#	def testImport(self):
#		astd = std.Standard()
#		astd.parse(os.path.join("tests", "rpls", "iostatic.rpl"))
#		astd.importData("", "") # Nothing is imported
#		self.assertEqual(astd.child("Test")["name"].get(), "imp")
#	#enddef

#	def testExport(self):
#		astd = std.Standard()
#		astd.parse(os.path.join("tests", "rpls", "iostatic.rpl"))
#		astd.exportData("", "") # Nothing is imported
#		self.assertEqual(astd.child("Test")["name"].get(), "exp")
#	#enddef
##endclass

class IOTest(object):
	"""
	compares: Tuples of (expected data, result data) order is important because
	          the result data is deleted before the tests.
	"""
	def _xxport(self, direction, name, *compares):
		astd = std.Standard()
		astd.parse(os.path.join("tests", "rpls", name + ".rpl"))
		folder = os.path.join("tests", "rpls", name.split("_", 1)[0])

		# Delete files
		for file1, file2 in compares:
			try: os.unlink(os.path.join(folder, file2))
			except OSError: pass
#			except OSError as err:
#				if err.errno == 2: pass
#				raise
#			#endtry
		#endfor

		if direction == 0: astd.importData(os.path.join(folder, "test." + name + ".bin"), folder)
		else: astd.exportData(os.path.join(folder, name + ".bin"), folder)

		for file1, file2 in compares:
			# Compare test.bin with data.bin
			data = read([folder, file1], "rb")
			test = read([folder, file2], "rb")
			self.assertEqual(data, test, "Unexpected result from %s." %
				["import", "export"][direction]
			)
		#endfor
	#enddef

	def _import(self, name, *compares): return self._xxport(0, name, *compares)
	def _export(self, name, *compares): return self._xxport(1, name, *compares)
#enddef

class TestData(unittest.TestCase, IOTest):
	@timedTest
	def testImport(self): self._import("data", ("data.bin", "test.data.bin"))

	@timedTest
	def testExport(self): self._export("data", ("data.rpl", "test.data.rpl"))
#endclass

class TestMapString(unittest.TestCase, IOTest):
	@timedTest
	def testImport(self): self._import("map_string", ("map_string.bin", "test.map_string.bin"))

	@timedTest
	def testExport(self): self._export("map_string", ("map_string.rpl", "test.map_string.rpl"))
#endclass

class TestMapList(unittest.TestCase, IOTest):
	@timedTest
	def testImport(self): self._import("map_list", ("map_list.bin", "test.map_list.bin"))

	@timedTest
	def testExport(self): self._export("map_list", ("map_list.rpl", "test.map_list.rpl"))
#endclass

class TestTable(unittest.TestCase, IOTest):
	@timedTest
	def testImport(self): self._import("table", ("table.bin", "test.table.bin"))

	@timedTest
	def testExport(self): self._export("table", ("table.rpl", "test.table.rpl"))
#endclass

if __name__ == "__main__":
	try:
		unittest.main()
	finally:
		for test, time in _timedTests:
			print "Time for %s: %.3fs" % (test, time)
