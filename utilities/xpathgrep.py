#!/usr/bin/env python
"""
A 'grep' for HTML/XML documents that uses xpath syntax.

Usage: xpathgrep.py xpath_expr [filename ...]
"""
import sys
from lxml import etree


def grep(expr, filename):
    try:
        if not filename:
            filename = '<stdin>'
            htmldata = sys.stdin.read()
        else:
            htmldata = file(filename).read()
        doc = etree.HTML(htmldata)
    except Exception, e:
        print >> sys.stderr, 'xpathgrep: %s: %s' % (filename, e)
        return
    try:
        results = doc.xpath(expr)
    except Exception, e:
        print >> sys.stderr, 'xpathgrep: %s' % e
        sys.exit(1) # no point in continuing if the expr has a syntax error
    if results:
        print  '%s: %s matches' % (filename, len(results))
        for node in results:
            print ' * ' + str(node).replace('\n', '\n   ')

def main():
    if len(sys.argv) < 2:
        print >> sys.stderr, __doc__.strip()
        sys.exit(1)
    expr = sys.argv[1]
    filenames = sys.argv[2:]
    if not filenames:
        filenames = [None] # read from sys.stdin
    for filename in filenames:
        grep(expr, filename)

if __name__ == '__main__':
    main()
