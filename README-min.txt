Pokemon mini module.

== Struct types and possible values ==
ROM{}
tilemap{}
tilemap3{}
spritemap{}
spritemap3{}
tile{}
tiles{}
sprite{}
sprites{}
tile3{}
tile3s{}
sprite3{}
sprite3s{}
Note that *3 types are for 3-colour graphics. 

= ROM =
id = four letter game ID
name = (optional) game name as in ROM, not including $00 padding
Both can be lists of possible values.

= tilemap =
base = base address of the tilemap in the ROM
base1 = base of first set of tiles
base2 = base of second set of tiles (these are composited to make gray)
file = file to read the graphics from
dimensions = [Width,Height]
map = (uniheritable) list of tiles by id, shorthand for lots of tile structs
	You can use x to draw a black square, eg: [0,1,2,x,5,6,10] or i to skip
	over the tile entirely.
white = (optional) define the white value (Default: white)
black = (optional) define the black value (Default: black)
invert = (optional) invert the colours (Default: false)
rotate = (optional) rotate N*90 degrees (Default: 0)
mirror = (optional) mirror the image horizontally (Default: false)
flip = (optional) flip the image vertically (Default: false)
export = (optional) export this section from the ROM (Default: true)
import = (optional) import this section into the ROM (Default: true)
tile{}
tiles{}
tile3{}
tile3s{}

= tilemap3 =
Alias of tilemap. See tiles for info on why this exists.

= tile =
position = position in graphic as a list of [X,Y]
index = (optional) position in ROM, 0 based, linear (Default: 0)
dir = (optional) reading direction for mapping positions to indexes (Default: LRUD)
	Possible values are: LRUD, LRDU, RLUD, RLDU, UDLR, UDRL, DULR, DURL
	For example, LRUD reads from the upper left corner to the right of the 
	page, then moves down a row and continues from the left.
base = see tilemap
file = see tilemap
dimensions = see tilemap
white = see tilemap
black = see tilemap
invert = see tilemap
rotate = see tilemap
mirror = see tilemap
flip = see tilemap
export = see tilemap
import = see tilemap

= tile3 =
position = position in graphic as a list of [X,Y]
index = (optional) position in ROM, 0 based, linear (Default: 0)
dir = (optional) reading direction for mapping positions to indexes (Default: LRUD)
	Possible values are: LRUD, LRDU, RLUD, RLDU, UDLR, UDRL, DULR, DURL
	For example, LRUD reads from the upper left corner to the right of the 
	page, then moves down a row and continues from the left.
base1 = see tilemap
base2 = see tilemap
file = see tilemap
dimensions = see tilemap
white = see tilemap
black = see tilemap
invert = see tilemap
rotate = see tilemap
mirror = see tilemap
flip = see tilemap
export = see tilemap
import = see tilemap

= tiles =
Alias of tile. Intended for position/index to be a range, however this
isn't necessary. You could also just call it tile and use a range.

= tile3s =
Alias of tile3. See tiles for info on why this exists.

= spritemap =
base = see tilemap
base1 = see tilemap
base2 = see tilemap
file = see tilemap
dimensions = see tilemap
white = see tilemap
black = see tilemap
alpha = (optional) transparent colour (Default: cyan)
setalpha = (optional) transparent (but set in the colouring part) colour (Default: magenta)
invert = see tilemap (note: only inverts black and white)
inverta = (optional) invert alpha and setalpha when writing to ROM (default: false)
rotate = see tilemap
mirror = see tilemap
flip = see tilemap
export = see tilemap
import = see tilemap

= spritemap3 =
Alias of spritemap. See tiles for info on why this exists.

= sprite =
position = see tile
index = see tile
dir = see tile
base = see tilemap
file = see tilemap
dimensions = see tilemap
white = see tilemap
black = see tilemap
alpha = see spritemap
setalpha = see spritemap
invert = see tilemap
inverta = see spritemap
rotate = see tilemap
mirror = see tilemap
flip = see tilemap
export = see tilemap
import = see tilemap

= sprite3 =
position = see tile
index = see tile
dir = see tile
base1 = see tilemap
base2 = see tilemap
file = see tilemap
dimensions = see tilemap
white = see tilemap
black = see tilemap
alpha = see spritemap
setalpha = see spritemap
invert = see tilemap
inverta = see spritemap
rotate = see tilemap
mirror = see tilemap
flip = see tilemap
export = see tilemap
import = see tilemap

= sprites =
Alias of sprite. See tiles for info on why this exists.

= sprite3s =
Alias of sprite3. See tiles for info on why this exists.
