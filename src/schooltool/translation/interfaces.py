##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Abstract objects for the i18n extraction machinery

$Id: interfaces.py,v 1.1 2003/12/17 13:58:53 philikon Exp $
"""

from zope.interface import Interface

class IPOTEntry(Interface):
    """Represents a single message entry in a POT file
    """

    def addComment(comment):
        """Add a comment to the entry
        """

    def addLocationComment(filename, line):
        """Add a comment regarding the location where this message id
        entry can be found
        """

    def write(file):
        """Write the entry to the file
        """

class IPOTMaker(Interface):
    """Writes POT entries to a POT file
    """
    
    def add(strings, base_dir=None):
        """Add strings to the internal catalog.
        """

    def write():
        """Write strings to the POT file
        """

class ITokenEater(Interface):
    """Eats tokens from the python tokenizer
    """
    
    def getCatalog():
        """Return the catalog of collected message ids as keys of a
        dictionary. The values are a tuple consisting the of the
        filename and the line number at which the message id was
        found.
        """
