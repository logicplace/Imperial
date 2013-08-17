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
from subprocess import Popen
try: import Tkinter as Tk, tkFileDialog, ttk
except ImportError: Tk = None

# Configuration file stuff...
from ConfigParser import ConfigParser, NoSectionError, NoOptionError
try: from xdg.BaseDirectory import xdg_config_home
except ImportError: xdg_config_home = None
try:
	from win32com.shell.shell import SHGetFolderPath
	from win32com.shell.shellcon import CSIDL_APPDATA
except ImportError: SHGetFolderPath = None

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
		metavar = ("name", "value"),
		default = []
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
		for x in args.define: thing.addDef(*x)

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
		for x in args.define: thing.addDef(*x)

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
		self.args, self.what, self.defs = args, [], dict(args.define)
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
			if not self.rpl.children:
				try: self.rpl.parse(rplfile)
				except (rpl.RPLError, helper.RPLInternal) as err: rplnote = unicode(err)
			#endif

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
			if not self.rpl.children:
				try: self.rpl.parse(rplfile)
				except (rpl.RPLError, helper.RPLInternal) as err: rplnote = unicode(err)
			#endif
			if self.rpl.children:
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
		#endif

		if not folder:
			# If we double clicked the executable, don't set the folder.
			cwd = os.path.realpath(os.getcwd())
			if os.path.dirname(os.path.realpath(sys.argv[0])) != cwd:
				# Otherwise default to cwd.
				folder = cwd
			#endif
		#endif

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
		editmenu = Tk.Menu(menubar, tearoff=0)
		editmenu.add_command(label="Defs struct", command=self.Defines)
		#editmenu.add_command(label="Edit mode", command=self.)
		editmenu.add_separator()
		editmenu.add_command(label="Edit ROM externally", command=self.EditROM)
		editmenu.add_command(label="Edit RPL externally", command=self.EditRPL)
		editmenu.add_separator()
		editmenu.add_command(label="Preferences", command=self.Preferences)
		menubar.add_cascade(label="Edit", menu=editmenu)
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
		)
		self.dirsec = Section(self.rpl, root, text="Resource Directory", entry=folder, isdir=True)

		# Import/Export buttons.
		self.ieframe = ieframe = Tk.Frame(root)
		impbut = Tk.Button(ieframe, text="Import", command=self.Import)
		impbut.grid(row=0, column=0, sticky="news")
		expbut = Tk.Button(ieframe, text="Export", command=self.Export)
		expbut.grid(row=0, column=1, sticky="news")
		self.ielbl = Note(ieframe)
		self.ielbl.grid(row=1, columnspan=2, sticky=Tk.N)
		ieframe.grid_columnconfigure(0, weight=1)
		ieframe.grid_columnconfigure(1, weight=1)
		ieframe.grid_rowconfigure(0, weight=1)
		ieframe.pack(fill=Tk.BOTH, expand=1)

		# Contine/Cancel buttons.
		self.ccframe = ccframe = Tk.Frame(root)
		contbut = Tk.Button(ccframe, text="Continue", command=self.Continue)
		contbut.grid(row=0, column=0, sticky="news")
		cnclbut = Tk.Button(ccframe, text="Cancel", command=self.Cancel)
		cnclbut.grid(row=0, column=0, sticky="news")
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

	def config(self, key=None):
		"""
		Return the configuration file location or values of keys.
		"""
		# First try a direct environment variable.
		try: fn = os.environ["IMPERIAL_CONFIG"]
		except KeyError:
			# Next, are we on Windows?
			if SHGetFolderPath: fn = SHGetFolderPath(0, CSIDL_APPDATA, None, 0) + "\\imperial.ini"
			# Or Linux? (God I hope this works on Mac, too!)
			elif xdg_config_home: fn = os.path.join(xdg_config_home, ".imperial")
			# Something else..? (Bonus points: it even fits 8.3)
			else: fn = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), "imperial" + os.extsep + "ini")
		#endtry
		if key is None: return fn
		else:
			config = ConfigParser()
			config.optionxform = str
			config.read(fn)
			if type(key) in [str, unicode]:
				try: ret = config.get("Imperial", key)
				except (NoSectionError, NoOptionError): ret = u""
			else:
				ret = {}
				try:
					for x in key: ret[x] = (config.get("Imperial", x))
				except (NoSectionError, NoOptionError):
					for x in key: ret[x] = u""
				#endtry
			return ret
		#endif
	#enddef

	def saveconfig(self, settings):
		config, fn = ConfigParser(), self.config()
		config.optionxform = str
		config.read(fn)
		try: new = dict(config.items("Imperial"))
		except (NoSectionError, NoOptionError): new = settings
		else: new.update(settings)
		buff = u"[Imperial]\n"
		for x in new.iteritems(): buff += u"=".join(map(unicode, x)) + u"\n"
		try: helper.writeTo(fn, buff)
		except helper.RPLInternal as err: return unicode(err)
		else: return u""
	#enddef

	###### GUI functions... ######
	# Edit menu:
	def Defines(self):
		dlg = Tk.Toplevel()
		dlg.title("Defines")
		dlg.grid_columnconfigure(0, weight=1)
		kvl = KVList(dlg, columns=("Key", "Value"))
		for k, v in self.defs.iteritems(): kvl.insert(Tk.END, k, unicode(v))
		kvl.grid(row=0, sticky="news")
		dlg.grid_rowconfigure(0, weight=1)

		def Apply(): self.defs = kvl.get()

		def OK():
			Apply()
			dlg.destroy()
		#enddef

		buttons = Tk.Frame(dlg)
		Tk.Button(buttons, text="Cancel", command=dlg.destroy).pack(side=Tk.RIGHT)
		Tk.Button(buttons, text="Apply", command=Apply).pack(side=Tk.RIGHT)
		Tk.Button(buttons, text="OK", command=OK).pack(side=Tk.RIGHT)
		Tk.Button(buttons, text="Add", command=kvl.insert).pack(side=Tk.RIGHT)
		buttons.grid(row=1, sticky="ews")
	#enddef

	def EditROM(self): Popen(self.config("EditROM").replace("%f", self.romsec.get()), shell=True)
	def EditRPL(self): Popen(self.config("EditRPL").replace("%f", self.rplsec.get()), shell=True)

	def Preferences(self):
		dlg = Tk.Toplevel()
		dlg.title("Preferences")
		dlg.grid_columnconfigure(0, weight=1)

		config = self.config({
			"EditROM": '',
			"EditRPL": 'notepad "%f"'
		})
		for x, v in config.iteritems():
			config[x] = StringVar()
			config[x].set(v)
		#endfor

		nb = ttk.Notebook(dlg)
		main = Tk.Frame(nb)
		main.grid_rowconfigure(0, pad=5)
		main.grid_rowconfigure(2, pad=5)
		main.grid_columnconfigure(1, weight=1)
		Tk.Label(main, text="Config file:").grid(row=0, column=0)
		Tk.Label(main, text=self.config()).grid(row=0, column=1)
		Tk.Label(main, text="Edit ROM:").grid(row=1, column=0)
		editrom = Tk.Entry(main, textvariable=config["EditROM"])
		editrom.grid(row=1, column=1, sticky="ew")
		Tk.Label(main, text="Edit RPL:").grid(row=2, column=0)
		editrpl = Tk.Entry(main, textvariable=config["EditRPL"])
		editrpl.grid(row=2, column=1, sticky="ew")
		nb.add(main, text="Main")

		nb.grid(row=0, sticky="news")
		dlg.grid_rowconfigure(0, weight=1)

		def Apply():
			err = self.saveconfig(config)
			errlbl.config(text=err)
			return not bool(err)
		#enddef

		def OK():
			if Apply(): dlg.destroy()
		#enddef

		buttons = Tk.Frame(dlg)
		Tk.Button(buttons, text="Cancel", command=dlg.destroy).pack(side=Tk.RIGHT)
		Tk.Button(buttons, text="Apply", command=Apply).pack(side=Tk.RIGHT)
		Tk.Button(buttons, text="OK", command=OK).pack(side=Tk.RIGHT)
		buttons.grid(row=1, sticky="ews")

		errlbl = Note(dlg)
		errlbl.grid(row=2, sticky="ews")
	#enddef

	# Help menu:
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

	# Execution:
	def Import(self, update=True):
		if update: self.UpdateRPL()
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

	def Export(self, update=True):
		if update: self.UpdateRPL()
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
		self.UpdateRPL()
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
		self.UpdateRPL()
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
		self.cont(False)
		self.args.romless = False
		self.romsec.note("")
	#enddef

	def Cancel(self):
		self.ccframe.pack_forget()
		self.ieframe.pack(fill=Tk.X)
		self.romsec.note("")
	#enddef

	def UpdateRPL(self):
		self.rpl.reset()
		try: self.rpl.parse(self.rplsec.get())
		except (rpl.RPLError, helper.RPLInternal) as err:
			self.rplsec.note(unicode(err))
		else:
			self.rplsec.note("")
			for x in self.defs.iteritems(): self.rpl.addDef(*x)
		#endtry
	#enddef
