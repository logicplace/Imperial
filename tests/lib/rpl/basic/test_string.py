#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

#from rpl.rpl.basic import String
from rpl.rpl.exceptions import errors, warnings

@unittest.skip("not implemented")
class TestBasicString(unittest.TestCase):
	def setUp(self):
		self.string = String("basic")

	def test_get(self):
		self.assertEqual(self.string.get(), "basic")
		self.assertEqual(self.string.get("data"), "basic")

	def test_string(self):
		self.assertEqual(self.string.string(), "basic")
		self.assertEqual(self.string.string("data"), "basic")

	def test_number(self):
		self.assertRaises(errors.TypeError, self.string.number)
		self.assertRaises(errors.TypeError, self.string.number, "data")

	def test_list(self):
		self.assertRaises(errors.TypeError, self.string.list)
		self.assertRaises(errors.TypeError, self.string.list, "data")

	def test_length(self):
		self.assertEqual(self.string.number("length"), 5)
		self.assertEqual(self.string.get("length"), 5)

	def test_serialize(self):
		self.assertEqual(self.string.serialize(), "basic")

	def test_stringify(self):
		self.assertEqual(self.string.stringify(), "basic")

	# NOTE: str(String(...)) is tested in localization.

@unittest.skip("not implemented")
class TestStringStringCast(unittest.TestCase)
	def setUp(self):
		self.string = String(String("cast"))

	def test_cast(self):
		self.assertIs(self.string, self.string.resolve("data"))

@unittest.skip("not implemented")
class TestStringLengthReflection(unittest.TestCase)
	def setUp(self):
		self.string = String("reflect")

	def test_set_lower(self):
		string = self.string()
		self.assertWarns(warnings.TruncationWarning, string.set, "length", 1)
		self.assertEqual(string.number("length"), 1)
		self.assertEqual(string.string(), "r")

	def test_set_same(self):
		try:
			self.string.set("length", 7)
		except errors.AssertionError:
			self.fail("setting length to current value raised an AssertionError unexpectedly")

	def test_set_higher(self):
		string = self.string()
		string.set("length", 8)
		self.assertEqual(self.string.number("length"), 8)
		self.assertEqual(string.string(), "reflect")

@unittest.skip("not implemented")
class TestStringSize(unittest.TestCase)
	def setUp(self):
		self.string = String({
			"data": "sized",
			"size": 8,
		})

	def test_bad_size(self):
		self.assertRaises(errors.AssertionError, String, {
			"data": "sized",
			"size": 1,
		})

	def test_default_size(self):
		string = String("unsized")
		self.assertEqual(string.number("size"), 7)

		# Ensure that checking the size didn't make it fixed.
		string.set("smol")
		self.assertEqual(string.number("size"), 4)

	def test_size(self):
		self.assertEqual(self.string.number("size"), 8)

@unittest.skip("not implemented")
class TestStringPadding(unittest.TestCase)
	def setUp(self):
		string = self.default = String({
			"data": "padme",
			"size": 8,
			"length": 8,
		})
		self.left = string({ "padside": "left", "padding": 0 })
		self.both = string({ "padside": "both", "padding": 0 })
		self.lboth = string({ "padside": "lboth", "padding": 0 })
		# Some cases need padding to be defaulted here.
		self.right = string({ "padside": "right" })

	def test_default(self):
		self.assertEqual(self.default.string("padside"), "right")

	def test_default_padding(self):
		self.assertEqual(self.default.serialize(), b"padme\x00\x00\x00")

	def test_default_align(self):
		self.assertEqual(self.default.string("align"), "left")

	def test_pad_left(self):
		self.assertEqual(self.left.serialize(), b"\x00\x00\x00padme")

	def test_pad_left_align(self):
		self.assertEqual(self.left.string("align"), "right")

	def test_pad_both(self):
		self.assertEqual(self.both.serialize(), b"\x00padme\x00\x00")

	def test_pad_both_align(self):
		self.assertEqual(self.both.string("align"), "center")

	def test_pad_lboth(self):
		self.assertEqual(self.lboth.serialize(), b"\x00\x00padme\x00")

	def test_pad_lboth_align(self):
		self.assertEqual(self.lboth.string("align"), "rcenter")

	def test_pad_right(self):
		self.assertEqual(self.right({ "padding": 0 }).serialize(), b"padme\x00\x00\x00")

	def test_pad_right_align(self):
		self.assertEqual(self.right.string("align"), "left")

	def test_padding(self):
		self.assertEqual(self.right({ "padding": "." }).serialize(), b"padme...")

	@unittest.skip("not in specification")
	def test_stringify_default_padding(self):
		self.assertEqual(self.right.stringify(), "padme   ")

@unittest.skip("not implemented")
class TestStringUnencoded(unittest.TestCase)
	def setUp(self):
		self.string1 = String("unencoded")
		self.string2 = String("ｕｎｅｎｃｏｄｅｄ")

	def test_serialize_ok(self):
		self.assertEqual(self.string1.serialize(), b"unencoded")

	def test_serialize_fail(self):
		# Cannot encode characters above 255.
		# That is, unencoded strings act something like bin in terms of the data it handles.
		self.assertRaises(errors.EncodingError, self.string2.serialize)

	@unittest.skip("not in specification")
	def test_default(self):
		self.assertEqual(self.string1.string("encoding"), "unencoded")

@unittest.skip("not implemented")
class TestStringEncoded(unittest.TestCase)
	def setUp(self):
		self.string = String({ "encoding": "shift_jis" })

	def test_serialize_lower(self):
		self.assertEqual(self.string("encoded").serialize(), b"encoded")

	def test_serialize_upper(self):
		self.assertEqual(
			self.string("ｅｎｃｏｄｅｄ").serialize(),
			b"\x82\x85\x82\x8e\x82\x83\x82\x8f\x82\x84\x82\x85\x82\x84")

	def test_serialize_bmp(self):
		# TODO: Should creating it cause an error?
		string = self.string("🙅🙅🙅🙅🙅🙅💦")
		self.assertRaises(errors.EncodingError, string.serialize)

	def test_unserialize_lower(self):
		string = self.string()
		string.unserialize(b"encoded")
		self.assertEqual(string.string(), "encoded")

	def test_unserialize_upper(self):
		string = self.string()
		string.unserialize(b"\x82\x85\x82\x8e\x82\x83\x82\x8f\x82\x84\x82\x85\x82\x84")
		self.assertEqual(string.string(), "ｅｎｃｏｄｅｄ")

	def test_unserialize_error(self):
		string = self.string()
		self.assertRaises(errors.EncodingError, string.unserialize, b"\x82")


if __name__ == '__main__':
	unittest.main()
