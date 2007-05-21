#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Unit tests for schooltool.generations.evolve2

$Id$
"""

import unittest

from zope.annotation.interfaces import IAnnotatable
from zope.testing import doctest
from zope.app.folder.folder import Folder
from zope.interface import implements

from schooltool.generations.tests import ContextStub
from schooltool.app.interfaces import ISchoolToolApplication


class AppStub(Folder):
    implements(ISchoolToolApplication, IAnnotatable)

    def __init__(self):
        super(AppStub, self).__init__()

def doctest_evolve():
    r"""Doctest for evolution to generation 2.

        >>> context = ContextStub()
        >>> context.root_folder['app'] = app = AppStub()

    Do the evolution:

        >>> from lyceum.generations.evolve2 import evolve
        >>> evolve(context)

    Now we should have a lyceum journal container in our application:

        >>> list(app.items())
        [(u'lyceum.journal', <lyceum.journal.journal.LyceumJournalContainer object at ...>)]

    """

def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
