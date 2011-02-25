Graphics Changer by Wa (logicplace.com) - v7
Requires clargs library, get it here: http://logicplace.com/pc/projects/clargs.py

See gfxchgr.py --help for basic usage info.

rpl.lang is a syntax file for gEdit for these descriptor files
Hopefully someone will make a Notepad++ one for me too!

If you link gfxchgr in /bin or something, you can set the environment variable
GFXCHGR_DIR to the path where its resources are.

=== Descriptor Format ===
There are two types of entries possible, a key and a struct.
Structs have the form of:
TYPE NAME {
}
And keys have the form of:
KEY: VALUE

Spacing is generally ignored (except inside a value, of course).
If spacing is necessary on the left or right of a value, use quotes.

Struct name is optional, it's only useful for root structs.

Substructs inherit key/values from their parents.

Values can be numbers, strings, ranges, references, or lists of those.
0129 = Number
$1280ab839 = Number in hexadecimal
Blah blah blah = String
"Blah blah blah" = String
"Blah blah $0a" = String with a character in it that's represented by hex
"0129" = String
[0,0] = List of two numbers
0-1 = A range of [0,1]
0-3:6-7 = A range of [0,1,2,3,6,7]
1-2:4*5 = A range of [1,2,4,4,4,4,4]
1:i:3:x = A range of [1,i,3,x]
@Example = A reference to a struct named Example, will return its basic value
@Example.test = ^, will return the value of Exmaple's test key
@Example.test[0] = ^, implies the test key is a list, and returns that list's
	first element

A basic value is determined by the type of the struct. If the struct does not
define a basic value, the struct's name is returned instead. Unless stated 
otherwise, it may not be a good idea to rely on it returning the name.

You may also use a keyword as a value:
false = 0
true = 1
black = $000000
white = $ffffff
red = $ff0000
blue = $00ff00
green = $0000ff
yellow = $ffff00
magenta = $ff00ff
pink = magenta
cyan = $00ffff
gray = $a5a5a5
byte = 1
short = 2
long = 4
double = 8

Lists can span multiple lines, when it does, a newline implies separation so
that a comma isn't necessary.
Similarly, you can place multiple key/value pairs on the same line, however
it's a good idea to use quotes for strings in this mode!

Strings must be in quotes if they meet any of these conditions:
* Starts or ends with spacing.
* Starts with a [
* Contains a , or #
* Is entirely numbers, hyphens, or colons
* Is a keyword
* Contains no characters

You may use $xx to denote a character in a string by its hexadecimal value.
To use a literal $, use $$
FYI newline is $0a, double quote is $22

Graphics files can be pretty much any image format. (Any supported by PIL.)

You may add line comments with #
There are no inline/muliline comments.

== Transposing ==
When you transpose an image, it will work oppositely based on whether importing
or exporting, so that it will end up the same. Here's a quick run down:
= On export =
1) Flip
2) Mirror
3) Rotate counter-clockwise

= On import =
1) Rotate clockwise
2) Mirror
3) Flip

== Standard structures ==
data{}
font{}
typeset{}

= data =
Basic value: The data it references.
base = see tilemap
format = format of output. Each entry is a list of a string and a number or
	just a string. You can have format set to one of these, or a list of these
	with any amount of sublists. The string is the data type and the number is
	the data size. Standard data types include:
	"string", "number", and "hexnum"
	A module may add other types.
file = filename to get data from. Can be a .bin file for binary data, .txt for 
	string data, or .rpl for descriptor style marked up data. The .rpl should 
	only contain the data to insert.
times = (optional) times to read (default: 1)
export = see tilemap
import = see tilemap
pretty = (optional) if true, will format a .rpl file with tabs and newlines inside lists (default: false)
endian = (optional) set the endianess of numbers, either "big" or "little" (default: "little")
pad = (optional) set the pad character (for strings that are too short) (default: "$00")
padleft = (optional) pad on the left instead of the right (default: false)
comment = (optional) comment to add to the top of the file. Only works with txt and rpl
Lists of data will be condensed into raw data per the size spec as necessary.

= font =
Basic value: Will always be the struct name.
file = image file to read the font from
spacing = (optional) spacing between characters (pixels) when writing (default: 0)
backspace = (optional) negative spacing between characters when writing (default: 0)
vertical = (optional) how to vertically align characters when printing.
	Can be base (default), top, middle (unimplemented), or bottom
charset{}
chars{}
char{}

= charset =
set = (optional) character set that is in this font (default:
	" !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~")
dimensions = (optional) dimensions of each character
spacing = (optional) space between each character in the image (default: 0)
start = (optional) [x,y] starting position of the first char (default: [0,0])
base = (optional) baseline of the letters (in pixels, 0 being the top of the char) (default: height)
chars{}
char{}

= chars =
set = see charset
dimensions = see charset
spacing = see charset
start = see charset
base = see charset

= char =
c = the character
box = [x,y,width,height] on the image
position = [x,y] on the image
size = [width,height] on the image
base = see charset
Must use either box or position/size, will prefer position/size if both are given.

= typeset =
font = (optional) font to use, by name (default: font0)
file = image file to draw to
dimensions = [width,height] dimensions of the entire image (pixels)
entry = (optional) [width,height] dimensions of each entry
align = (optional) [horizontal,vertical] alignment of text within entry dimensions
	Horizontal can be left, center, or right
	Vertical can be top, middle, or bottom
	(default: [left,top])
paddingleft = (optional) padding on the left (move text right this many pixels,
	after justification) (default: 0)
paddingright = (optional) padding on the right (default: 0)
paddingtop = (optional) padding on the top (default: 0)
paddingbottom = (optional) padding on the bottom (default: 0)
padding = (optional) [left,right,top,bottom] (default: [0,0,0,0])
import = see tilemap
bg = (optional) background color (default: white)
mirror = see tilemap
flip = see tilemap
rotate = see tilemap
text{}
Using both types of paddings will use the sums of both.
Left/right padding and top/bottom padding cancel each other out.

= text =
font = see typeset
dimensions = see typeset
entry = see typeset
text =  text to write
align = see typeset
paddingleft = see typeset
paddingright = see typeset
paddingtop = see typeset
paddingbottom = see typeset
padding = see typeset
index = (optional) index via entry/dimensions info in LRUD order
position = [x,y] location to draw section. Will use size or entry for
	width/height depending on what's available.
size = [width,height] of section
box = [x,y,width,height]
mirror = see tilemap
flip = see tilemap
rotate = see tilemap
import = see tilemap
bg = see typeset
Must specify one of: entry/index, position/size, position/entry, or box
