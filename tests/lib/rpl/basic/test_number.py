#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

#from rpl.rpl.basic import Number
from rpl.rpl.exceptions import errors, warnings

BIG = { "endian": "big" }
LITTLE = { "endian": "little" }

@unittest.skip("not implemented")
class TestBasicNumber(unittest.TestCase):
	def setUp(self):
		self.number = Number(123)

	def test_get(self):
		self.assertEqual(self.number.get(), 123)
		self.assertEqual(self.number.get("data"), 123)

	def test_string(self):
		self.assertRaises(errors.TypeError, self.number.string)
		self.assertRaises(errors.TypeError, self.number.string, "data")

	def test_number(self):
		self.assertEqual(self.number.number(), 123)
		self.assertEqual(self.number.number("data"), 123)

	def test_list(self):
		self.assertRaises(errors.TypeError, self.number.list)
		self.assertRaises(errors.TypeError, self.number.list, "data")

@unittest.skip("not implemented")
class TestNumberNumberCast(unittest.TestCase)
	def setUp(self):
		self.number = Number(Number(457))

	def test_cast(self):
		self.assertIs(self.number, self.number.resolve("data"))

@unittest.skip("not implemented")
class TestBits(unittest.TestCase):
	def setUp(self):
		self.number = Number({
			"data": 0x0c13,
			"size": 2,
		})

	def test_length(self):
		self.assertEqual(len(self.number.list("bits")), 2*8)

	def test_bits(self):
		self.assertEqual([x.number() for x in self.number.list("bits")], [
			1, 1, 0, 0,
			1, 0, 0, 0,
			0, 0, 1, 1,
			0, 0, 0, 0,
		])

@unittest.skip("not implemented")
class TestSerializationKeys(unittest.TestCase):
	def setUp(self):
		self.default = Number(123)
		self.defined = Number({
			"size": 1,
			"sign": "signed",
			"ending": "big",
		})

	def test_default_size(self):
		self.assertEqual(self.default.number("size"), 4)

	def test_default_sign(self):
		self.assertEqual(self.default.string("sign"), "unsigned")

	def test_default_endian(self):
		self.assertEqual(self.default.string("endian"), "little")

	def test_defined_size(self):
		self.assertEqual(self.defined.number("size"), 1)

	def test_defined_sign(self):
		self.assertEqual(self.defined.string("sign"), "signed")

	def test_defined_endian(self):
		self.assertEqual(self.defined.string("endian"), "big")

	# TODO: test_bad_sign, test_bad_endian

@unittest.skip("not implemented")
class TestSerializeNumber(unittest.TestCase):
	def setUp(self):
		signed = Number({
			"size": 2,
			"sign": "signed",
		})
		unsigned = Number({
			"size": 2,
			"sign": "unsigned",
		})

		self.signed_big = signed(BIG)
		self.signed_little = signed(LITTLE)
		self.unsigned_big = unsigned(BIG)
		self.unsigned_little = unsigned(LITTLE)


	def test_serialize_signed_big_1(self):
		self.assertEqual(self.signed_big(1).serialize(), b"\x00\x01")

	def test_serialize_signed_big_256(self):
		self.assertEqual(self.signed_big(256).serialize(), b"\x01\xff")

	@unittest.skip("not in specification")
	def test_serialize_signed_big_65534(self):
		self.assertEqual(self.signed_big(65534).serialize(), b"\xff\xfe")

	def test_serialize_signed_big_neg2(self):
		self.assertEqual(self.signed_big(-2).serialize(), b"\xff\xfe")


	def test_serialize_signed_little_1(self):
		self.assertEqual(self.signed_little(1).serialize(), b"\x01\x00")

	def test_serialize_signed_little_256(self):
		self.assertEqual(self.signed_little(256).serialize(), b"\xff\x01")

	@unittest.skip("not in specification")
	def test_serialize_signed_little_65534(self):
		self.assertEqual(self.signed_little(65534).serialize(), b"\xfe\xff")

	def test_serialize_signed_little_neg2(self):
		self.assertEqual(self.signed_little(-2).serialize(), b"\xfe\xff")


	def test_serialize_unsigned_big_1(self):
		self.assertEqual(self.unsigned_big(1).serialize(), b"\x00\x01")

	def test_serialize_unsigned_big_256(self):
		self.assertEqual(self.unsigned_big(256).serialize(), b"\x01\xff")

	def test_serialize_unsigned_big_65534(self):
		self.assertEqual(self.unsigned_big(65534).serialize(), b"\xff\xfe")

	@unittest.skip("not in specification")
	def test_serialize_unsigned_big_neg2(self):
		self.assertEqual(self.unsigned_big(-2).serialize(), b"\xff\xfe")


	def test_serialize_unsigned_little_1(self):
		self.assertEqual(self.unsigned_little(1).serialize(), b"\x01\x00")

	def test_serialize_unsigned_little_256(self):
		self.assertEqual(self.unsigned_little(256).serialize(), b"\xff\x01")

	def test_serialize_unsigned_little_65534(self):
		self.assertEqual(self.unsigned_little(65534).serialize(), b"\xfe\xff")

	@unittest.skip("not in specification")
	def test_serialize_unsigned_little_neg2(self):
		self.assertEqual(self.unsigned_little(-2).serialize(), b"\xfe\xff")


	def test_serialize_error_too_big(self):
		self.assertRaises(errors.DataLossError, self.unsigned_little(0x01ffff).serialize)


	def test_unserialize_signed_big_00f0(self):
		number = self.signed_big()
		number.unserialize(b"\x00\xf0")
		self.assertEqual(number.number(), 240)

	def test_unserialize_signed_big_f000(self):
		number = self.signed_big()
		number.unserialize(b"\xf0\x00")
		self.assertEqual(number.number(), -4096)


	def test_unserialize_signed_little_00f0(self):
		number = self.signed_little()
		number.unserialize(b"\x00\xf0")
		self.assertEqual(number.number(), -4096)

	def test_unserialize_signed_little_f000(self):
		number = self.signed_little()
		number.unserialize(b"\xf0\x00")
		self.assertEqual(number.number(), 240)


	def test_unserialize_unsigned_big_00f0(self):
		number = self.unsigned_big()
		number.unserialize(b"\x00\xf0")
		self.assertEqual(number.number(), 240)

	def test_unserialize_unsigned_big_f000(self):
		number = self.unsigned_big()
		number.unserialize(b"\xf0\x00")
		self.assertEqual(number.number(), 61440)


	def test_unserialize_unsigned_little_00f0(self):
		number = self.unsigned_little()
		number.unserialize(b"\x00\xf0")
		self.assertEqual(number.number(), 61440)

	def test_unserialize_unsigned_little_f000(self):
		number = self.unsigned_little()
		number.unserialize(b"\xf0\x00")
		self.assertEqual(number.number(), 240)


	def test_unserialize_ignore_extraneous(self):
		number = self.signed_big()
		number.unserialize(b"\xf0\x00\xe8")
		self.assertEqual(number.number(), -4096)

