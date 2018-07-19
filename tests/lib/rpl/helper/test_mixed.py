#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from rpl.rpl.helper import mixed

class TestMixed(unittest.TestCase):
	def setUp(self):
		self.data = mixed("a", "b", c = 0, d = 1)

	def test_index(self):
		self.assertEqual(self.data[0], "a")

	def test_notindexerror(self):
		with self.assertRaises(KeyError): self.data[2]

	def test_key(self):
		self.assertEqual(self.data["c"], 0)

	def test_keyerror(self):
		with self.assertRaises(KeyError):
			self.data["bd"]

	def test_str(self):
		data = mixed("a", "b", c = 0)
		self.assertEqual(str(data), "mixed('a', 'b', c = 0)")

		data = mixed("a", "b", **{"%": 1})
		self.assertEqual(str(data), "mixed('a', 'b', **{'%': 1})")

	def test_iter(self):
		for i, (k, v) in enumerate(self.data.items()):
			if isinstance(k, int):
				self.assertEqual(i, k)
			else:
				return

if __name__ == '__main__':
	unittest.main()
