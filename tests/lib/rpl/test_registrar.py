#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from imperial.rpl.registrar import Registrar, Key
from imperial.rpl.exceptions import errors

# Toys used for testing Registrar.
class Toy:
	registrar = None

	def __init__(self, data, *, source=None, name=None, parent=None):
		if not self.registrar:
			self.__class__.registrar = self.registrar = self.register()
		#endif

		self.data = {}
		self.parent = parent

		self.define(data, source)
	#enddef

	def __call__(self, data, *, source=None, name=None):
		return type(self)(data, source=source, name=name, parent=self.parent)
	#enddef

	def register(self):
		return Registrar()
	#enddef
#endclass

class ToyContext(Toy):
	def add_child(self, child):
		self.child[child.name] = child
	#enddef
#endclass

class ToyContext1(ToyContext): pass
class ToyContext2(ToyContext): pass

class ToyNumber(Toy):
	def define(self, data, source=None):
		if isinstance(data, dict):
			if "data" in data:
				self.define(data.pop("data"))
			#endif

			if data: raise errors.UndefinedKey()
		elif isinstance(data, (list, tuple)):
			raise errors.TypeError()
		elif isinstance(data, ToyNumber):
			self.value = data.get()
		else:
			try:
				self.value = int(data)
			except ValueError:
				raise errors.TypeError()
			#endtry
		#endif
	#enddef

	def get(self, key=None):
		if key is None or key == "data":
			return self.value
		else:
			raise KeyError(key)
		#endif
	#enddef
#enddef

CALCULATED = { "type": "calculated" }
class ToyString(Toy):
	value = None

	def register(self):
		return Registrar(keys = [
			Key("length", { "": ToyNumber }),
		])
	#enddef

	def define(self, data, source):
		try:
			length_key = self.registrar.key("length")
		except KeyError:
			raise errors.UndefinedKey()
		#endtry

		if isinstance(data, dict):
			if "data" in data:
				self.define(data.pop("data"))
			#endif

			if "length" in data:
				self.set("length", length_key.type(data.pop("length"), source=source))
			#endif

			if data: raise errors.UndefinedKey()
		elif isinstance(data, (list, tuple)):
			raise errors.TypeError()
		else:
			value = self.value = str(data)
			# Not how this normally works, obviously!!
			self.set("length", length_key.type(len(value), source=CALCULATED))
		#endif
	#enddef

	def get(self, key=None):
		if key is None or key == "data":
			return self.value
		elif key in self.data:
			return self.data[key].get()
		elif key == "length":
			v = self.value
			if v is None: return None
			l = len(v)
			self.data["length"] = ToyNumber(l, source=CALCULATED)
		else:
			raise KeyError(key)
		#endif
	#enddef

	def set(self, key, data):
		if key == "length":
			l = self.get("length")
			if l is not None and data.get() != l:
				raise errors.AssertionError()
			#endif
			self.data[key] = data
		elif key == "data":
			data = data.get()
			self.set("length", ToyNumber(len(data), source=CALCULATED))
			self.value = data
		else:
			raise errors.UndefinedKey()
		#endif
	#enddef
#endclass



class TestKey(unittest.TestCase):
	def setUp(self):
		self.key1 = Key("num", { "": ToyNumber })
		self.key2 = Key("numor1", { "": ToyNumber }, 1)

	def test_name(self):
		self.assertEqual(self.key1.name, "num")

	def test_type(self):
		t = self.key1.type
		self.assertIsInstance(t, ToyNumber)

		# Assert that it was cached.
		self.assertIsNotNone(self.key1._cached_type)

	def test_nodefault(self):
		self.assertFalse(self.key1.has_default())
		self.assertIsNone(self.key1.default(None))

	def test_default(self):
		self.assertTrue(self.key2.has_default())

		default = self.key2.default(None)
		self.assertIsInstance(default, ToyNumber)
		self.assertEqual(default.get(), 1)

	# TODO:
	#def test_copy(self)
	#def test_copywithdefault(self)


class TestRegistrar(unittest.TestCase):
	def setUp(self):
		self.string = ToyString("abc")
		self.registrar = self.string.registrar

	def test_exists(self):
		self.assertIsNotNone(self.registrar)
		self.assertIsNotNone(ToyString.registrar)

	def test_key(self):
		# Should not raise an exception...
		self.registrar.key("length")

	def test_badkey(self):
		with self.assertRaises(KeyError):
			self.registrar.key("uguu")

	def test_keys(self):
		# Should not raise an exception...
		r = self.registrar.keys("length")
		self.assertIsInstance(r, list)
		self.assertEqual(len(r), 1)

	def test_badkeys(self):
		with self.assertRaises(KeyError):
			self.registrar.keys("length", "uguu")

	def test_value(self):
		self.assertEqual(self.string.get(), "abc")

	def test_length(self):
		self.assertEqual(self.string.get("length"), 3)

	def test_typeerror(self):
		with self.assertRaises(errors.TypeError):
			ToyString({ "length": "abc" })

	# TODO:
	#def test_copy(self)
	#def test_copywithnewstuff(self)

if __name__ == '__main__':
	unittest.main()
