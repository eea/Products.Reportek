#!/usr/bin/env python
import codecs
import re
import sys

f = open(sys.argv[1])

colPat = re.compile(r'\bposition (\d+):')

for i, line in enumerate(f, 1):
    try:
        codecs.decode(line, 'ascii')
    except UnicodeDecodeError as e:
        m = colPat.search(str(e))
        if m:
            print "non ascii found on line %d, col: %s" % (i, m.groups()[0])
            print line
        else:
            print "Error on line %d" % i
            print str(e)
            print line
