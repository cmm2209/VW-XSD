use strict;
use warnings;
use utf8;

use Lingua::Interset qw(decode);

binmode(STDIN,  ":utf8");
binmode(STDOUT, ":utf8");

while (<STDIN>) {
    chomp;
    next if /^\s*$/;

    my ($form, $tag, $lemma) = split /\t/;

    my $fs = decode('la::it', $tag);

    # Serialize feature structure safely
    my $fs_string = $fs->as_string();  # e.g. pos=noun|case=dat|number=plur

    print join("\t", $form, $lemma, $fs_string), "\n";
}