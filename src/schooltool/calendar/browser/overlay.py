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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool calendar overlay views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

import schooltool.skin.flourish.page
from schooltool.app.browser.overlay import CalendarOverlayBase
from schooltool.common import DateRange
from schooltool.skin import flourish
from schooltool.term.interfaces import IDateManager
from schooltool.term.interfaces import ITerm

from schooltool.common import SchoolToolMessage as _


class CalendarOverlayView(flourish.page.Refine, CalendarOverlayBase):
    title = _('Show')
    body_template = ViewPageTemplateFile('templates/calendar_overlay.pt')
    update = CalendarOverlayBase.update

    def render(self, *args, **kw):
        if not self.show_overlay():
            return ''
        return flourish.page.Refine.render(self, *args, **kw)

    def grouped_items(self):
        # XXX: this introduces dependency on terms.  A generic grouping
        #      would be more appropriate.
        items = super(CalendarOverlayView, self).items()
        non_term_items = []
        by_term = {}
        current_term = removeSecurityProxy(
            getUtility(IDateManager).current_term)

        for item in items:
            term = ITerm(item['calendar'].__parent__, None)
            unsecure_term = removeSecurityProxy(term)
            if unsecure_term is None:
                non_term_items.append(item)
                continue
            term_range = DateRange(term.first, term.last)
            view_range = self.view.cursor_range
            if term_range.overlaps(view_range):
                if unsecure_term not in by_term:
                    by_term[unsecure_term] = {
                        'group': term,
                        'items': [],
                        'expanded': unsecure_term is current_term,
                        }
                by_term[unsecure_term]['items'].append(item)

        order = sorted(by_term, key=lambda t: t.last, reverse=True)
        result = []
        if non_term_items:
            result.append({
                    'group': None,
                    'items': non_term_items,
                    'expanded': True,
                    })
        for term in order:
            result.append(by_term[term])
        return result

