#!/usr/bin/env python
# Python script requiring python 2.7
# For python 2 documentation, see: https://docs.python.org/2/index.html

import sys, subprocess, string

# Get command line argument using the list provided from sys.argv.
# Don't need argv0 though so slice over it...
files = sys.argv[1:]

# Need various clang options...
# -fsyntax-only tells clang to only examine syntax and to not generate object file
cmdlist = ["clang", "-Xclang", "-ast-dump", "-fsyntax-only", "-fno-color-diagnostics", "-std=c++14", "-I."]
# cmdlist.extend(args)
# print(cmdlist)

def check_file(filename):
    args = cmdlist + [filename]
    p = subprocess.Popen(args, stdout=subprocess.PIPE)
    # subprocess.check_output(cmdlist)
    # Look for "TextComment"
    astlinenum = 0
    foundnum = 0
    srclinenum = 0
    skipTillHTMLEndTagComment = False
    with p.stdout:
        for line in iter(p.stdout.readline, b''):
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
                if (linenum < srclinenum):
                    continue
                srclinenum = linenum
            data = info[1]
            if not (data.startswith("Text=\"")):
                continue
            text = data.lstrip("Text=\"").rstrip("\"").lstrip(" ").lstrip(string.punctuation)
            if not text:
                continue
            print("at line #{0}: {1}".format(srclinenum, text))
    p.wait() # Blocks until clang exits

for file in files:
    print("checking file {0} now".format(file))
    check_file(file)
