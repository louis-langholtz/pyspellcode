#!/usr/bin/env python
# Python script requiring python 2.7
# For python 2 documentation, see: https://docs.python.org/2/index.html

import sys, subprocess, string, re, argparse, os

# Function to check that given argument names a file that exists.
# Function idea from https://stackoverflow.com/a/11541495/7410358
def extant_file(arg):
    if not os.path.exists(arg):
        raise argparse.ArgumentTypeError("\"{0}\" does not exist".format(arg))
    return arg

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose',
    dest='verbose', action='store_true',
    help='Gets more verbose to aid with diagnostics')
parser.add_argument('-I', '--include-dir',
    dest='includedirs', nargs=1, metavar='<dir>', action='append',
    help='Add directory to include search path')
parser.add_argument('-std=c++11',
    dest='langstd', action='store_const', const='c++11',
    help='Selects the C++11 language standard')
parser.add_argument('-std=c++14',
    dest='langstd', action='store_const', const='c++14',
    help='Selects the C++14 language standard')
parser.add_argument('-std=c++17',
    dest='langstd', action='store_const', const='c++17',
    help='Selects the C++17 language standard')
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
    clangpipe = subprocess.Popen(argsneeded, stdout=subprocess.PIPE)
    astlinenum = 0
    foundnum = 0
    srclinenum = 0
    skipTillHTMLEndTagComment = False
    skipTillNextLinenum = False
    skipTillNextDepth = 0
    mispellings = 0
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
            #if (skipTillNextDepth and skipTillNextDepth < len(depth)):
            #    continue
            skipTillNextDepth = 0
            useful = match.group(2)
            fields = useful.split(" ", 2)
            if (len(fields) <= 2):
                continue
            nodetype = fields[0]
            if (nodetype == "HTMLEndTagComment"):
                skipTillHTMLEndTagComment = False
                continue
            if skipTillHTMLEndTagComment:
                continue
            if (nodetype == "HTMLStartTagComment"):
                skipTillHTMLEndTagComment = True
                continue
            #if (nodetype == "BlockCommandComment"):
            #    if not re.match("Name=\"sa\"$", useful):
            #        continue
            #    skipTillNextDepth = len(depth)
            if (nodetype != "TextComment"):
                continue
            if cmdlineargs.verbose:
                print(useful)
            nodeinfo = fields[2].rstrip("\n").lstrip("<")
            info = nodeinfo.split("> ", 1)
            if (len(info) < 2):
                continue
            location = info[0]
            locations = location.split(", ")
            if (locations[0].startswith("line:")):
                linenum = locations[0].split(":")[1]
                #if (linenum < srclinenum):
                #    skipTillNextLinenum = True
                #    continue
                srclinenum = linenum
                skipTillNextLinenum = False
            if skipTillNextLinenum:
                continue
            data = info[1]
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
                word = word.strip("\"\'").lstrip("(").rstrip(")").strip(string.punctuation)
                if not check_word(word):
                    unrecognizedwords.append(word)
                    mispellings += 1
            if not unrecognizedwords:
                continue
            #print("line #{0},        found words: {1}".format(srclinenum, words))
            print("line #{0}, unrecognized words: {1}".format(srclinenum, unrecognizedwords))
    clangpipe.wait() # Blocks until clang exits
    return mispellings

totalerrors = 0
for file in files:
    print("checking file {0} now".format(file))
    totalerrors += check_file(file)

hunspellpipe.stdin.close()
hunspellpipe.wait() # Blocks until hunspell exits

if (totalerrors > 0):
    exit(1)