#!/usr/bin/env python
#
# Copyright (c) 2017 Louis Langholtz https://github.com/louis-langholtz/pyspellcode
#
# This software is provided 'as-is', without any express or implied
# warranty. In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

# Python script requiring python 2.7
# For python 2 documentation, see: https://docs.python.org/2/index.html

# Bring in stuff that'll be used...
from __future__ import print_function
import sys, subprocess, string, re, argparse, os

# Function to check that given argument names a file that exists.
# Function idea from https://stackoverflow.com/a/11541495/7410358
def extant_file(arg):
    if not os.path.exists(arg):
        raise argparse.ArgumentTypeError("\"{0}\" does not exist".format(arg))
    return arg

# Setup some command line argument parsing...
# Note that convention for help text is to have first letter of string as
# lower-case and to not end with any punctuation.
parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose',
    dest='verbose', action='store_true',
    help='gets more verbose to aid with diagnostics')
parser.add_argument('-I', '--include-dir',
    dest='includedirs', nargs=1, metavar='<dir>', action='append',
    help='adds directory to include search path')
parser.add_argument('-std=c++11',
    dest='langstd', action='store_const', const='c++11',
    help='selects the C++11 language standard')
parser.add_argument('-std=c++14',
    dest='langstd', action='store_const', const='c++14',
    help='selects the C++14 language standard')
parser.add_argument('-std=c++17',
    dest='langstd', action='store_const', const='c++17',
    help='selects the C++17 language standard')
parser.add_argument('-a', '--all-comments', '-fparse-all-comments',
    dest='all_comments', action='store_true',
    help='results in checking all comments')
parser.add_argument('-e', '-Werror', '--error-exit',
    dest='nonzero_exit_on_misspellings', action='store_true',
    help='emits nonzero status on exit if there were unrecognized words')
parser.add_argument('-p', '--personal-dict',
    dest='dict', nargs=1, metavar='<full-file-path>',
    help='specify the fullpath to a personal dictionary')
parser.add_argument('filenames',
    metavar='filename', type=extant_file, nargs='+',
    help='filename to inspect')

cmdlineargs = parser.parse_args()
if cmdlineargs.verbose:
    print("argparse result: {0}".format(cmdlineargs))

if cmdlineargs.dict:
    dictionary = cmdlineargs.dict

langstd = 'c++11'
if cmdlineargs.langstd:
    langstd = cmdlineargs.langstd

# Get command line argument using the list provided from sys.argv.
# Don't need argv0 though so slice over it...
#files = sys.argv[1:]
files = cmdlineargs.filenames

# Need various clang options...
# -fsyntax-only tells clang to only examine syntax and to not generate object file
clangargs = ["clang", "-Xclang", "-ast-dump", "-fsyntax-only", "-fno-color-diagnostics"]
clangargs.append('-std=' + langstd)
if cmdlineargs.all_comments:
    clangargs.append('-fparse-all-comments')
if cmdlineargs.includedirs:
    for includedirs in cmdlineargs.includedirs:
        includedir = string.join(includedirs)
        clangargs.append('-I' + includedir)
        #clangargs.extend(includedir)
if cmdlineargs.verbose:
    print("argv for AST generator: {0}".format(clangargs))

# Note: hunspell has issues with use of the apostrophe character.
# For details, see: https://github.com/marcoagpinto/aoo-mozilla-en-dict/issues/23
hunspellargs = ["hunspell", "-a"]
if cmdlineargs.dict:
    hunspellargs = hunspellargs + ["-p"] + cmdlineargs.dict
if cmdlineargs.verbose:
    print("argv for spelling tool: {0}".format(hunspellargs))

hunspellpipe = subprocess.Popen(hunspellargs, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1)
hunspellpipe.stdout.readline() # read the first line from hunspell

def check_word(word):
    #print(word, file=hunspellpipe.stdin)
    #print("checking word \"{0}\"".format(word))
    #word = word.lstrip("\"").rstrip("\"")
    if re.search("^\W+$", word):
        return True
    if re.search("^\W", word):
        return False
    if not word:
        return True
    hunspellpipe.stdin.write(word + "\n")
    hunspellpipe.stdin.flush()
    isokay = True
    #with hunspellpipe.stdout:
    for line in iter(hunspellpipe.stdout.readline, b''):
        if not line.rstrip("\n"):
            break
        if not line.startswith("*"):
            isokay = False
    #resultline = hunspellpipe.stdout.readline()
    #emptyline  = hunspellpipe.stdout.readline()
    #print("      word=\"{0}\"  isokay={1}".format(word, isokay))
    #print("resultline=\"{0}\"".format(resultline))
    #print(" emptyline=\"{0}\"".format(emptyline))
    #if (resultline.startswith("*")):
    #    return True
    #return False
    return isokay

