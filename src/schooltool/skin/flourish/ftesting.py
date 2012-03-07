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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#


def registerSeleniumSetup():
    try:
        import selenium
    except ImportError:
        return
    from schooltool.testing import registry
    import schooltool.testing.selenium
    import selenium.webdriver.common.keys

    def type_in_date(element, date):
        keys = selenium.webdriver.common.keys.Keys
        element.type(keys.DELETE, date, keys.ENTER)
        browser = element.browser
        if browser is not None:
            browser.wait_no(lambda: browser.query.id('ui-datepicker-div').is_displayed())
    registry.register('SeleniumHelpers',
        lambda: schooltool.testing.selenium.registerElementUI('enter_date', type_in_date))

registerSeleniumSetup()
del registerSeleniumSetup
