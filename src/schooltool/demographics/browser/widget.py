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

from zope.app.form.browser import DateWidget as DateWidget_
from zope.app.form.browser.widget import renderElement
from zope.app import zapi
from zope.app.component.hooks import getSite

class FancyDateWidget(DateWidget_):
    def __call__(self):
        result = super(FancyDateWidget, self).__call__()
        site_url = zapi.absoluteURL(getSite(), self.request)
        img_tag = renderElement(
            "img",
            cssClass="CalIcon",
            src=site_url + "/@@/calwidget-icon.gif",
            id=self.name + "Icon",
            onmousedown="",
            alt="[popup calendar]",
            onclick="clickWidgetIcon('%s');" % self.name)
        div_tag = renderElement(
            "div",
            id=self.name + "Div",
            style="background: #fff; position: absolute; display: none;")
        return result + img_tag + div_tag
