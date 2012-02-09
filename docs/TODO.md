# New methodology #
## System ##
Mod inherits Std inherits Rpl

### Rpl Methods (ie. don't override) ###
* `parse(file)` -> reads and parses the RPL
* `regType(name, class)` -> Register a custom type

### Methods ###
* `__init__()` -> Register stuff
* `template(file)` -> export RPL template (generic one in Rpl, but more specific possible)
* `verify()` -> Compares ROM info to class
* `importData(file, folder, what)` -> Import what|* from folder into file (ROM)
* `exportData(file, folder, what)` -> Export what|* from file (ROM) into folder
* Optional: `gfxTransform(image, info, dir)` -> Transform image; dir=Import/Export

## RPL data ##
CustomStruct inherits RPLStruct
This basically just does all the instantiation of each data element when the
 RPL is read. It does all of the required/optional/non-existant checks and
 adding default values.

### RPLStruct Methods ###
* `__init__(rpl, name)` -> Store info
* `regKey(name, basic[, default])` -> Register a key for this struct. If no default is given, this key is required.
* `parse(obj)` -> Verify and store obj
* `__unicode__()` -> Output self as unicode string
* `__getitem__(key)` -> Return data for key if it exists
* `__setitem__(key, val)` -> Set val to key, casting val as necessary
* `fromBin(key, val)` -> Set val to key, assuming val is binary data

### Methods ###
* `__init__(rpl, name)` -> Call super init and register stuff
* `basic()` -> Return basic data (default is name)

CustomType inherits RPLData

### Methods ###
* `__init__(basic)` -> Interpret basic type and store to self
* `__unicode__()` -> Return type as a unicode string (when writing to RPL etc)

# Foremost #
* Convert std and min to modules loaded with __import__
* Create tests and anything needed for the testing framework
	- std.data
	- std.static
	- std.font
	- std.typeset
	- std.cond (post-implementation)
	- std.exec (post-implementation)
	- std.calc (post-implementation)
	- min.tilemap
	- min.spritemap
	- min.tile
	- min.sprite
	- min.tile3
	- min.sprite3
	- Translations (rotations/flips)
* New class to manage strings. Literal chars in strings can be utf8.
   $uXXXX is utf16. And $XX is binary. Interact with it like a string..

# etc #
* Make system to define what module to load/use based on a file defining the
  magic, ext, and/or mimetype to use. Attempts to guess in that order of
  precedence.
+ (T) Syntax, Parser) * - x i should be literals when by themselves
* rplref) Special "Caller" ref. Refers to calling struct. Passes caller to
           subsequent references.
+ (T) Parse/Range) Hex in ranges, $ can come before a number to indicate hex
* std) cond, exec, and calc structs:
   cond) Evaluates "expr". If result is true check if "truex" is defined,
         if so, exec that and return the result. If not return "true"
         (default value is 1). If result is false, do the same with "falsex"
         and "false".
   exec) Exec "exec" which is like cond/calc's expr except it assumes the format
         is [command,[expr]] where you don't need to nest expr. (Note: this
         applies to truex and falsex as well, they're basically shorthand for
         making this struct.) Also assumes concatenation in expr, use sublists
         for calculations.
   calc) Evaluates "expr" and returns the result.
   Note: return means basic data
   translit) Define a transliteration, useful for converting data/strings to the
             actual data needed. Keys "out" and "in" match by char to char.
             "in" must be non-unicode. They are short for outside/inside
             Pass the name of a translit struct in the format section of a data
             struct to use it to convert data. Basic data will always be the name
* Make "file" "folder" and "ext" keys globally useful and not managed by the
   structs themselves. "export" and "import" can be global too. Structs can define
   if they do manage data or not and what their default "ext" is. When a struct
   makes its filename it will combine all parent structs' folder values into its
   path, use its own filename as the name and bubble up for explicit ext (defaulting
   to its own default) if the ext is not already in the filename.
   Defaults: If a struct ex/imports then its name becomes "file", if it does not
   then its name becomes "folder". eg. static MyFolder { tilemap MyTilemapFile { ... } }
   Will save to ./MyFolder/MyTilemapFile.png (assuming png is tilemap's default ext)
* rplref) Able to reference internal stuff via .. or ! or something idk.
           Possibilities include: name, basic (just for explicitness, maybe it
           doesn't return the name as default), file (calculated path/filename/ext),
           link (looks up the key of the name that this key is in)