@unittest.skip("not implemented")
class TestStringification(unittest.TestCase):
	def setUp(self):
		self.twohundie = Number({
			"data": 200
		})
		self.twokay = Number({
			"data": 2000
		})
		self.twentybilsome = Number({
			"size": 5,
			"data": 20011000081,
		})
		self.sequence = Number({
			"size": 8,
			"data": 131211109876543210
		})

		comma = self.comma = Number.Pretty({ "form": "comma" })
		japanese = self.japanese = Number.Pretty({ "form": ["japanese", "kanji"] })
		roman = self.roman = Number.Pretty({ "form": ["roman", "ascii", "upper"] })

		self.comma200    = self.twohundie({ "pretty": comma })
		self.japanese200 = self.twohundie({ "pretty": japanese })
		self.roman200    = self.twohundie({ "pretty": roman })

		self.comma2k    = self.twokay({ "pretty": comma })
		self.japanese2k = self.twokay({ "pretty": japanese })
		self.roman2k    = self.twokay({ "pretty": roman })

		self.comma20b    = self.twentybilsome({ "pretty": comma })
		self.japanese20b = self.twentybilsome({ "pretty": japanese })
		self.roman20b    = self.twentybilsome({ "pretty": roman })

		self.comma100q    = self.sequence({ "pretty": comma })
		self.japanese100q = self.sequence({ "pretty": japanese })

		self.roman1999 = Number({
			"data": 1999,
			"pretty": roman,
		})

	def test_str(self):
		self.assertEqual(str(self.twentybilsome), "20011000081")
		self.assertEqual(str(self.comma20b), "20011000081")
		self.assertEqual(str(self.japanese20b), "20011000081")
		self.assertEqual(str(self.roman20b), "20011000081")

	def test_stringify_comma(self):
		self.assertEqual(self.comma200.stringify(), "200")
		self.assertEqual(self.comma2k.stringify(), "2,000")
		self.assertEqual(self.comma20b.stringify(), "20,011,000,081")
		self.assertEqual(self.comma100q.stringify(), "131,211,109,876,543,210")

	def test_stringify_japanese_kanji(self):
		self.assertEqual(self.japanese200.stringify(), "二百") # 200
		self.assertEqual(self.japanese2k.stringify(), "二千") # 2000
		self.assertEqual(self.japanese20b.stringify(), "二百億千百万八十一") # 200,1100,0081
		self.assertEqual(self.japanese100q.stringify(), "十三京千二百十一兆千九十八億七千六百五十四万三千二百十") # 13,1211,1098,7654,3210

	def test_stringify_roman_ascii_upper(self):
		self.assertEqual(self.roman200.stringify(), "CC")
		self.assertEqual(self.roman2k.stringify(), "MM")
		self.assertEqual(self.roman20b.stringify(), 20011000 * "M" + "LCCCI")
		self.assertEqual(self.roman1999.stringify(), "MCMXCIX")


	def test_parse_comma(self):
		number = Number()
		number.parse("131,211,109,876,543,210")
		self.assertEqual(number.number(), 131211109876543210)

	def test_parse_japanese_kanji(self):
		number = self.japanese()
		number.parse("十三京千二百十一兆千九十八億七千六百五十四万三千二百十")
		self.assertEqual(number.number(), 131211109876543210)

	def test_parse_roman_ascii_upper(self):
		number = self.roman()
		number.parse("MCMXCIX")
		self.assertEqual(number.number(), 1999)

	# TODO: All number forms I guess.


if __name__ == '__main__':
	unittest.main()
