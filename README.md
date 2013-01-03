With [that](https://github.com/logicplace/Imperial/commit/071c4a67a8bd9ea5d8d71a1f5945796847283aef),
 this is pretty much feature compatible with v8!

Missing items:
* min lib does not adjust ROM.name to be of type pokestr.
* Typesetting functions have not been implemented.

But the important part is that this is now usable.

Alright, this is mostly cleaned. Everything structural has been completed. I do
 need to add more tests, comments, and error handling, however. Anyone who wants
 to write a lib for this may start now. I will make the documentation for doing
 so when I'm happy with the rest of the cleaning process.

I haven't finished the CLI yet either.

After I finish the clean-up process, I will then write a guide on how to develop
 libs and also begin on the wiki. After which, I will bother to write the
 typesetting lib. Maybe I'll even make it an example or something.

When all of this is done, I will move on to the assembler portion, and maybe
 I'll write a few guides and the extra syntax files.

For now, this will stay as a development release (though in a working state!)
 until I've completed the clean-up process, at which point I will officially
 release 1.0 packed with py2exe for ezpz usage.
