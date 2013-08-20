#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Unit tests for schooltool.generations.evolve28
"""
import unittest
import doctest
import os.path
import transaction

from zope.app.publication.zopepublication import ZopePublication
from zope.app.testing import setup
from ZODB.FileStorage.FileStorage import FileStorage
from ZODB.DemoStorage import DemoStorage
from ZODB.DB import DB
from zope.app.appsetup import config

import schooltool.app


class ContextStub(object):

    def __init__(self, db):
        connection = db.open()
        self.root_folder = connection.root()
        self.connection = connection


def FileStorage28():
    here = os.path.dirname(__file__)
    data_fs = os.path.join(here, "Data28.fs")
    return FileStorage(data_fs)


def doctest_evolve28():
    """Test that a database at generation 28 can be opened.

       >>> storage = DemoStorage(base=FileStorage28())
       >>> db = DB(storage, database_name="")
       >>> context = ContextStub(db)
       >>> app = context.connection.root()[ZopePublication.root_name]
       >>> from zope.component.hooks import setSite
       >>> setSite(app)

       >>> sy = app['schooltool.schoolyear'][u'2008-2009']
       >>> sy.title, sy.first, sy.last
       ('2008-2009', datetime.date(2008, 10, 1), datetime.date(2009, 1, 16))

       >>> transaction.abort()
       >>> context.connection.close()
       >>> db.close()

    """


def setUp(test):
    # Make sure unit tests are cleaned up
    setup.placefulSetUp()
    setup.placefulTearDown()
    app_module = os.path.dirname(schooltool.app.__file__)
    c = config(os.path.join(app_module, "ftesting.zcml"))


def tearDown(test):
    setup.placelessTearDown()


def test_suite():
    return doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                optionflags=doctest.ELLIPSIS
                                |doctest.REPORT_ONLY_FIRST_FAILURE)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
