#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Helper functions for unit tests.
"""

import difflib

def dedent(text):
    """Remove leading indentation from tripple quoted strings.

    Example:
       foo = dedent('''\
                some text
                is here
                   with maybe some indents
                ''')
    foo now contains 'some text\nis here\n   with maybe some indents\n'.

    Corner cases (mixing tabs and spaces, lines that are indented less than
    the first line) are not
    handled yet.
    """
    lines = text.splitlines()
    first, limit = 0, len(lines)
    while first < limit and not lines[first]:
        first += 1
    if first >= limit:
        return ''
    firstline = lines[first]
    indent, limit = 0, len(firstline)
    while indent < limit and firstline[indent] in (' ', '\t'):
        indent += 1
    return '\n'.join([line[indent:] for line in lines[first:]])


def diff(old, new, oldlabel="expected output", newlabel="actual output"):
    """Display a unified diff between old text and new text."""
    old = old.splitlines()
    new = new.splitlines()

    diff = ['--- %s' % oldlabel, '+++ %s' % newlabel]

    def dump(tag, x, lo, hi):
        for i in xrange(lo, hi):
            diff.append(tag + x[i])

    differ = difflib.SequenceMatcher(a=old, b=new)
    for tag, alo, ahi, blo, bhi in differ.get_opcodes():
        if tag == 'replace':
            dump('-', old, alo, ahi)
            dump('+', new, blo, bhi)
        elif tag == 'delete':
            dump('-', old, alo, ahi)
        elif tag == 'insert':
            dump('+', new, blo, bhi)
        elif tag == 'equal':
            dump(' ', old, alo, ahi)
        else:
            raise AssertionError('unknown tag %r' % tag)
    return "\n".join(diff)

