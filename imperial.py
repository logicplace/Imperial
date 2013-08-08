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

import os
import sys
import argparse
from rpl import rpl, helper
from time import time

debug = False

def main():
	global debug
	parser = argparse.ArgumentParser(
		description  = "Imperial Exchange by Wa (logicplace.com)\n"
		"Easily replace resources in ROMs (or other binary formats) by use of"
		" a standard descriptor format.",

		usage        = "Usage: %(prog)s [options] {-x | -i | -m} ROM RPL [Struct names...]\n"
		"       %(prog)s -h [RPL | lib]\n"
		"       %(prog)s -t [RPL] [-l libs] [-s Struct types...]",

		formatter_class=argparse.RawDescriptionHelpFormatter,
		add_help     = False,
	)
	action = parser.add_mutually_exclusive_group()
	action.add_argument("--help", "-h", "-?", #"/?", "/h",
		help    = argparse.SUPPRESS,
		action  = "store_true"
	)
	action.add_argument("--version", #"/v",
		help    = "Show version number and exit.",
		action  = "store_true"
	)
	action.add_argument("--import", "-i", #"/i",
		dest    = "importing",
		help    = "Import resources in the ROM via the descriptor.",
		nargs   = 2,
		metavar = ("ROM", "RPL")
	)
	action.add_argument("--export", "-x", #"/x",
		help    = "Export resources from the ROM via the descriptor.",
		nargs   = 2,
		metavar = ("ROM", "RPL")
	)
	action.add_argument("--makefile", "-m", "--binary", "-b", #"/m", "/b",
		help    = "Create a new file. This will overwrite an existing file.\n"
		"Implies -r",
		nargs   = 2,
		metavar = ("ROM", "RPL")
	)
	action.add_argument("--template", "-t", #"/t",
		help    = "Generate a descriptor skeleton for the given module.\n"
		'Use "rpl" to generate the basic one.\n'
		"If no destination is given, result is printed to stdout.",
		action  = "store_true"
	)
	action.add_argument("--run",
		help    = "Run a RPL without involving a ROM. Implies --romless",
		nargs   = 1,
		metavar = ("RPL")
	)
	parser.add_argument("--libs", "-l", #"/l",
		help    = "What libs to load for template creation.",
		nargs   = "*"
	)
	parser.add_argument("--structs", "-s", #"/s",
		help    = "What structs to include in the template.",
		nargs   = "*"
	)
	parser.add_argument("--romless", "-r", #"/r",
		help    = "Do not perform validations in ROM struct, and"
		" do not warn if there isn't a ROM struct.",
		action  = "store_true"
	)
	parser.add_argument("--blank",
		help    = "Run action without creating or modifying a ROM file.",
		action  = "store_true"
	)
	parser.add_argument("--define", "-d", #"/d",
		help    = "Define a value that can be referenced by @Defs.name\n"
		"Values are interpreted as RPL data, be aware of this in regards to"
		" strings vs. literals.",
		action  = "append",
		nargs   = 2,
		metavar = ("name", "value")
	)
	parser.add_argument("--folder", "-f", #"/f",
		help    = "Folder to export to, or import from. By default this is the"
		" current folder.",
		default = "."
	)
	parser.add_argument("--debug",
		help    = argparse.SUPPRESS,
		action  = "store_true"
	)
	parser.add_argument("args", nargs="*", help=argparse.SUPPRESS)

	if len(sys.argv) == 1:
		parser.print_help()
		return 0
	#endif

	args = parser.parse_args(sys.argv[1:])

	debug = args.debug

	# Windows help flag.
	if args.args and args.args[0] == "/?":
		args.help = True
		args.args.pop(0)
	#endif

	if args.help:
		if len(args.args) >= 1:
			if args.args[0][-3:] == "rpl":
				# Load a RPL file's help.
				thing = rpl.RPL()
				thing.parse(args.args[0], ["RPL"])
				rplStruct = thing.childrenByType("RPL")
				if not rplStruct: return 0
				help = rplStruct[0]["help"].get()

				# Abuse argparse's help generator.
				filehelp = argparse.ArgumentParser(
					description = help[0].get(),
					usage       = argparse.SUPPRESS
				)
				for x in help[1:]:
					defkey, defhelp = tuple([y.get() for y in x.get()])
					filehelp.add_argument("-d" + defkey, help=defhelp)
				#endfor
				filehelp.print_help()
			else:
				# Load a lib's help.
				tmp = getattr(__import__("rpl." + args.args[0], globals(), locals()), args.args[0])
				tmp.printHelp(args.args[1:])
			#endif
		else: parser.print_help()
	elif args.template:
		thing = rpl.RPL()
		# Load requested libs.
		if args.libs:
			rplStruct = rpl.StructRPL()
			rplStruct["lib"] = rpl.List(map(rpl.String, args.libs))
			thing.load(rplStruct)
		#endif
		structs = args.structs
		if structs and not args.romless: structs = ["ROM"] + structs
		print thing.template(structs)
	elif args.run:
		thing = rpl.RPL()

		thing.parse(args.run[0])

		# Do defines.
		if args.define:
			for x in args.define: thing.addDef(*x)
		#endif

		# Run RPL.
		start = time()
		thing.run(args.folder, args.args)
		print "Finished executing. Time taken: %.3fs" % (time() - start)
	else:
		# Regular form.
		thing = rpl.RPL()

		# Grab filenames.
		if args.importing:  romfile, rplfile = tuple(args.importing)
		elif args.export:   romfile, rplfile = tuple(args.export)
		elif args.makefile: romfile, rplfile = tuple(args.makefile)

		thing.parse(rplfile)

		if not args.romless and not args.makefile:
			romstream = helper.stream(romfile)
			roms = thing.childrenByType("ROM")
			for x in roms:
				fails = x.validate(romstream)
				if fails:
					print "Failed the following checks: %s" % helper.list2english([
						("%s[%i]" % fail
						if type(fail) is tuple else
						fail) for fail in fails
					])
					answer = "."
					while answer not in "yYnN": answer = raw_input("Continue anyway (y/n)? ")
					if answer in "nN": return 1
				#endif
			#endfor
		#endif

		# Do defines.
		if args.define:
			for x in args.define: thing.addDef(*x)
		#endif

		# Run imports.
		start = time()
		if args.importing:
			thing.importData(romstream, args.folder, args.args, args.blank)
			print "Finished %s." % ("blank import" if args.blank else "importing"),
			romstream.close()
		elif args.export:
			thing.exportData(romstream, args.folder, args.args, args.blank)
			print "Finished %s." % ("blank export" if args.blank else "exporting"),
			romstream.close()
		elif args.makefile:
			try: os.unlink(romfile)
			except OSError as err:
				if err.errno == 2: pass
				else:
					helper.err('Could not delete "%s": %s' % (romfile, err.strerror))
					return 1
				#endif
			#endtry
			thing.importData(romfile, args.folder, args.args, args.blank)
			print "Finished %s." % ("build test" if args.blank else "building"),
		#endif
		print "Time taken: %.3fs" % (time() - start)
	#endif
#enddef

if __name__ == "__main__":
	try: sys.exit(main())
	except (EOFError, KeyboardInterrupt):
		if debug: raise
		print "\nOperations terminated by user."
		sys.exit(0)
	except rpl.RPLError as err:
		if debug: raise
		helper.err(err)
		sys.exit(1)
	#endtry
#endif
