#!/usr/bin/perl

# You must run (once): cpan Switch Text::WikiCreole File::Slurp
# Then see ./build.pl --help for details
# or to build everything, run: ./build.pl --all

use Getopt::Long;
use File::Find qw(find);
use File::Path qw(make_path remove_tree);
use File::Slurp qw(read_file write_file);

use Text::WikiCreole;
creole_extend;

# Handle links.
use URI::Split qw(uri_split uri_join);
use URI::Escape qw(uri_escape_utf8);
sub mylink {
	my ($scheme, $auth, $path, $query, $frag) = uri_split($_[0]);
	$path = "/$path" if !$scheme && $path;
	$path =~ s/\p{Z}/_/g;
	return uri_join($scheme, $auth,
		uri_escape_utf8($path, "^A-Za-z0-9\-\._~/"),
	$query, $frag);
}
creole_link \&mylink;

# Handle custom stuff.
sub myplugin {
	$_[0] =~ s/^(\**)TOC(?: (.*))?/make_toc($1,$2)/e or
	$_[0] =~ s/^import (.*)/import_html($1)/e or
	$_[0] =~ s/^table (.*)$([\s\S]+)/make_table($1,$2)/me or
	$_[0] = "<!-- Parse error: this plugin was not found -->\n";
	return $_[0];
}
creole_plugin \&myplugin;

$current_doc = '';
sub make_toc {
	# Create a table of contents for the given document or for the current one.
	my $doc = $current_doc;
	my $stars = $_[0];
	$doc = read_file($_[1], binmode => ':utf8') if $_[1];
	$doc =~ s/^(=+) *(.*)$|^.*(\r?\n|\r|\z)/make_toc_bit($stars . $1, $2)/mge;
	return creole_parse($doc);
}

sub make_toc_bit {
	my $n = $_[1];
	return $_[0] ? ('*' x length($_[0])) . ' [[#' . valid_anchor($n) . "|$n]]" : '';
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
	my $fn = $_[0];
	my $ft = read_file($fn, binmode => ':utf8');

	if ($fn =~ /\.creole$/) {
		my $bup = $current_doc;
		my $html = parse_text($ft);
		$current_doc = $bup;
		return $html;
	} else {
		return $ft;
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
	my @widths = ($args =~ /\bwidth=\(([^)]*)\)\b/) ? split(/ *, */, $1) : [];

	# Height definitions. 1 per row.
	my @heights = ($args =~ /\height=\(([^)]*)\)\b/) ? split(/ *, */, $1) : [];

	# TODO: other attrs, style

	# Make the cells. Everything between |= or | unless preceeded by ~
	my @cells = grep(!/^\s*$/, split(/\s*(?<!~)\|/, $table));
	for (my $i = 0; $i < scalar @cells; $i++) {
		$cells[$i] =~ s%^=\s*(.+?)\s*$%'<th>' . trim(creole_parse($1)) . '</th>'%se or
		$cells[$i] =~ s%^\s*(.+?)\s*$%'<td>' . trim(creole_parse($1)) . '</td>'%se;
		print "$i: " . $cells[$i] . "\n";
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
		$result .= '<tr>';
		for (my $x = 0; $x < $width; $x++) {
			my $idx = $indexer->($x, $y);
			print "$x,$y = $idx\n";
			$result .= $cells[$idx];
		}
		$result .= '</tr>';
	}
	return $result . '</table>';
}

sub trim {
	$_[0] =~ s%<p>|</p>|\s+$%%g;
	return $_[0];
}

# Subroutines for build code.
sub conv_file {
	my $infile = shift @_;
	my $outfile = shift @_;

	my $creoletext = read_file($infile, binmode => ':utf8');
	my $htmltext = parse_text($creoletext);

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
my $text = '';
my $file = '';
my $out = '';
my $all = 0;
my $help = 0;
my $verbose = 0;

GetOptions(
	'all|a'      => \$all,
	'help|h|?'   => \$help,
	'out|o=s'    => \$out,
	'text|t=s'   => \$text,
	'file|f=s'   => \$file,
	'verbose|v+' => \$verbose,
);

if ($help) {
	(my $helptext = <<'	HELP_TEXT') =~ s/^\t//gm;
	Converts input WikiCreole to HTML.
	Usage: ./build.pl [OPTIONS]

	  --help    -h  Print this help text.
	  --all     -a  Build all files in the given directory (default: CWD)
	  --out     -o  Directory or file to write to (default: 'build' or stdout)
	  --text    -t  Input creole text directly
	  --file    -f  Specify a creole file (assumed if no flag specified)
	  --verbose -v  Print verbose information
	HELP_TEXT
	print $helptext
} elsif ($all) {
	# Build directory accordingly
	$out = 'build' if !$out;

	# First create the folder and clear it
	remove_tree($out);
	make_path($out);

	# Now build according to the structure:
	#  Main.creole -> index.html
	#  *.creole -> */index.html
	#  */*.creole -> */*/index.html
	find({
		wanted => \&wanted,
		no_chdir => 1
	}, scalar @ARGV ? $ARGV[0] : '.');
	sub wanted {
		my $outfile = $_;
		if ($outfile =~ /\.creole$/) {
			$outfile =~ s%^(?:\./)?((?:[^/]+/)*)(.*)\.creole$%$out/$1/$2%;
			$outfile =~ s%/+%/%g;
			$outfile =~ s%/Main$%%;
			conv_file($_, $outfile . "/index.html");
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
