#!/usr/bin/perl

# You must run (once): cpan Text::WikiCreole File::Slurp HTML::Escape
# Then see ./build.pl --help for details
# or to build everything, run: ./build.pl --all

use Getopt::Long;
use File::Find qw(find);
use File::Path qw(make_path remove_tree);
use File::Slurp qw(read_file write_file);
use File::Basename qw(fileparse dirname basename);
use HTML::Escape qw(escape_html);

use Text::WikiCreole;
creole_extend;

sub dots {
	my $dots = dirname($current_fn) . "/";
	$dots =~ s%[^/.]+%..%g;
	my $rm = length ($out =~ /\//g) + 1;
	$dots =~ s%^(../){$rm}%%;
	$dots =~ s%^([^.])|^$%./$1%;
	return $dots;
}

# Handle links.
use URI::Split qw(uri_split uri_join);
use URI::Escape qw(uri_escape_utf8);
sub mylink {
	my ($scheme, $auth, $path, $query, $frag) = uri_split($_[0]);
	$path = dots() . "$path" if !$scheme && $path;
	$path =~ s/\p{Z}/_/g;
	return uri_join($scheme, $auth,
		uri_escape_utf8($path, "^A-Za-z0-9\-\._~/"),
	$query, valid_anchor($frag));
}
creole_link \&mylink;

# Handle custom stuff.
sub myplugin {
	$_[0] =~ s/^TOC(?:\s+(.*))?/make_toc($1)/es or
	$_[0] =~ s/^import (.*)/import_html($1)/e or
	$_[0] =~ s/^table(?: +(.+))?$([\s\S]+)/make_table($1,$2)/me or
	$_[0] =~ s%^code(?: +(\S+))? *$\r?\n([\s\S]+)%<pre><code class="$1">$2</code></pre>\n%m or
	$_[0] =~ s/^crumbs (.*)/make_crumbs($1)/e or
	$_[0] = "<!-- Parse error: this plugin was not found -->\n";
	return $_[0];
}
creole_plugin \&myplugin;

$current_fn = '';
$current_doc = '';
sub make_toc {
	# Create a table of contents for the given document or for the current one.
	my $doc;
	my ($files, $indent) = @_;
	if ($files) {
		$files =~ s/^\s+|\s+$//g;
		my @docs = split(/\s+/, $files);
		$doc = "";
		foreach $x (@docs) {
			print "Reading in file for TOC: $x\n" if $verbose;
			print "  For use in file: $current_fn\n" if $verbose >= 2;
			my $d = read_file($x, binmode => ':utf8');
			$x =~ s/\.[^.]+$//;
			$d =~ s/^(=+) *(.*)$|^(?:.*<<TOC\s+([^\s>][^>]*?)\s*>>.*|.*)(?:\r?\n|\r|\z)/$3 ? make_toc("$3", "$indent#") : make_toc_bit($indent . $1, $2, "$x#")/mge;
			$d =~ s/\n*\z/\n/;
			$doc .= "$d";
		}
	} else {
		$doc = $current_doc;
		$doc =~ s/^(=+) *(.*)$|^.*(\r?\n|\r|\z)/make_toc_bit($indent . $1, $2, '#')/mge;
		$doc =~ s/\n*\z/\n/;
	}
	return $doc if $indent;

	# Make every level incriment by one at most.
	$doc =~ /^(#+)/;
	my $expected = 1; my $got = length $1;
	my @lines = split(/\n/, $doc);
	$doc = '';
	foreach $line (@lines) {
		$line =~ /^(#+)/;
		my $amt = length $1;
		++$expected if $amt > $got; # New level.
		--$expected if $amt < $got; # Back down a level.
		$got = $amt;
		my $diff = $got - $expected;
		$line =~ s/^#{$diff}// if $diff;
		$doc .= "$line\n";
	}
	return creole_parse($doc);
}

sub make_toc_bit {
	my $n = $_[1];
	return $n ? ('#' x length($_[0])) . ' [[' . $_[2] . valid_anchor($n) . "|$n]]" : '';
}

sub valid_anchor {
	# Remove all html and punctuation, turn spaces into underscores.
	my $anc = shift @_;
	$anc =~ s/^ +| +$//g;
	$anc =~ s/<[^>]+>//g;
	$anc =~ s/\p{Punctuation}|\p{Other}|\p{Symbol}//g;
	$anc =~ s/\p{Separator}/_/g;
	return $anc;
}

sub import_html {
	my @tmp = split(/ +/, $_[0]);
	my $fn = shift @tmp;
	my $ft = read_file($fn, binmode => ':utf8');

	if ($fn =~ /\.(hidden-)?cr(eole)?$/) {
		my $bup = $current_doc;
		my $html = parse_text($ft);
		$current_doc = $bup;
		return $html;
	} elsif ($fn =~ /\.x?html?$/) {
		# Template in some stuff.
		my $x;
		for (my $i = 1; $x = shift @tmp; ++$i) {
			$ft =~ s/\{\{$i\}\}/$x/g;
		}
		my $dots = dots();
		$dots =~ s%/$%%;
		$ft =~ s/\{\{\.\.\}\}/$dots/g;
		return $ft;
	} elsif ($fn =~ /\.txt$/) {
		$fn = basename($fn);
		$fn =~ s%\W%-%g;
		$fn =~ s%-+%-%g;
		$p = '<p class="' . $fn . '">';

		# wrap every paragraph
		$ft = escape_html($ft);
		$ft =~ s%\r?\n\r?\n%</p>$p%;
		return "$p$ft</p>\n";
	}
}

sub make_table {
	my $args = shift @_;
	my $table = shift @_;

	# Table dimensions are required.
	$args =~ /\b(\d)x(\d)\b/;
	my $width = $1;
	my $height = $2;

	# Is there a read direction? If not assume lrud
	my $dir = $args =~ /\b([lrud]+)\b/ ? $1 : "lrud";

	# Width definitions. 1 per col.
	my @widths = ($args =~ /\bwidth *= *\( *([^)]*) *\)/) ? split(/ *, */, $1) : ();

	# Height definitions. 1 per row.
	my @heights = ($args =~ /\bheight=\(([^)]*)\)/) ? split(/ *, */, $1) : ();

	# TODO: other attrs, style

	# Make the cells. Everything between |= or | unless preceeded by ~
	my @cells = grep(!/^\s*$/, split(/\s*(?<!~)\|/, $table));
	for (my $i = 0; $i < scalar @cells; $i++) {
		$cells[$i] =~ s%^=\s*(.+?)\s*$%'<th>' . trim(creole_parse($1)) . '</th>'%se or
		$cells[$i] =~ s%^\s*(.+?)\s*$%'<td>' . trim(creole_parse($1)) . '</td>'%se;
	}

	# Now reorganize them.
	my $dir = substr($dir, 0, 1) . substr($dir, 2, 1) if length $dir >= 3;
	my %indexers = (
		# $indexers{$dir}->(x, y)
		"lu" => (sub { $_[1] * $width + $_[0] }),
		"ld" => (sub { (($height - $_[1]) % $height) * $width + $_[0] }),
		"ru" => (sub { $_[1] * $width + (($width - $_[0]) % $width) }),
		"rd" => (sub { (($height - $_[1]) % $height) * $width + (($width - $_[0]) % $width) }),
		"ul" => (sub { $_[0] * $height + $_[1] }),
		"ur" => (sub { (($width - $_[0]) % $width) * $height + $_[1] }),
		"dl" => (sub { $_[0] * $height + (($height - $_[1]) % $height) }),
		"dr" => (sub { (($width - $_[0]) % $width) * $height + (($height - $_[1]) % $height) }),
	);
	my $indexer = $indexers{$dir} or $indexers{"lu"};

	my $result = '<table>';
	for (my $y = 0; $y < $height; $y++) {
		my $h = $heights[$y];
		$result .= $h ? "<tr height=\"$h\">" : '<tr>';
		for (my $x = 0; $x < $width; $x++) {
			my $idx = $indexer->($x, $y);
			my $cell = $cells[$idx];
			my $w = $widths[$x];
			$cell =~ s/<td>/<td width="$w">/ if $w;
			$result .= $cell;
		}
		$result .= '</tr>';
	}
	return $result . "</table>\n";
}

sub make_crumbs {
	my @crumbs = split(/ *-> */, $_[0]);
	my $name = pop @crumbs;
	my $ret = '<div class="breadcrumbs">';
	my $link = '';
	foreach $c (@crumbs) {
		$c =~ s/^ +| +$//g;
		$link .= $link ? "/$c" : $c;
		$ret .= '<span class="breadcrumb"><a href="' . mylink($link) . '">' . $c . '</a></span>';
	}
	return "$ret<span class=\"breadcrumb\">$name</span></div>\n";
}

sub trim {
	$_[0] =~ s%<p>|</p>|\s+$%%g;
	return $_[0];
}

# Subroutines for build code.
sub conv_file {
	my $infile = shift @_;
	my $outfile = $current_fn = shift @_;

	print "Converting $infile -> $outfile...\n" if $verbose;

	my $creoletext = read_file($infile, binmode => ':utf8');
	my $htmltext = parse_text($creoletext);

	make_path(dirname($outfile));
	write_file($outfile, $htmltext) if $outfile;
	return $htmltext;
}

sub parse_text {
	my $creoletext = shift @_;
	$current_doc = $creoletext;

	$creoletext = creole_parse($creoletext);

	# Add anchors to headers.
	$creoletext =~ s%<h(\d)>(.*?)</h\1>%add_anchor($1,$2)%ge;

	# Replace unicode with entities.
	$creoletext =~ s/(\P{ASCII})/uni2entity($1)/ge;

	return $creoletext;
}

sub add_anchor {
	my $num = shift @_;
	my $name = shift @_;
	return "<h$num><a name=\"" . valid_anchor($name) . "\">$name</a></h$num>";
}

sub uni2entity { "&#" . ord(@_[0]) . ";"; }

# Decode command line input.
use I18N::Langinfo qw(langinfo CODESET);
my $codeset = langinfo(CODESET);
use Encode qw(decode);
@ARGV = map { decode $codeset, $_ } @ARGV;

# Parse command line.
$text = '';
$file = '';
$out = '';
$all = 0;
$help = 0;
$verbose = 0;
$nopretty = 0;

GetOptions(
	'all|a'       => \$all,
	'help|h|?'    => \$help,
	'out|o=s'     => \$out,
	'text|t=s'    => \$text,
	'file|f=s'    => \$file,
	'no-pretty|P' => \$nopretty,
	'verbose|v+'  => \$verbose,
);

if ($help) {
	(my $helptext = <<'	HELP_TEXT') =~ s/^\t//gm;
	Converts input WikiCreole to HTML.
	Usage: ./build.pl [OPTIONS]

	  --help       -h  Print this help text.
	  --all        -a  Build all files in the given directory (default: CWD)
	  --out        -o  Directory or file to write to (default: 'release' or stdout)
	  --text       -t  Input creole text directly
	  --file       -f  Specify a creole file (assumed if no flag specified)
	  --no-pretty  -P  Don't use pretty URLs (better for use locally)
	  --verbose    -v  Print verbose information
	HELP_TEXT
	print $helptext
} elsif ($all) {
	# Build directory accordingly
	$out = 'release' if !$out;

	# First create the folder and clear it
	remove_tree($out);
	make_path($out);

	# Now build according to the structure:
	# Pretty:
	#  Main.creole -> index.html
	#  *.creole -> */index.html
	#  */*.creole -> */*/index.html
	# Nonpretty:
	#  *.creole -> *.html
	find({
		wanted => \&wanted,
		no_chdir => 1
	}, scalar @ARGV ? $ARGV[0] : '.');
	sub wanted {
		my $outfile = $_;
		if ($outfile =~ /\.creole$/) {
			$outfile =~ s%^(?:\./)?((?:[^/]+/)*)(.*)\.creole$%$out/$1/$2%;
			$outfile =~ s%/+%/%g;
			if ($nopretty) {
				conv_file($_, "$outfile.html");
			} else {
				$outfile =~ s%/Main$%%;
				conv_file($_, "$outfile/index.html");
			}
		}
	}
} elsif ($text) {
	print parse_text($text);
} else {
	$file = $ARGV[0] if (scalar @ARGV) && !$file;
	exit 1 if !$file;

	if ($out) {
		conv_file($file, $out);
	} else {
		print conv_file($file, '') . "\n";
	}
}
