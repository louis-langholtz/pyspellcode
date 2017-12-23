#!/usr/bin/env python
# Python script requiring python 2.7
# For python 2 documentation, see: https://docs.python.org/2/index.html

import sys, subprocess, string, re

# Get command line argument using the list provided from sys.argv.
# Don't need argv0 though so slice over it...
files = sys.argv[1:]

# Need various clang options...
# -fsyntax-only tells clang to only examine syntax and to not generate object file
cmdlist = ["clang", "-Xclang", "-ast-dump", "-fsyntax-only", "-fno-color-diagnostics", "-std=c++14", "-I."]
# cmdlist.extend(args)
# print(cmdlist)

hunspellpipe = subprocess.Popen(["hunspell", "-a"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1)
hunspellpipe.stdout.readline() # read the first line from hunspell

def check_word(word):
    #print(word, file=hunspellpipe.stdin)
    #print("checking word \"{0}\"".format(word))
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

def check_file(filename):
    args = cmdlist + [filename]
    clangpipe = subprocess.Popen(args, stdout=subprocess.PIPE)
    # subprocess.check_output(cmdlist)
    # Look for "TextComment"
    astlinenum = 0
    foundnum = 0
    srclinenum = 0
    skipTillHTMLEndTagComment = False
    skipTillNextLinenum = False
    with clangpipe.stdout:
        for line in iter(clangpipe.stdout.readline, b''):
            astlinenum += 1
            if (foundnum == 0):
                pos = line.find(filename)
                if (pos == -1):
                    continue
                foundnum = astlinenum
            useful = line.lstrip(" |-\`")
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
            if (nodetype != "TextComment"):
                continue
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
            text = data.lstrip("Text=\"").rstrip("\"").lstrip(" ").lstrip(string.punctuation)
            if not text:
                continue
            words = re.split("[-\s\"\.]+", text) # Split on any space or dash char
            unrecognizedwords = []
            for word in words:
                if not check_word(word):
                    unrecognizedwords.append(word)
            if not unrecognizedwords:
                continue
            #print("line #{0},        found words: {1}".format(srclinenum, words))
            print("line #{0}, unrecognized words: {1}".format(srclinenum, unrecognizedwords))
    clangpipe.wait() # Blocks until clang exits

for file in files:
    print("checking file {0} now".format(file))
    check_file(file)

hunspellpipe.stdin.close()
hunspellpipe.wait() # Blocks until hunspell exits
