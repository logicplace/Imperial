#!/usr/bin/env python3
#-*- coding:utf-8 -*-

# Copyright 2018 Sapphire Becker (logicplace.com)
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from rpl.rpl.helper import frozendict

class TestFrozenDict(unittest.TestCase):
	def setUp(self):
		self.data = frozendict({"a": 1, "b": "b"})

	def test_key(self):
		self.assertEqual(self.data["a"], 1)

	def test_keyerror(self):
		with self.assertRaises(KeyError):
			self.data["bd"]

	def test_seterror(self):
		# New key.
		with self.assertRaises(TypeError):
			self.data["bd"] = 1

		# Existing key.
		with self.assertRaises(TypeError):
			self.data["a"] = 1

	def test_copy(self):
		copy1 = frozendict(self.data, update={"a": 2, "c": 3})
		copy2 = frozendict({"a": 2, "c": 3}, update=self.data)

		self.assertEqual(copy1, {"a": 2, "b": "b", "c": 3})
		self.assertEqual(copy2, {"a": 1, "b": "b", "c": 3})

if __name__ == '__main__':
	unittest.main()
