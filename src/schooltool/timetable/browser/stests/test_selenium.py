#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
Functional selenium tests for schooltool.timetable
"""
import unittest

from schooltool.testing.selenium import collect_ftests
from schooltool.testing.util import format_table
from schooltool.timetable.stesting import timetable_selenium_layer


def print_schedules(browser):
    title_sel = '.container .body > div > h3:not(".done-link")'
    rows = []
    for title in browser.driver.execute_script(
        'return $(arguments[0])', title_sel):
        print title.text
        for table in browser.driver.execute_script(
            'return $(arguments[0]).next().find(arguments[1])',
            title, 'table.timetable'):
            rows.append(
                [th.text
                 for th in browser.driver.execute_script(
                        'return $(arguments[0]).find(arguments[1])',
                        table, 'th.day')])
            for tr in browser.driver.execute_script(
                'return $(arguments[0]).find(arguments[1])',
                table, 'tbody tr'):
                row = []
                for td in browser.driver.execute_script(
                    'return $(arguments[0]).find(arguments[1])',
                    tr, 'td'):
                    row.append(td.text)
                rows.append(row)
    print format_table(rows, header_rows=1)


def test_suite():
    extra_globs = {
        'print_schedules': print_schedules,
        }
    return collect_ftests(layer=timetable_selenium_layer,
                          extra_globs=extra_globs)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
