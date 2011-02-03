#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
Report browser views.

"""
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getAdapters
from zope.i18n.interfaces.locales import ICollator
from zope.publisher.browser import BrowserView

from schooltool.report.interfaces import IReportReference, IReportRequest
from schooltool.common import SchoolToolMessage as _


class ReportReferenceView(BrowserView):

    template = ViewPageTemplateFile('templates/report_reference.pt')

    def __call__(self):
        return self.template()

    def rows(self):
        key_order = ['student', 'group', 'section', 'schoolyear', 'term']
        collator = ICollator(self.request.locale)

        rows = []
        for name, ref in getAdapters((self.context, self.request),
                                     IReportReference):
            row = {
                'category': ref.category,
                'title': ref.title,
                'description': ref.description,
                'url': ref.url,
                }

            for index, key in enumerate(key_order):
                if key == ref.category_key:
                    break
            else:
                index = len(key_order)

            rows.append([index, collator.key(ref.title), row])

        return [row for index, title, row in sorted(rows)]


class ReportRequestView(BrowserView):

    template = ViewPageTemplateFile('templates/report_request.pt')

    def __call__(self):
        return self.template()

    def title(self):
        return '%s %s' % (self.category, _('Reports'))

    def links(self):
        result = []
        for name, req in getAdapters((self.context, self.request),
                                     IReportRequest):
            link = {
                'title': req.title,
                'url': req.url,
                }
            result.append(link)
        return result


class StudentReportRequestView(ReportRequestView):
    category = _('Student')


class GroupReportRequestView(ReportRequestView):
    category = _('Group')


class SchoolYearReportRequestView(ReportRequestView):
    category = _('School Year')


class TermReportRequestView(ReportRequestView):
    category = _('Term')


class SectionReportRequestView(ReportRequestView):
    category = _('Section')

