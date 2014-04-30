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
Functional selenium tests for schooltool.schoolyear
"""
import unittest

from schooltool.testing.util import format_table
from schooltool.testing.selenium import collect_ftests
from schooltool.schoolyear.stesting import schoolyear_selenium_layer


def print_timetables_table(browser):
    driver = browser.driver
    for tr in driver.execute_script(
            'return $(arguments[0])', 'table tbody tr'):
        row = []
        for i, td in enumerate(driver.execute_script(
                'return $(arguments[0]).find("td")', tr)):
            e = td
            if i == 0:
                e = driver.execute_script(
                    'return $(arguments[0]).find("a")', td)[0]
            row.append(e.text)
        print ', '.join(row)


def print_timetable(browser):
    driver = browser.driver
    h3s = driver.execute_script('return $(arguments[0])', 'h3')
    tables = []
    for table in driver.execute_script('return $(arguments[0])', 'table'):
        rows = []
        row = []
        for th in driver.execute_script(
                'return $(arguments[0]).find(arguments[1])', table, 'thead th'):
            row.append(th.text)
        rows.append(row)
        for tr in driver.execute_script(
                'return $(arguments[0]).find(arguments[1])', table, 'tbody tr'):
            row = []
            for td in driver.execute_script(
                'return $(arguments[0]).find(arguments[1])', tr, 'td'):
                spans = []
                for span in driver.execute_script(
                        'return $(arguments[0]).find(arguments[1])',
                        td, 'span'):
                    text = span.text.strip()
                    if text:
                        spans.append(text)
                row.append(' '.join(spans))
            rows.append(row)
        tables.append(rows)
    print h3s[0].text
    print '-' * len(h3s[0].text)
    print h3s[1].text
    print format_table(tables[0], header_rows=1)
    print h3s[2].text
    print format_table(tables[1], header_rows=1)


def test_suite():
    extra_globs = {
        'print_timetables_table': print_timetables_table,
        'print_timetable': print_timetable,
        }
    return collect_ftests(layer=schoolyear_selenium_layer,
                          extra_globs=extra_globs)


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
