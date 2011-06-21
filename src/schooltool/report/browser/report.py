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
Report browser views.

"""
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.publisher.browser import BrowserView

from schooltool.report.interfaces import IReportLinksURL
from schooltool.report.report import getReportRegistrationUtility
from schooltool.report.report import ReportLinkViewletManager
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


class ReportsView(BrowserView):

    template = ViewPageTemplateFile('templates/report_links.pt')

    def __call__(self):
        return self.template()


class StudentReportsView(ReportsView):

    title = _('Student Reports')


class GroupReportsView(ReportsView):

    title = _('Group Reports')


class SchoolYearReportsView(ReportsView):

    title = _('School Year Reports')


class TermReportsView(ReportsView):

    title = _('Term Reports')


class SectionReportsView(ReportsView):

    title = _('Section Reports')


class FlourishReportsView(flourish.page.Page):
    """Report request view base class."""


class FlourishStudentReportsView(FlourishReportsView):

    title = _('Student Reports')


class FlourishReportsInfo(flourish.page.Content):
    body_template = ViewPageTemplateFile('templates/f_report_links.pt')


def reportLinksURL(ob, request, name=''):
    """Helper method to obtain the report links URL"""
    url = queryMultiAdapter((ob, request), IReportLinksURL, name=name)
    if url is None:
       return ''
    return url


class ReportReferenceView(BrowserView):

    template = ViewPageTemplateFile('templates/report_reference.pt')

    def __call__(self):
        return self.template()

    def rows(self):
        collator = ICollator(self.request.locale)
        utility = getReportRegistrationUtility()
        app = self.context

        rows = []
        for group_key, group_reports in utility.reports_by_group.items():
            reference_url = reportLinksURL(app, self.request, name=group_key)
            for report in group_reports:
                row = { 
                    'url': reference_url,
                    'group': report['group'],
                    'title': report['title'],
                    'description': report['description'],
                    }
                rows.append([collator.key(report['group']),
                             collator.key(report['title']),
                             row])

        return [row for group, title, row in sorted(rows)]

