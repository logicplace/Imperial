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

import sys
import argparse
from zlib import crc32
from rpl.rpl import RPL, RPLError, RPLTypeCheck, ROM, List, HexNum
from rpl.helper import err

def main():
	parser = argparse.ArgumentParser(
		description  = "CRC32 by Wa (logicplace.com)\n"
		"Allows you to retrieve CRC32s of sections of a file. Prints"
		" checksums to stdout in RPL format.\n"
		"Part of Imperial Exchange.",

		#usage        = "Usage: %(prog)s File Range...",

		formatter_class=argparse.RawTextHelpFormatter,
		add_help     = False,
		prefix_chars = "-/"
	)
	parser.add_argument("--help", "-h", "-?", "/?", "/h",
		help    = argparse.SUPPRESS,
		action  = "store_true"
	)
	parser.add_argument("file",
		help  = "Binary file to perform checksums on.",
		nargs = "?"
	)
	parser.add_argument("ranges",
		help  = "RPL range types to interpret and use as address scopes for checksums.\n"
		"If omitted, checksum entire file.",
		nargs = "*"
	)
	if len(sys.argv) == 1:
		parser.print_help
		return 0
	#endif
	args = parser.parse_args(sys.argv[1:])

	if args.help:
		parser.print_help()
		return 0
	elif not args.file:
		parser.error("File argument required.")
	#endif

	f = open(args.file, "rb")

	# Checksum entire file
	if not args.ranges:
		print u"crc32: %s" % unicode(HexNum(crc32(f.read()) & 0xFFFFFFFF))
		return 0
	#endif

	rpl = RPL()
	check = RPLTypeCheck(rpl, "check", "range")
	out = []
	# Checksum all ranges
	for x in args.ranges:
		try: data = check.verify(rpl.parseData(x))
		except RPLError:
			err("Ranges should be RPL range type.")
			return 1
		#endtry

		# Since nothing's going to process this list, we can leave x as is
		out.append(List([x, HexNum(ROM.getCRC(f, data))]))
	#endfor

	if len(out) == 1: print u"crc32: %s" % unicode(out[0])
	else: print u"crc32: %s" % unicode(List(out))
	return 0
#enddef

if __name__ == "__main__":
	try: sys.exit(main())
	except (EOFError, KeyboardInterrupt):
		print "\nOperations terminated by user."
		sys.exit(0)
	#endtry
#endif
