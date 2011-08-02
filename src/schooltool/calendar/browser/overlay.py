#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
SchoolTool calendar overlay views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

import schooltool.skin.flourish.page
from schooltool.app.browser.overlay import CalendarOverlayBase
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


class CalendarOverlayView(flourish.page.Refine, CalendarOverlayBase):
    title = _('Show')
    body_template = ViewPageTemplateFile('templates/calendar_overlay.pt')
    update = CalendarOverlayBase.update
