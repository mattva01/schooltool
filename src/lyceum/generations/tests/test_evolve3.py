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
Unit tests for schooltool.generations.evolve3

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
        self['persons'] = {}

def doctest_evolve():
    r"""Doctest for evolution to generation 3.

      >>> context = ContextStub()
      >>> context.root_folder['app'] = app = AppStub()
      >>> from lyceum.person.person import LyceumPerson
      >>> alpha = LyceumPerson('alpha', 'Alpha alpha', 'Foo')
      >>> beta = LyceumPerson('alpha', 'Betha', 'Bar')
      >>> app['persons']['alpha'] = alpha
      >>> alpha.__name__ = 'alpha'
      >>> app['persons']['beta'] = beta
      >>> beta.__name__ = 'beta'
      >>> gamma = LyceumPerson('gamma', 'B.', 'Teacher')
      >>> app['persons']['gamma'] = gamma
      >>> gamma.__name__ = 'gamma'

    Do the evolution:

      >>> from lyceum.generations.evolve3 import evolve
      >>> evolve(context)

    Now first names of all the studenrs should be properly
    capitalized, while first names of teachers should stay untouched:

      >>> beta.title
      'Bar Betha'

      >>> alpha.title
      'Foo Alpha Alpha'

      >>> gamma.title
      'Teacher B.'

    """

def test_suite():
    return doctest.DocTestSuite(optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
