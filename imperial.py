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

import os, sys, argparse
from rpl import rpl, helper
from time import time

# Imports specific to the GUI.
import difflib, glob, webbrowser
try: import Tkinter as Tk, tkFileDialog
except ImportError: Tk = None

debug = False
TITLE = "Imperial Exchange"
VERSION = "0.9d Aug 15, 2013"

def main():
	global debug
	parser = argparse.ArgumentParser(
		description  = TITLE + " by Wa (logicplace.com)\n"
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
	action.add_argument("--gui",
		help    = "Open the GUI.",
		action  = "store_true"
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
	elif args.version:
		print TITLE + " - v" + VERSION
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
	elif args.importing or args.export or args.makefile:
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
				successes, fails = x.validate(romstream)
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
	else:
		return GUI().run(args)
	#endif
	return 0
#enddef

class GUI(object):
	def run(self, args):
		if Tk is None:
			print "Please install python-tk!"
			return 1
		#endif
		self.args, self.what = args, []
		romfile, rplfile, folder, self.rpl = "", "", "" if args.folder == "." else args.folder, rpl.RPL()
		romnote, rplnote = u"", u""
		if args.args:
			for x in args.args:
				if os.path.isdir(x): folder = x
				else:
					ext = os.path.basename(x).split(os.extsep)[-1]
					if ext == "rpl": rplfile = x
					else: romfile = x
				#endif
			#endfor
		#endif

		# Fancy guesswork~
		if not rplfile and romfile:
			# Look for a similarly named RPL file nearby.
			name = os.path.splitext(romfile)[0]
			search = [os.path.splitext(x)[0] for x in glob.glob("*.rpl") + glob.glob("*/*.rpl")]
			try: rplfile = difflib.get_close_matches(name, search)[0]
			except IndexError: pass
		#endif

		if not rplfile and folder:
			# Check if there's only one rpl file in the passed folder, and use that.
			rpls = glob.glob(os.path.join(folder, "*.rpl"))
			if len(rpls) == 1: rplfile = os.path.abspath(rpls[0])
		#endif

		if not rplfile:
			# Check if there's only one rpl file in the cwd, and use that.
			rpls = glob.glob("*.rpl")
			if len(rpls) == 1: rplfile = os.path.abspath(rpls[0])
		#endif

		if rplfile and not romfile:
			if not self.rpl.children: self.rpl.parse(rplfile)

			# Collect search area.
			top = os.path.dirname(rplfile)
			searches = [x for x in (
				# eg. CoolGame/ROM CoolGame/RPL
				glob.glob(os.path.join(top, "*")) +
				# eg. CoolGame/ROM CoolGame/dev/RPL
				glob.glob(os.path.join(os.path.dirname(top), "*")) +
				# eg. CoolGame/RPL CoolGame/build/ROM
				glob.glob(os.path.join(top, "*", "*"))
			) if os.path.isfile(x)]

			# Is there a ROM struct we can use for verification?
			rom = self.rpl.childrenByType("ROM")
			if rom:
				successes, curfails = 0, 0

				# Check files against ROM struct validation.
				for x in searches:
					stream = helper.stream(x)
					succs, fails = 0, 0
					for r in rom:
						s, f = r.validate(stream)
						succs += s
						fails += len(f)
					#endfor

					if succs > successes:
						romfile, successes, curfails = x, succs, fails
						if fails == 0: break
					#endif
				#endfor
				if romfile and curfails: romnote = u"There were %i ROM validation failures." % curfails
			else:
				# Filter out some known extensions, like archives...
				searches = [x for x in searches if (
					x.split(os.extsep)[-1] not in [
						"rpl", "zip", "rar", "tar", "gz", "7z", "lzh",
						"lz", "bz2", "lzma", "lha", "tgz"
					]
				)]

				# Look for a similarly named ROM file nearby.
				name = os.path.splitext(romfile)[0]
				noext = [os.path.split(x)[0] for x in searches]
				# Compare names without extensions.
				try: result = difflib.get_close_matches(name, noext)[0]
				except IndexError: pass
				# Look up name with extension and store as the romfile.
				else: romfile = searches[noext.index(result)]
			#endif
		#endif

		if rplfile and not folder:
			# It's probably nearby... Parse and look for directory structure.
			if not self.rpl.children: self.rpl.parse(rplfile)
			files = []
			for x in self.rpl.recurse():
				try: x.open
				except AttributeError: pass
				else:
					if x.manage([]): files.append(x)
				#endtry
			#endfor

			# Compare directory structure of RPL with subdirs.
			toplevel, best = os.path.abspath(os.path.dirname(rplfile)), 0
			for top, dirs, _ in os.walk(toplevel, followlinks=True):
				if top.replace(toplevel, "", 1).count(os.sep) >= 2: dirs = []
				ltop = list(os.path.split(top))
				success, fail = 0, 0
				for x in files:
					fn = x.open(ltop, ext="", retName=True)
					if os.path.exists(fn) or glob.glob(os.extsep.join((fn, "*"))):
						success += 1
					else: fail += 1
				#endif
				if success > best:
					folder, best = top, success
					if fail == 0: break
				#endif
			#endfor

			# If nothing else, this can start in the same directory as the RPL file.
			if not folder: folder = toplevel
		#endif

		if not folder:
			# If we double clicked the executable, don't set the folder.
			cwd = os.path.realpath(os.getcwd())
			if os.path.dirname(os.path.realpath(sys.argv[0])) != cwd:
				# Otherwise default to cwd.
				folder = cwd
			#endif
		#endif

		# RPL file is parsed when loaded.
		if rplfile and not self.rpl.children: self.rpl.parse(rplfile)

		####### Create GUI. #######
		root = Tk.Tk()
		root.title(TITLE)

		# Add menu.
		menubar = Tk.Menu(root)
		filemenu = Tk.Menu(menubar, tearoff=0)
		filemenu.add_command(label="Run", command=self.Run)
		filemenu.add_command(label="Make", command=self.Make)
		#filemenu.add_separator()
		#filemenu.add_command(label="New ROM", command=self.)
		#filemenu.add_command(label="New RPL", command=self.)
		filemenu.add_separator()
		filemenu.add_command(label="Exit", command=root.quit)
		menubar.add_cascade(label="File", menu=filemenu)
		#editmenu = Tk.Menu(menubar, tearoff=0)
		#editmenu.add_command(label="Edit mode", command=self.)
		#editmenu.add_separator()
		#editmenu.add_command(label="Edit ROM externally", command=self.EditROM)
		#editmenu.add_command(label="Edit RPL externally", command=self.EditRPL)
		#editmenu.add_separator()
		#editmenu.add_command(label="Preferences", command=self.Preferences)
		#menubar.add_cascade(label="Edit", menu=editmenu)
		helpmenu = Tk.Menu(menubar, tearoff=0)
		helpmenu.add_command(label="Help", command=self.Help)
		helpmenu.add_command(label="About", command=self.About)
		menubar.add_cascade(label="Help", menu=helpmenu)
		root.config(menu=menubar)

		# Add sections.
		self.romsec = Section(self.rpl, root, text="ROM", entry=romfile, note=romnote)
		self.rplsec = Section(
			self.rpl, root, text="RPL", entry=rplfile, note=rplnote,
			filetypes=[("RPL Files", "*.rpl")],
			validate="focusout", vcmd=self.UpdateRPL
		)
		self.dirsec = Section(self.rpl, root, text="Resource Directory", entry=folder, isdir=True)

		# Import/Export buttons.
		self.ieframe = ieframe = Tk.Frame(root)
		impbut = Tk.Button(ieframe, text="Import", command=self.Import)
		impbut.grid(row=0, column=0, sticky=Tk.N+Tk.W+Tk.S+Tk.E)
		expbut = Tk.Button(ieframe, text="Export", command=self.Export)
		expbut.grid(row=0, column=1, sticky=Tk.N+Tk.W+Tk.S+Tk.E)
		self.ielbl = Note(ieframe)
		self.ielbl.grid(row=1, columnspan=2, sticky=Tk.N)
		ieframe.grid_columnconfigure(0, weight=1)
		ieframe.grid_columnconfigure(1, weight=1)
		ieframe.grid_rowconfigure(0, weight=1)
		ieframe.pack(fill=Tk.BOTH, expand=1)

		# Contine/Cancel buttons.
		self.ccframe = ccframe = Tk.Frame(root)
		contbut = Tk.Button(ccframe, text="Continue", command=self.Continue)
		contbut.grid(row=0, column=0, sticky=Tk.N+Tk.W+Tk.S+Tk.E)
		cnclbut = Tk.Button(ccframe, text="Cancel", command=self.Cancel)
		cnclbut.grid(row=0, column=0, sticky=Tk.N+Tk.W+Tk.S+Tk.E)
		ccframe.grid_columnconfigure(0, weight=1)
		ccframe.grid_columnconfigure(1, weight=1)
		ccframe.grid_rowconfigure(0, weight=1)

		# All done, show it.
		root.mainloop()
	#enddef

	def validate(self, romfile, cont=None):
		if not self.args.romless:
			romstream = helper.stream(romfile)
			roms = self.rpl.childrenByType("ROM")
			totalfails = []
			for x in roms:
				successes, fails = x.validate(romstream)
				totalfails += fails
			#endfor
			if totalfails:
				self.romsec.note("Failed the following checks: %s" % helper.list2english([
					("%s[%i]" % fail
					if type(fail) is tuple else
					fail) for fail in totalfails
				]))
				if cont:
					self.ieframe.pack_forget()
					self.ccframe.pack(fill=Tk.X)
					self.cont = cont
				#endif
				return False
			#endif
		#endif
		return True
	#enddef

	# GUI functions...
	def Help(self): webbrowser.open("http://logicplace.com/imperial")
	def About(self):
		dlg = Tk.Toplevel()
		dlg.title("About")

		lbl = Tk.Message(dlg, text=(
			TITLE + " is developed by Wa\n"
			"Version: " + VERSION + "\n"
			"Website: http://logicplace.com/imperial"
		), width=500)
		lbl.pack()
	#enddef

	def Import(self):
		romfile = self.romsec.get()
		if not self.validate(romfile, self.Import): return
		start = time()
		try: self.rpl.importData(romfile, self.dirsec.get(), self.what, self.args.blank)
		except (rpl.RPLError, helper.RPLInternal) as err:
			self.ielbl.config(text=unicode(err))
		else:
			self.ielbl.config(text="Finished %s. Time taken: %.3fs" % (
				"blank import" if self.args.blank else "importing",
				time() - start
			))
		#endtry
	#enddef

	def Export(self):
		romfile = self.romsec.get()
		if not self.validate(romfile, self.Export): return
		start = time()
		try: self.rpl.exportData(romfile, self.dirsec.get(), self.what, self.args.blank)
		except (rpl.RPLError, helper.RPLInternal) as err:
			self.ielbl.config(text=unicode(err))
		else:
			self.ielbl.config(text="Finished %s. Time taken: %.3fs" % (
				"blank export" if self.args.blank else "exporting",
				time() - start
			))
		#endtry
	#enddef

	def Make(self):
		romfile = self.romsec.get()
		try: os.unlink(romfile)
		except OSError as err:
			if err.errno == 2: pass
			else:
				helper.err('Could not delete "%s": %s' % (romfile, err.strerror))
				return 1
			#endif
		#endtry
		start = time()
		try: self.rpl.importData(romfile, self.dirsec.get(), self.what, self.args.blank)
		except (rpl.RPLError, helper.RPLInternal) as err:
			self.ielbl.config(text=unicode(err))
		else:
			self.ielbl.config(text="Finished %s. Time taken: %.3fs" % (
				"test build" if self.args.blank else "building",
				time() - start
			))
		#endtry
	#enddef

	def Run(self):
		start = time()
		try: self.rpl.run(self.dirsec.get(), self.what)
		except (rpl.RPLError, helper.RPLInternal) as err:
			self.ielbl.config(text=unicode(err))
		else:
			self.ielbl.config(text="Finished executing. Time taken: %.3fs" % (time() - start))
		#endtry
	#enddef

	def Continue(self):
		self.ccframe.pack_forget()
		self.ieframe.pack(fill=Tk.X)
		self.args.romless = True
		self.cont()
		self.args.romless = False
		self.romsec.note("")
	#enddef

	def Cancel(self):
		self.ccframe.pack_forget()
		self.ieframe.pack(fill=Tk.X)
		self.romsec.note("")
	#enddef

	def UpdateRPL(self, *blah):
		# TODO: Should this backup/restore Defs?
		#defs = self.rpl.child("Defs")
		self.rpl.reset()
		try: self.rpl.parse(self.rplsec.get())
		except (rpl.RPLError, helper.RPLInternal) as err:
			self.rplsec.note(unicode(err))
		else: self.rplsec.note("")
		return True
	#enddef
#enddef

class Note(Tk.Label):
	def grid(self, **options):
		Tk.Label.grid(self, **options)
		if self.cget("text") == "": self.grid_remove()
	#enddef

	def config(self, **options):
		Tk.Label.config(self, **options)
		self.grid()
	#enddef
#enddef

class Section(Tk.LabelFrame):
	def __init__(self, top, master=None, entry=u"", note=u"", filetypes=[], isdir=False, validate=None, vcmd=None, **options):
		Tk.LabelFrame.__init__(self, master, **options)
		self.rpl = top
		self.entry = Tk.Entry(self, width=60, validate=validate, vcmd=vcmd)
		self.entry.insert(0, entry)
		if vcmd: self.entry.bind("<Return>", vcmd)
		self.entry.grid(row=0, column=0, sticky=Tk.W+Tk.E)
		self.button = Tk.Button(self, text="Open", command=self.open)
		self.button.grid(row=0, column=1)
		self.wnote = Note(self, text=note)
		self.wnote.grid(row=1, columnspan=2, sticky=Tk.N)
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(1, weight=1)
		self.pack(fill=Tk.X)

		self.isdir = isdir
		self.title = "Open %s %s" % (options["text"], "directory" if isdir else "file")
		self.filetypes = filetypes + [("All Files", "*")]
	#enddef

	def open(self):
		if self.isdir:
			filename = tkFileDialog.askdirectory(
				initialdir = self.entry.get(),
				title = self.title
			)
		else:
			filename = tkFileDialog.askopenfilename(
				filetypes = self.filetypes,
				initialdir = os.path.dirname(self.entry.get()),
				title = self.title
			)
		#endif
		self.entry.delete(0, Tk.END)
		self.entry.insert(0, filename)
	#enddef

	def get(self): return self.entry.get()

	def note(self, note):
		self.wnote.config(text=note)
		#self.wnote.pack()
	#enddef
#endclass

if __name__ == "__main__":
	try: sys.exit(main())
	except (EOFError, KeyboardInterrupt):
		if debug: raise
		print "\nOperations terminated by user."
		sys.exit(0)
	except (rpl.RPLError, helper.RPLInternal) as err:
		if debug: raise
		helper.err(err)
		sys.exit(1)
	#endtry
#endif
