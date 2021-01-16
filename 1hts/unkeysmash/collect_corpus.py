#!/usr/bin/env python3

import sys
import os, fnmatch
from vocab import Vocab

# via https://code.activestate.com/recipes/499305-locating-files-throughout-a-directory-tree/
def locate(pattern, root=os.curdir):
    """Locate all files matching supplied filename pattern in and below
    supplied root directory."""
    for path, dirs, files in os.walk(os.path.abspath(root)):
        print(path)
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def main(argv):
    if len(argv) != 2:
        print("usage: %s <corpus dir>" % argv[0])
        return 1

    corpusdir = argv[1]
    vocab_path = "vocab.json"

    vocab = Vocab()
    for md_path in locate("**.md", corpusdir):
        with open(md_path, "r") as md_file:
            print("collecting vocab from", md_path)
            md_str = md_file.read()
            vocab.consume_md_str(md_str)

    print("writing vocab to %s" % vocab_path)

    with open(vocab_path, "w") as vocab_file:
        vocab_file.write(vocab.dumps())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
