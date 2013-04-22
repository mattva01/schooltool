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
from urllib import quote, urlencode, unquote_plus
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts, queryMultiAdapter
from zope.i18n import translate
from zope.i18n.interfaces.locales import ICollator
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces import IPublishTraverse
from zope.traversing.browser.absoluteurl import AbsoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.interface import implements
from zope.cachedescriptors.property import Lazy
from z3c.form import button

import schooltool.traverser.traverser
from schooltool.person.interfaces import IPerson
from schooltool.report.interfaces import IReportLinksURL
from schooltool.report.interfaces import IReportFile
from schooltool.report.report import IFlourishReportLinkViewletManager
from schooltool.report.report import getReportRegistrationUtility
from schooltool.report.report import ReportTask
from schooltool.skin import flourish
from schooltool.skin.flourish.page import WideContainerPage
from schooltool.skin.flourish.page import RefineLinksViewlet
from schooltool.skin.flourish import IFlourishLayer
from schooltool.skin.flourish.form import DialogForm
from schooltool.task.tasks import query_message
from schooltool.task.interfaces import IRemoteTask
from schooltool.task.browser.task import MessageDialog

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
    content_template = ViewPageTemplateFile('templates/f_report_links.pt')
    subtitle = _('Reports')


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


class FlourishReportReferenceView(WideContainerPage, ReportReferenceView):

    def done_link(self):
        return absoluteURL(self.context, self.request) + '/manage'


    def rows(self):
        self.collator = ICollator(self.request.locale)
        utility = getReportRegistrationUtility()
        app = self.context
        rows = {}
        for group_key, group_reports in utility.reports_by_group.items():
            reference_url = reportLinksURL(app, self.request, name=group_key)
            for report in group_reports:
                group = report['group']
                name = report['name']
                row = {
                    'url': reference_url,
                    'group': group,
                    'title': report['title'],
                    'file_type': report['file_type'].upper(),
                    'description': report['description'],
                    }
                # XXX: this check is needed to override old skin
                #      report links with flourish ones
                if (group, name) not in rows or \
                   report['layer'] is IFlourishLayer:
                    rows[group, name] = row
        return sorted(rows.values(), key=self.sortKey)

    def sortKey(self, row):
        return self.collator.key(row['group']), self.collator.key(row['title'])


class ReportsLinks(RefineLinksViewlet):
    """Reports links viewlet."""

    implements(IFlourishReportLinkViewletManager)

    body_template = ViewPageTemplateFile('templates/f_report_links_body.pt')

    @Lazy
    def items(self):
        items = super(ReportsLinks, self).items
        result = []
        for item in items:
            viewlet = item['viewlet']
            url = viewlet.link
            is_report_link = bool(getattr(viewlet, 'file_type', ''))
            if is_report_link:
                file_type = translate(viewlet.file_type,
                                      context=self.request)
                description = translate(viewlet.description,
                                        context=self.request)
                querystring = urlencode({
                        'file_type': file_type.encode('utf-8').upper(),
                        'description': description.encode('utf-8')})
                url = '%s?%s' % (viewlet.report_link, querystring)
            result.append({
                    'class': item['class'],
                    'viewlet': viewlet,
                    'content': item['content'],
                    'is_report_link': is_report_link,
                    'link_id': viewlet.link.replace('.', '_'),
                    'form_id': viewlet.link.replace('.', '_') + '_form',
                    'title': translate(viewlet.title, context=self.request),
                    'url': url,
                    })
        return result


class RequestReportDownloadDialog(DialogForm):

    template = ViewPageTemplateFile('templates/f_request_report_download.pt')

    dialog_submit_actions = ('download',)
    dialog_close_actions = ('cancel',)
    label = None

    @button.buttonAndHandler(_("Download"), name='download')
    def handleDownload(self, action):
        self.request.response.redirect(self.nextURL())
        # We never have errors, so just close the dialog.
        self.ajax_settings['dialog'] = 'close'

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(RequestReportDownloadDialog, self).updateActions()
        self.actions['download'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        raise NotImplementedError("nextURL must redirect to a 'downloadable' view")

    @property
    def file_type(self):
        if 'file_type' in self.request:
            return unquote_plus(self.request['file_type'])

    @property
    def description(self):
        if 'description' in self.request:
            return unquote_plus(self.request['description'])


class RequestRemoteReportDialog(RequestReportDownloadDialog):

    template = ViewPageTemplateFile('templates/f_request_report_download.pt')

    dialog_submit_actions = ('download',)
    dialog_close_actions = ('cancel',)
    label = None

    report_builder = None # report generating class or view name

    task_factory = ReportTask

    report_task = None
    replace_dialog = None

    @button.buttonAndHandler(_("Generate"), name='download')
    def handleDownload(self, action):
        task = self.task_factory(self.report_builder, self.target)
        self.schedule(task)
        self.report_task = task
        message = query_message(task)
        if message is None:
            self.ajax_settings['dialog'] = 'close'
            return
        content = queryMultiAdapter(
            (message, self.request), name='dialog')
        if content is None:
            self.ajax_settings['dialog'] = 'close'
            return
        self.replace_dialog = content

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def updateActions(self):
        super(RequestReportDownloadDialog, self).updateActions()
        self.actions['download'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def target(self):
        return self.context

    def schedule(self, task):
        """Subclasses should update task.request_params dict here."""
        task.schedule(self.request)

    def render(self, *args, **kw):
        if self.replace_dialog is not None:
            return self.replace_dialog.render(*args, **kw)
        return super(RequestRemoteReportDialog, self).render(*args, **kw)


class ReportAbsoluteURLAdapter(AbsoluteURL):
    adapts(IReportFile, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        base = absoluteURL(self.context.__parent__, self.request)
        filename = quote(unicode(self.context.__name__))
        url = base + '/download/' + filename
        return url

    __call__ = __str__


class ReportMessageDownloads(object):
    implements(IPublishTraverse)
    file_attrs = ('report',)
    files = None

    def __init__(self, context, request, name='download'):
        self.__name__ = name
        self.__parent__ = context
        self.context = context
        self.request = request
        self.collectFiles()

    def collectFiles(self):
        self.files = {}
        for attr in self.file_attrs:
            value = getattr(self.context, attr, None)
            if value is None:
                continue
            self.files[value.__name__] = value

    def publishTraverse(self, request, name):
        if name not in self.files:
            raise NotFound(self.context, name, self.request)
        return self.files[name]


class ReportMessageDownloadsPlugin(schooltool.traverser.traverser.TraverserPlugin):

    def traverse(self, name):
        return ReportMessageDownloads(self.context, self.request)


class DownloadReportDialog(MessageDialog):

    template = flourish.templates.File('templates/f_download_report_dialog.pt')

    @property
    def report(self):
        return getattr(self.context, 'report', None)

    @property
    def report_generated(self):
        return bool(self.report)

    @property
    def main_recipient(self):
        person = IPerson(self.request, None)
        if self.context.recipients is None:
            return None
        recipients = sorted(self.context.recipients, key=lambda r: r.__name__)
        if person in recipients:
            return person
        for recipient in recipients:
            if flourish.canView(recipient):
                return recipient
        return None

    @Lazy
    def failure_ticket_id(self):
        sender = self.context.sender
        if (IRemoteTask.providedBy(sender) and
            sender.failed):
            return sender.__name__
        return None


class ShortReportMessage(flourish.content.ContentProvider):

    @Lazy
    def failure_ticket_id(self):
        sender = self.context.sender
        if (IRemoteTask.providedBy(sender) and
            sender.failed):
            return sender.__name__
        return None
