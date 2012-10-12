With [that](https://github.com/logicplace/Imperial/commit/071c4a67a8bd9ea5d8d71a1f5945796847283aef),
 this is pretty much feature compatible with v8!

Missing items:
* min lib does not adjust ROM.name to be of type pokestr.
* Typesetting functions have not been implemented.

But the important part is that this is now usable.

**NOTE: If someone actually wants to write a lib for this, wait a bit.**  
Next up is the cleaning process, and I'm going to do a slight redesign based
 on what I've learned is better from writing this. There will likely be breaking
 but not major changes to the internal code (RPL as a language will not be
 affected (oops that's a lie, map struct will change)). However, there is one
 major thing: I plan to remove executables.
 This was a bad idea based on a spur-of-the-moment decision that I've learned
 will give more headache for lib developers than it would help anyone. I also
 plan to remove all the type checking and make the system a bit more pythonic.
 I also hope to add a lot more comments, to the test rpls as well. I'll be
 changing the CLI too, to something a lot more intelligent.

After I finish the clean-up process, I will then write a guide on how to develop
 libs and also begin on the wiki. After which, I will bother to write the
 typesetting lib. Maybe I'll even make it an example or something.

When all of this is done, maybe I will start implementing the sound system, or
 maybe I'll write a few guides and the extra syntax files.

For now, this will stay as a development release (though in a working state!)
 until I've completed the clean-up process, at which point I will officially
 release 1.0 packed with py2exe for ezpz usage.
