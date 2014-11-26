I'll basically always run the tests before pushing and make sure they all pass.
 If they don't, I'll make a branch for the tempermental commits. So that way,
 you can be assured master will be functional until there are stable releases.

Oops I added a 0 in front. I decided I don't want this to be 1.0 until there's
 support for all the highest hyponymic data types: graphic (supported), text (see
 below), assembly (designed), sound, and formatted text. Other types may be added
 along the way, but I consider these the next layer of foundations for file types.
 eg. a video can be considered an archive (represented by data struct) of images
 and sound(s). In regards to the new numbering, I'm thinking of it like the first
 two numbers being the stable version (major and minor), then the last number being
 the unstable/dev version number.

Regarding the current state of the project, I'm mainly questioning some things,
 and improving the design. As I was implementing the text handling, I realized
 some fundamental flaws in the design wrt how values can be inferred from exported
 data, mainly, and have been trying to design the best way to handle this, since
 it's quite important. From this, I've side tracked to other designs, such as a
 full design for the assembler, as well as a couple other beautifying tasks.
 Most importantly, I've decided to step back, and write a mission statement, or
 manifesto or something, for what this project is about, its goals, and how it
 should ideally be implemented. I don't get much support for this project, even
 from my friends, mainly because none of them do ROM hacking, so I hope this will
 serve as a way to communicate to them what this is about so I can more successfully
 bounce ideas off of them. I also think ROM hackers themselves don't care much
 because this is just another everything project. I respect that, it's fine. This
 project won't be useful until more things are implemented, so I can only hope my
 own experience and design ideas are sufficient until then.

### Countdown to 0.1.0 ###
* <del>Implement typesetting lib.</del>
* <del>Finish CLI \[as far as I care anymore\].</del>
* Add exports for: <del>structured rpl, JSON, bin</del>, txt, csv
* Add better error reporting.
* Clean, make efficiency adjustments, add more comments.
* Complete help contents.

### After 0.1.0 ###
* Finish RPL tutorial.
* Finish lib development tutorial.
* Finish other documentation on the wiki.
* Write other syntax files.
* Begin on 0.1.1 with assembler.