def check_file(path):
    argsneeded = clangargs + [path]
    # Note: Specifying bufsize=-1 hugely improves performance over its default!
    # For usage details, see:
    #   https://docs.python.org/2/library/subprocess.html#popen-constructor
    clangpipe = subprocess.Popen(argsneeded, bufsize=-1, stdout=subprocess.PIPE)
    astlinenum = 0
    foundnum = 0
    srclinenum = 0
    skipNextTextComment = False
    skipTillHTMLEndTagComment = False
    skipTillNextLinenum = False
    skipFirstWord = False
    skipTillNextDepth = 0
    misspellings = 0
    print("file {0}:".format(path))
    with clangpipe.stdout:
        for line in iter(clangpipe.stdout.readline, b''):
            line = line.rstrip()
            if cmdlineargs.verbose:
                print("checking: {0}".format(line))
            astlinenum += 1
            if (foundnum == 0):
                pos = line.find(path)
                if (pos == -1):
                    continue
                foundnum = astlinenum
            match = re.match("^(\W*)(\w.*)$", line)
            #print("lhs=\"{0}\" rhs=\"{1}\"".format(match.group(1), match.group(2)))
            depth = match.group(1)
            if (skipTillNextDepth and skipTillNextDepth < len(depth)):
                if cmdlineargs.verbose:
                    print("skipping: {0}".format(line))
                continue
            skipTillNextDepth = 0
            useful = match.group(2)
            fields = useful.split(" ", 2)
            if (len(fields) <= 2):
                # Shouldn't happen but apparently it did!
                continue
            nodetype = fields[0] # Like: FullComment
            nodehex  = fields[1] # Like: 0x10f24bb30
            nodedata = fields[2] # Like: <line:97:5, line:99:5>
            m = re.match("<([^>]*)>\s*(.*)", nodedata)
            if not m:
                if cmdlineargs.verbose:
                    print("Skipped: {0}".format(useful))
                continue
            locations = m.group(1).split(", ") # Ex: 'col:15, col:47'
            data = m.group(2) # Ex: 'Text=" Computes the AABB for the given body."'
            if (locations[0].startswith("line:")):
                linenum = locations[0].split(":")[1]
                #if (linenum < srclinenum):
                #    skipTillNextLinenum = True
                #    continue
                srclinenum = linenum
                skipTillNextLinenum = False
            if skipTillNextLinenum:
                continue
            if (nodetype == "HTMLEndTagComment"):
                skipTillHTMLEndTagComment = False
                continue
            if skipTillHTMLEndTagComment:
                continue
            if (nodetype == "HTMLStartTagComment"):
                skipTillHTMLEndTagComment = True
                continue
            if (nodetype == "BlockCommandComment"):
                if cmdlineargs.verbose:
                    print("found: {0}".format(useful))
                m = re.search("Name=\"([^\"]*)\"", useful)
                if not m:
                    continue
                cmdName = m.group(1)
                if (cmdName == "sa") or (cmdName == "see"):
                    skipTillNextDepth = len(depth)
                    continue
                if (cmdName == "throws"):
                    skipFirstWord = True
                    continue
                continue
            if (nodetype == "InlineCommandComment"):
                if not re.search("Name=\"image\"", useful):
                    continue
                skipNextTextComment = True
            if (nodetype != "TextComment"):
                continue
            if skipNextTextComment:
                skipNextTextComment = False
                continue
            if cmdlineargs.verbose:
                print(useful)
            if not (data.startswith("Text=\"")):
                continue
            #text = data.lstrip("Text=\"").rstrip("\"").lstrip(" ").lstrip(string.punctuation)
            text = data.lstrip("Text=\"").rstrip("\"").lstrip(" ").strip(string.punctuation)
            if not text:
                continue
            words = re.split("[\s]+", text) # Split on any space or dash char
            if cmdlineargs.verbose:
                print(words)
            unrecognizedwords = []
            for word in words:
                if skipFirstWord:
                    skipFirstWord = False
                    continue
                word = word.strip("\"\'").lstrip("(").rstrip(")").strip(string.punctuation)
                if not check_word(word):
                    unrecognizedwords.append(word)
                    misspellings += 1
            if not unrecognizedwords:
                continue
            print("  line #{0}, unrecognized words: {1}".format(srclinenum, unrecognizedwords))
    clangpipe.wait() # Blocks until clang exits
    if misspellings == 0:
        print("  no unrecognized words")
    return misspellings

totalmisspellings = 0
for file in files:
    totalmisspellings += check_file(file)

hunspellpipe.stdin.close()
hunspellpipe.wait() # Blocks until hunspell exits

if ((totalmisspellings > 0) and cmdlineargs.nonzero_exit_on_misspellings):
    exit(1)

exit(0)
