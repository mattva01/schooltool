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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
from schooltool.testing.util import format_table
from schooltool.testing.analyze import queryHTML
from schooltool.testing.functional import ZCMLLayer
from schooltool.testing.selenium import SeleniumLayer

here = os.path.dirname(__file__)

app_functional_layer = ZCMLLayer(os.path.join(here, 'ftesting.zcml'),
                                 __name__,
                                 'app_functional_layer')

app_selenium_layer = SeleniumLayer(os.path.join(here, 'stesting.zcml'),
                                   __name__+'_selenium',
                                   'app_functional_layer')

app_selenium_oldskin_layer = SeleniumLayer(os.path.join(here,
                                           'stesting-oldskin.zcml'),
                                           __name__+'_oldskin',
                                           'app_functional_layer')


def format_weekly_calendar(contents):
    table = []
    for n, row in enumerate(queryHTML('//table[@id="calendar-view-week"]//tr', contents)):
        if n == 0:
            header = []
            for cell in queryHTML('//tr//th/a/text()', str(row)):
                header.append(cell)
            table.append(header)
        else:
            block = []
            for cell in queryHTML('//tr//td', str(row)):
                events = []
                for event in queryHTML('//td//a//span/text()', str(cell)):
                    events.append(event)
                block.append(", ".join(events))
            table.append(block)
    return format_table(table, header_rows=1)
