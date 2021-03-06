#!/usr/bin/env python
#-*- coding:utf-8 -*-

#
# Copyright (C) 2012 Sapphire Becker (http://logicplace.com)
#
# This file is part of Imperial Exchange.
#
# Imperial Exchange is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Imperial Exchange is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Imperial Exchange.  If not, see <http://www.gnu.org/licenses/>.
#

"""
Test cases for RPL.

Usage: python -m tests.tests [tests...]
For a list of tests see python -m tests.tests --help
"""

import os, sys, Image, codecs, unittest, shutil
from rpl import rpl, helper
from time import time

_timedTests = []

def timedTest(fn):
	def wrapper(self):
		start = time()
		fn(self)
		_timedTests.append((
			self.__class__.__name__ + "." + fn.__name__,
			(self.time if hasattr(self, "time") else time()) - start
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
			'Unexpected data type for "%s" (got "%s")' % (name, tName)
		)
		if not typeOnly:
			self.assertEqual(val, exVal,
				'Unexpected value for "%s" (got "%s")' % (name, val)
			)
		#endif
	#enddef

	def check(self, data, key, exType, exVal):
		return self.subCheck(data[key], "%s.%s" % (data.name, key), exType, exVal)

	def subComp(self, l1, l2, heir):
		self.assertEqual(len(l1), len(l2),
			'Incompatible lengths in "%s" (%i vs %i)' % (heir, len(l1), len(l2))
		)
		for i, x in enumerate(l1):
			n = heir + ("[%i]" % i)
			isList = isinstance(x, rpl.List)
			self.subCheck(x, n, *(l2[i]), typeOnly=isList)
			if isList: self.subComp(x.get(), l2[i][1], n)
		#endfor
	#enddef

	def comp(self, data, key, exType, ex):
		tName, val = data[key].typeName, data[key].get()
		if tName == "reference": tName = data[key].get(retCl=True).typeName
		self.assertEqual(tName, exType,
			'Unexpected datatype for "%s.%s" Got: %s' % (data.name, key, tName)
		)
		self.subComp(val, ex, "%s.%s" % (data.name, key))
	#enddef
#endclass

class TestParse(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.basic = rpl.RPL()
		cls.basic.parse(os.path.join("tests", "rpls", "rpl.rpl"))
	#enddef

	def testRegressions(self):
		regression = TestParse.basic.child("regression")
		self.comp(regression, "endoflistnospacenumber", "list", [
			("literal", "lit"), ("number", 1)
		])
		self.check(regression, "oneletter", "literal", "a")
	#enddef

	def testAndAnotherStatic(self):
		AndAnotherStatic = TestParse.basic.child("AndAnotherStatic")
		self.checkLen(AndAnotherStatic, 1)
		self.check(AndAnotherStatic, "just", "literal", "because")
	#enddef

	def testStatic0(self):
		static0 = TestParse.basic.child("static0")
		self.checkLen(static0, 9)
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

		self.check(static0, "escape", "string", "$")

		for y in static0:
			self.assertEqual(y.name, "sub", 'Unexpected sub "%s"' % y.name)
			self.checkLen(y, 1)
			self.check(y, "lit", "literal", ";D")
		#endfor

		regression = TestParse.basic.child("regression")
		self.comp(regression, "endoflistnospacenumber", "list", [
			("literal", "lit"), ("number", 1)
		])
		self.check(regression, "oneletter", "literal", "a")
		self.check(regression, "a", "literal", "one letter key")
		self.check(regression, "commentnospacenumber", "number", 1)
		self.check(regression, "endofstructnospacenumber", "number", 1)
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
		self.check(x, "test12", "literal", "hi")
		self.check(x, "test13", "literal", "hi")
		self.check(x, "test14", "literal", "hi")
		self.check(x, "test15", "literal", "hi")
		self.check(x, "test16", "literal", "he")
		self.check(x, "test17", "refstr", "hi world. Also 1")

		x = TestReferences.refers.child("ImaGParent").child("ImaParent").child("ImaToysRUsKid")
		self.check(x, "test1", "number", 3)
		self.check(x, "test2", "number", 2)
	#enddef
#endclass

class TestCalc(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		cls.refers = rpl.RPL()
		cls.refers.parse(os.path.join("tests", "rpls", "calc.rpl"))
	#enddef

	def testStuff(self):
		x = TestCalc.refers.child("tests")
		self.check(x, "test1", "math", 2)
		self.check(x, "test2", "math", 6)
		self.check(x, "test3", "math", 9)
		self.check(x, "test4", "math", 389)
		self.check(x, "test5", "math", 704)
		self.check(x, "test6", "math", 729)
		self.check(x, "test7", "math", -69)
		self.check(x, "test8", "math", 1)
		self.check(x, "test9", "math", 1)
		self.check(x, "test10", "math", 0xdeadbeef)
		self.check(x, "test11", "math", 0xbeadbabe)
		self.check(x, "test12", "math", 0777)
		self.check(x, "test13", "math", 041)
		self.check(x, "test14", "math", 0b00110011)
		self.check(x, "test15", "math", 0b11001100)
		self.check(x, "test16", "math", int("butts", 36))
	#enddef
#endclass

class TestRPL(RPLTestCase):
	@classmethod
	def setUpClass(cls):
		# The .rpl is relative to itself, however, we're not running from its
		# directory, like it expects.
		os.environ["RPL_INCLUDE_PATH"] = "tests/rpls"
		cls.refers = rpl.RPL()
		cls.refers.parse(os.path.join("tests", "rpls", "rplstruct.rpl"))
	#enddef

	def testLibs(self):
		# Check if data struct is available to see if the lib loaded.
		self.assertTrue("data" in TestRPL.refers.structs,
			"Expected to find data struct as available in root."
		)
	#enddef

	def testIncludes(self):
		# Check checkme to see if the include worked.
		checkme = TestRPL.refers.child("checkme")
		checkme2 = TestRPL.refers.child("checkme2")
		self.assertEqual(checkme["doiwork"].get(), "yes",
			'Expected checkme.doiwork to be "yes"'
		)
		self.assertEqual(checkme2["doiwork"].get(), "yes",
			'Expected checkme2.doiwork to be "yes"'
		)
	#enddef
#endclass

class TestROM(RPLTestCase):
	@timedTest
	def testROM(self):
		arpl = rpl.RPL()
		arpl.parse(os.path.join("tests", "rpls", "rom.rpl"))
		folder = os.path.join("tests", "rpls", "rom")
		arpl.importData(os.path.join(folder, "test.bin"), folder, nocreate=True)
	#enddef
#endclass

# Uhg, can't do this yet cause it'll only return the right data during the process.
#class TestIOStatic(unittest.TestCase):
#	def testImport(self):
#		arpl = rpl.RPL()
#		arpl.parse(os.path.join("tests", "rpls", "iostatic.rpl"))
#		arpl.importData("", "") # Nothing is imported
#		self.assertEqual(arpl.child("Test")["name"].get(), "imp")
#	#enddef

#	def testExport(self):
#		arpl = rpl.RPL()
#		arpl.parse(os.path.join("tests", "rpls", "iostatic.rpl"))
#		arpl.exportData("", "") # Nothing is imported
#		self.assertEqual(arpl.child("Test")["name"].get(), "exp")
#	#enddef
##endclass

class IOTest(RPLTestCase):
	"""
	compares: Tuples of (expected data, result data) order is important because
	          the result data is deleted before the tests.
	"""
	def _xxport(self, direction, name, ext, what, compares, defs={}):
		if type(what) is not list:
			compares = [what] + list(compares)
			what = None
		#endif

		arpl = rpl.RPL()
		if defs:
			for k, v in defs.iteritems(): arpl.addDef(k, v)
		#endif
		arpl.parse(os.path.join("tests", "rpls", name + ".rpl"))
		folder = os.path.join("tests", "rpls", name.split("_", 1)[0])

		# Delete files
		if direction != 2 and compares[0]:
			for file1, file2 in compares:
				try: os.unlink(os.path.join(folder, file2))
				except OSError as err:
					if err.errno == 2: pass
					else: raise
				#endtry
			#endfor
		#endif

		if direction == 0:   arpl.importData(os.path.join(folder, "test." + name + ext), folder, what)
		elif direction == 1: arpl.exportData(os.path.join(folder, name + ext), folder, what)
		elif direction == 2: arpl.run(folder, what)

		self.time = time()
		if not compares[0]: return
		for file1, file2 in compares:
			# Compare test.bin with data.bin
			exts = map(lambda x: x[1:].lower(),
				[os.path.splitext(file1)[1], os.path.splitext(file2)[1]]
			)
			# PIL supports a few other formats for r/w but I'm not too concerned.
			if helper.allIn(exts, ["bmp", "jpg", "jpeg", "png", "gif", "tif", "tiff"]):
				data = Image.open(os.path.join(folder, file1))
				test = Image.open(os.path.join(folder, file2))
				data, test = (
					"".join([chr(x[0]) + chr(x[1]) + chr(x[2]) for x in list(data.convert().getdata())]),
					"".join([chr(x[0]) + chr(x[1]) + chr(x[2]) for x in list(test.convert().getdata())])
				)
			elif helper.allIn(exts, ["rpl", "txt", "json", "csv"]):
				data = read([folder, file1], "rb").replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n").rstrip("\n")
				test = read([folder, file2], "rb").replace("\r\n", "\n").replace("\n\r", "\n").replace("\r", "\n").rstrip("\n")
			else:
				data = read([folder, file1], "rb")
				test = read([folder, file2], "rb")
			#endif
			self.assertEqual(data, test, "Unexpected result from %s." %
				["import", "export", "run"][direction]
			)
		#endfor
	#enddef

	def _import(self, name, ext, what=None, *compares, **kwargs): return self._xxport(0, name, ext, what, compares, defs=kwargs.get("defs", {}))
	def _export(self, name, ext, what=None, *compares, **kwargs): return self._xxport(1, name, ext, what, compares, defs=kwargs.get("defs", {}))
	def _run(self, name, what=None, *compares): return self._xxport(2, name, "", what, compares)
#enddef

class TestData(IOTest):
	@timedTest
	def testImportRPL(self): self._import("data", ".bin", ("data.bin", "test.data.bin"), defs={"ext": "rpl"})

	@timedTest
	def testExportRPL(self): self._export("data", ".bin", ("data.rpl", "test.data.rpl"), defs={"ext": "rpl"})

	@timedTest
	def testImportJSON(self): self._import("data", ".bin", ("data.bin", "test.data.bin"), defs={"ext": "json"})

	@timedTest
	def testExportJSON(self): self._export("data", ".bin", ("data.json", "test.data.json"), defs={"ext": "json"})

	@timedTest
	def testImportBIN(self): self._import("data", ".bin", ("data.bin", "test.data.bin"), defs={"ext": "bin"})

	@timedTest
	def testExportBIN(self): self._export("data", ".bin", ("data.bin", "test.data.bin"), defs={"ext": "bin"})
#endclass

class TestMapString(IOTest):
	@timedTest
	def testImport(self): self._import("map_string", ".bin", ("map_string.bin", "test.map_string.bin"))

	@timedTest
	def testExport(self): self._export("map_string", ".bin", ("map_string.rpl", "test.map_string.rpl"))
#endclass

class TestMapList(IOTest):
	@timedTest
	def testImport(self): self._import("map_list", ".bin", ("map_list.bin", "test.map_list.bin"))

	@timedTest
	def testExport(self): self._export("map_list", ".bin", ("map_list.rpl", "test.map_list.rpl"))
#endclass

class TestTable(IOTest):
	@timedTest
	def testImport(self): self._import("table", ".bin", ("table.bin", "test.table.bin"))

	@timedTest
	def testExport(self): self._export("table", ".bin", ("table.rpl", "test.table.rpl"))
#endclass

class TestGraphic(IOTest):
	@timedTest
	def testImport16(self): self._import("graphic", "16.bmp", ["Header", "BMP16"], ("graphic16.bmp", "test.graphic16.bmp"))
	@timedTest
	def testImport256(self): self._import("graphic", "256.bmp", ["Header", "BMP256"], ("graphic256.bmp", "test.graphic256.bmp"))
	@timedTest
	def testImport24b(self): self._import("graphic", "24b.bmp", ["Header", "BMP24b"], ("graphic24b.bmp", "test.graphic24b.bmp"))

	@timedTest
	def testExport16(self): self._export("graphic", "16.bmp", ["Header", "BMP16"], ("graphic.png", "test.graphic16.png"), ("graphic16.rpl", "test.graphic16.rpl"))
	@timedTest
	def testExport256(self): self._export("graphic", "256.bmp", ["Header", "BMP256"], ("graphic.png", "test.graphic256.png"), ("graphic256.rpl", "test.graphic256.rpl"))
	@timedTest
	def testExport24b(self): self._export("graphic", "24b.bmp", ["Header", "BMP24b"], ("graphic.png", "test.graphic24b.png"), ("graphic24b.rpl", "test.graphic24b.rpl"))
#endclass

class TestMin(IOTest):
	@timedTest
	def testImport(self): self._import("min", ".bin", ("min.bin", "test.min.bin"))

	@timedTest
	def testExport(self): self._export("min", ".bin", ("tile.bmp", "test.tile.bmp"), ("tilemap1.bmp", "test.tilemap1.bmp"), ("tilemap2.bmp", "test.tilemap2.bmp"))
#endclass

class TestTypeset(IOTest):
	@timedTest
	def testAll(self):
		# First, blank the test bmp.
		shutil.copy2(
			os.path.join("tests", "rpls", "typeset", "blank.typeset.png"),
			os.path.join("tests", "rpls", "typeset", "test.typeset.png")
		)

		# Now run the test.
		self._run("typeset", ("typeset.png", "test.typeset.png"))
	#enddef
#endclass

if __name__ == "__main__":
	run = sys.argv[1:]
	if not run: run = ["all"]
	elif run[0] in ["-?", "-h", "--help", "/?"]:
		print "\n".join((
			"all        - Run all tests (default).",
			"rpl        - Run all basic tests.",
			"std        - Run all std lib tests.",
			"min        - Run all min lib tests.",
			"parse      - Run .rpl parsing test.",
			"typecheck  - Run typechecking tests.",
			"references - Run reference tests.",
			"ROM        - Run ROM struct tests.",
			"RPL        - Run RPL struct tests.",
			"data       - Run data struct tests.",
			"graphic    - Run graphic struct tests.",
			"map        - Run map struct tests.",
			"maplist    - Run only map's list-type test.",
			"mapstring  - Run only map's string-type test.",
			"table      - Run table struct tests.",
		))
		sys.exit(0)
	#endif

	suite = []
	if helper.oneOfIn(["all", "rpl", "parse"], run): suite.append(TestParse)
	if helper.oneOfIn(["all", "rpl", "typecheck"], run): suite.append(TestTypeCheck)
	if helper.oneOfIn(["all", "rpl", "references"], run): suite.append(TestReferences)
	if helper.oneOfIn(["all", "rpl", "RPL"], run): suite.append(TestRPL)
	if helper.oneOfIn(["all", "rpl", "ROM"], run): suite.append(TestROM)
	if helper.oneOfIn(["all", "std", "data"], run): suite.append(TestData)
	if helper.oneOfIn(["all", "std", "map", "mapstring"], run): suite.append(TestMapString)
	if helper.oneOfIn(["all", "std", "map", "maplist"], run): suite.append(TestMapList)
	if helper.oneOfIn(["all", "std", "table"], run): suite.append(TestTable)
	if helper.oneOfIn(["all", "std", "graphic"], run): suite.append(TestGraphic)
	if helper.oneOfIn(["all", "std", "calc"], run): suite.append(TestCalc)
	if helper.oneOfIn(["all", "min"], run): suite.append(TestMin)
	if helper.oneOfIn(["all", "typeset"], run): suite.append(TestTypeset)
	try:
		errors = {}
		if suite:
			for x in suite:
				print "===== Tests for %s =====" % x.__name__.replace("Test", "")
				tmp = unittest.TextTestRunner().run(
					unittest.defaultTestLoader.loadTestsFromTestCase(x)
				)
				if tmp.errors: errors[x.__class__.__name__] = len(tmp.errors) + len(tmp.failures)
			#endfor
		else: unittest.main()
	finally:
		total, errs = 0.0, 0
		for x in errors:
			print "%i errors & failures in %s" % (errors[x], x)
			errs += errors[x]
		#endfor
		print "Total errors & failures: %i\n" % errs

		for test, time in _timedTests:
			print "Time for %s: %.3fs" % (test, time)
			total += time
		#endfor
		print "Total time for all tests: %.3fs" % total
	#endtry
#endif
