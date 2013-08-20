#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Functional selenium tests for schooltool.resource
"""
import unittest

from schooltool.common import parse_date
from schooltool.testing.selenium import collect_ftests
from schooltool.resource.stesting import resource_selenium_layer
from schooltool.skin import flourish


class DateManagementView(flourish.page.Page):

    def __call__(self):
        value = self.request.get('value')
        try:
            today = parse_date(value)
        except (ValueError,):
            return
        self.context.today = today


def test_suite():
    return collect_ftests(layer=resource_selenium_layer)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
