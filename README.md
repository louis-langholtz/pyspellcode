# pyspellcode
Python script for using `clang` and `hunsepll` for spell checking source code comments.

This script parses the [AST dump](http://clang.llvm.org/docs/IntroductionToTheClangAST.html) output from `clang` and runs words found in comment nodes through `hunspell`. It's not perfect, but it's completely IDE independent. It just needs `clang` and `hunspell`. So it should be usable in continuous integration environments like [Travis CI](https://travis-ci.org).

The script accepts command line arguments to fine tune what it does. These arguments are similar to what `clang` and `hunspell` use for doing things like setting which language standard to use or adding a personal dictionary file. For the most up-to-date command line argument usage, run the script with the `-h` flag.

For example:
```
$ ./spell-check.py -h
usage: spell-check.py [-h] [-v] [-I <dir>] [-std=c++11] [-std=c++14]
                      [-std=c++17] [-p <full-file-path>]
                      filename [filename ...]

positional arguments:
  filename              filename to inspect

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Gets more verbose to aid with diagnostics
  -I <dir>, --include-dir <dir>
                        Add directory to include search path
  -std=c++11            Selects the C++11 language standard
  -std=c++14            Selects the C++14 language standard
  -std=c++17            Selects the C++17 language standard
  -p <full-file-path>, --personal-dict <full-file-path>
                        specify the fullpath to a personal dictionary

```