#enddef

class StringVar(Tk.StringVar):
	def __unicode__(self): return unicode(self.get())
#endclass

class Note(Tk.Label):
	def grid(self, **options):
		Tk.Label.grid(self, **options)
		if self.cget("text") == "": self.grid_remove()
	#enddef

	def pack(self, **options):
		Tk.Label.pack(self, **options)
		if self.cget("text") == "": self.pack_forget()
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
		self.entry.grid(row=0, column=0, sticky="ew")
		self.button = Tk.Button(self, text="Open", command=self.open)
		self.button.grid(row=0, column=1)
		self.wnote = Note(self, text=note)
		self.wnote.grid(row=1, columnspan=2, sticky="n")
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

class KVList(Tk.Frame):
	def __init__(self, master=None, columns=None, **options):
		Tk.Frame.__init__(self, master, **options)
		self.canvas = Tk.Canvas(self, background="#ffffff")
		self.table = Tk.Frame(self.canvas)
		self.table.grid_columnconfigure(0, weight=2)
		self.table.grid_columnconfigure(1, weight=8)
		self.col1lbl = Note(self.table, text=columns[0] if columns else None)
		self.col1lbl.grid(row=0, column=0, sticky="news")
		self.col2lbl = Note(self.table, text=columns[1] if columns else None)
		self.col2lbl.grid(row=0, column=1, sticky="news")
		self.canvas.pack(side=Tk.LEFT, fill=Tk.BOTH, expand=1)
		yscroll = Tk.Scrollbar(self, command=self.canvas.yview, orient=Tk.VERTICAL)
		yscroll.pack(side=Tk.RIGHT, fill=Tk.Y, expand=0)
		self.canvas.configure(yscrollcommand=yscroll.set)
		self.interior = self.canvas.create_window(0, 0, window=self.table, anchor=Tk.NW)
		self.canvas.bind('<Configure>', self._configcanvas)
		self.table.bind('<Configure>', self._configinterior)
		self.rows = []
	#enddef

	def _configcanvas(self, event):
		tmp = self.canvas.winfo_width()
		if self.table.winfo_reqwidth() != tmp:
			self.canvas.itemconfigure(self.interior, width=tmp)
		#endif
	#enddef

	def _configinterior(self, event):
		size = (self.table.winfo_reqwidth(), self.table.winfo_reqheight())
		self.canvas.config(scrollregion="0 0 %s %s" % size)
		if size[0] != self.canvas.winfo_width():
			self.canvas.config(width=size[0])
		#endif
	#enddef

	def config(self, columns=None, **options):
		if columns:
			self.col1lbl.config(text=columns[0])
			self.col2lbl.config(text=columns[1])
		#endif
		Tk.Frame.config(**options)
	#enddef

	def disable(self, index=Tk.ALL):
		if index == Tk.ALL:
			for i in self.rows: self.disable(i)
			return
		elif index == Tk.END: index = -1
		for x in self.rows[index]: x.config(state=DISABLED)
	#enddef

	def insert(self, index=Tk.END, key="", value=""):
		opts = {"relief": Tk.FLAT, "background": "#ffffff"}
		row = (Tk.Entry(self.table, width=8, **opts), Tk.Entry(self.table, width=30, **opts))
		row[0].insert(0, key)
		row[1].insert(0, value)
		if index == Tk.END: self.rows.append(row)
		else: self.rows.insert(row, index)
		self.updateGrid()
	#enddef

	def remove(self, index=Tk.END):
		if index == Tk.END: index = -1
		for x in self.rows[index]: x.destroy()
		self.rows.pop(index)
	#enddef

	def updateGrid(self):
		for index, row in enumerate(self.rows):
			row[0].grid(row=index + 1, column=0, sticky="ew", padx=1)
			row[1].grid(row=index + 1, column=1, sticky="ew")
		#endfor
	#enddef

	def get(self, key=None):
		if key is None:
			ret = {}
			for row in self.rows: ret[row[0].get()] = row[1].get()
			return ret
		else:
			for row in self.rows:
				if row[0].get() == key: return row[1].get()
			#endfor
		#endif
		return None
	#enddef

	def set(self, key, value=""):
		for row in self.rows:
			if row[0].get() == key:
				row[1].delete(0, Tk.END)
				row[1].insert(0, value)
				return True
			#endif
		#endfor
		return False
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
