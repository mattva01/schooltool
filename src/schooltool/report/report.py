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
Base classes for report reference and request adapters

"""

import urllib

import celery.utils

import zope.i18n.locales
import zope.component
import zope.interface
import zope.location
import zope.publisher.base
import zope.file.file
from persistent.dict import PersistentDict
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility, queryUtility, getGlobalSiteManager
from zope.interface import implements
from zope.intid.interfaces import IIntIds
from zope.publisher.browser import BrowserView
from zope.publisher.browser import BrowserRequest
from zope.publisher.http import HTTPResponse
from zope.traversing.browser.absoluteurl import absoluteURL
from z3c.rml import rml2pdf

import schooltool.common
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.course.interfaces import ISectionContainer
from schooltool.group.interfaces import IGroupContainer
from schooltool.report.interfaces import IReportLinkViewletManager
from schooltool.report.interfaces import IRegisteredReportsUtility
from schooltool.report.interfaces import IReportLinksURL
from schooltool.report.interfaces import IReportTask
from schooltool.report.interfaces import IReportMessage
from schooltool.report.interfaces import IRemoteReportLayer
from schooltool.report.interfaces import IReportFile
from schooltool.schoolyear.interfaces import ISchoolYear
from schooltool.skin import flourish
from schooltool.skin.skin import OrderedViewletManager
from schooltool.task.tasks import RemoteTask
from schooltool.task.tasks import query_messages
from schooltool.task.tasks import Message
from schooltool.task.interfaces import ITaskScheduledNotification
from schooltool.task.tasks import TaskCompletedNotification
from schooltool.task.tasks import TaskScheduledNotification
from schooltool.task.tasks import TaskFailedMessage
from schooltool.term.interfaces import IDateManager

from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


class ReportFile(zope.file.file.File):
    implements(IReportFile)


class ReportLinkViewletManager(OrderedViewletManager):
    implements(IReportLinkViewletManager)


class IFlourishReportLinkViewletManager(flourish.interfaces.IViewletManager,
                                        IReportLinkViewletManager):
    pass


class FlourishReportLinkViewletManager(flourish.viewlet.ViewletManager):
    template = ViewPageTemplateFile('templates/f_report_link_manager.pt')

    @property
    def table(self):
        result = {}
        for viewlet in self.viewlets:
            group = result.setdefault(viewlet.file_type, {
                'file_type': viewlet.file_type.upper(),
                'rows': [],
                })
            group['rows'].append({
                'title': viewlet.title,
                'url': viewlet.link,
                'link_id': viewlet.link.replace('.', '_'),
                'form_id': viewlet.link.replace('.', '_') + '_form',
                'description': viewlet.description,
                })
        return [group for key, group in sorted(result.items())]


class ReportLinkViewlet(object):
    template=ViewPageTemplateFile('templates/report_link.pt')
    group=u''
    title=u''
    link=u'' # an optional relative link - subclasses can override report_link property in some cases

    @property
    def report_link(self):
        return '%s/%s' % (absoluteURL(self.context, self.request), self.link)

    def render(self, *args, **kw):
        return self.template()


class RegisteredReportsUtility(object):
    implements(IRegisteredReportsUtility)

    def __init__(self):
        self.reports_by_group = {}

    def registerReport(self, group, title, description, file_type, name, layer):
        # make a non-translatable group key
        group_key = unicode(group)

        if group_key not in self.reports_by_group:
            self.reports_by_group[group_key] = []
        self.reports_by_group[group_key].append({
            'group': group, # remember the translatable group title
            'title': title,
            'description': description,
            'file_type': file_type,
            'name': name,
            'layer': layer,
            })


def getReportRegistrationUtility():
    """Helper - returns report registration utility and registers a new one
    if missing."""
    utility = queryUtility(IRegisteredReportsUtility)
    if not utility:
        utility = RegisteredReportsUtility()
        getGlobalSiteManager().registerUtility(utility,
            IRegisteredReportsUtility)
    return utility


class ReportLinksURL(BrowserView):
    implements(IReportLinksURL)

    def actualContext(self):
        return self.context

    def __unicode__(self):
        return urllib.unquote(self.__str__()).decode('utf-8')

    def __str__(self):
        return absoluteURL(self.actualContext(), self.request)

    def __call__(self):
        return self.__str__()


class StudentReportLinksURL(ReportLinksURL):

    def actualContext(self):
        return ISchoolToolApplication(None)['persons']


class GroupReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return IGroupContainer(ISchoolYear(current_term))


class SchoolYearReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return ISchoolYear(current_term)


class TermReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return current_term


class SectionReportLinksURL(ReportLinksURL):

    def actualContext(self):
        current_term = getUtility(IDateManager).current_term
        if current_term is None:
            return ISchoolToolApplication(None)
        return ISectionContainer(current_term)


class FlourishSchoolReportLinksURL(ReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/manage'


class FlourishGroupReportLinksURL(GroupReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/groups'


class FlourishSchoolYearReportLinksURL(SchoolYearReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/schoolyears'


class FlourishTermReportLinksURL(TermReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/terms'


class FlourishSectionReportLinksURL(SectionReportLinksURL):

    def __str__(self):
        app = ISchoolToolApplication(None)
        return absoluteURL(app, self.request) + '/sections'


class RemoteReportResponse(HTTPResponse):
    pass


class ReportResourceURL(object):
    zope.component.adapts(IRemoteReportLayer)
    zope.interface.implements(schooltool.common.IResourceURIGetter)

    def __init__(self, request):
        self.request = request

    def __call__(self, library_name, resource_name):
        if not resource_name:
            return None
        fake_request = BrowserRequest('', {})
        zope.interface.directlyProvides(
            fake_request, flourish.interfaces.IFlourishLayer)
        if library_name is not None:
            library = zope.component.queryAdapter(
                fake_request, name=library_name)
            resource = library.get(resource_name)
        else:
            resource = zope.component.queryAdapter(
                fake_request, name=resource_name)
        if resource is None:
            return None
        result = schooltool.common.data_uri(
            resource.context.data,
            mime=resource.context.content_type)
        return result


class RemoteRequestParams(PersistentDict):
    locale_id = None


class RemoteReportRequest(object):
    implements(IRemoteReportLayer)

    response = None
    debug = None
    annotations = None
    locale = None
    interaction = None
    form = None
    URL = ''
    task = None

    def __init__(self, params=None, task=None):
        self.task = task
        if params is None:
            params = {}
        self.form = dict(params)
        self.response = RemoteReportResponse()
        self.debug = zope.publisher.base.DebugFlags()
        self.annotations = {}
        locale_id = getattr(params, 'locale_id', None)
        if locale_id is not None:
            self.locale = zope.i18n.locales.Locale(locale_id)

    @property
    def task_id(self):
        if self.task is None:
            return None
        return self.task.task_id

    def get(self, value, default=None):
        return self.form.get(value, default)

    def __getitem__(self, name):
        return self.form[name]

    def __contains__(self, name):
        return name in self.form

    def getVirtualHostRoot(self):
        return None

    def getApplicationURL(self, depth=0, path_only=False):
        return ''


class AbstractReportTask(RemoteTask):
    implements(IReportTask)

    routing_key = "zodb.report"
    report = None

    abstract = True

    view_name = None
    factory_name = None

    context_intid = None

    def __init__(self, report_builder, context, remote_request=None):
        RemoteTask.__init__(self)
        if isinstance(report_builder, str):
            self.view_name = report_builder
        else:
            self.factory = report_builder
        self.context = context
        if remote_request is None:
            self.request_params = RemoteRequestParams()
        else:
            self.request_params = remote_request

    def default_request_param(self, name, other):
        if (name not in self.request_params and
            name in other):
            self.request_params[name] = other[name]

    def update(self, request):
        super(AbstractReportTask, self).update(request)
        if (self.request_params.locale_id is None and
            request.locale is not None):
            self.request_params.locale_id = request.locale.id
        self.default_request_param('HTTP_ACCEPT_LANGUAGE', request)

    def beginRequest(self, params=None):
        # XXX: move begin/end requests to runTransaction level
        if params is None:
            params = self.request_params
        request = RemoteReportRequest(params, task=self)
        # XXX:
        from schooltool.app.security import Principal
        from zope.security.checker import ProxyFactory
        principal = Principal(self.creator.__name__, 'XXX:title',
                              person=ProxyFactory(self.creator))
        request.principal = principal
        zope.security.management.endInteraction()
        zope.security.management.newInteraction(request)

    def endRequest(self, request=None):
        zope.security.management.endInteraction()

    def getCurrentRequest(self):
        policy = zope.security.management.queryInteraction()
        if policy is None:
            return None
        requests = getattr(policy, 'participations', ())
        if not requests:
            return None
        return requests[0]

    def execute(self, celery_task, *args, **kwargs):
        self.beginRequest()
        renderer = self.getRenderer()
        if renderer is None:
            return # skip the report
        report_file = self.renderToFile(renderer, *args, **kwargs)
        self.report = report_file
        self.endRequest()

    def complete(self, request, result):
        self.beginRequest()
        res = super(AbstractReportTask, self).complete(request, result)
        self.endRequest()
        return res

    def fail(self, request, result, traceback):
        self.beginRequest()
        res = super(AbstractReportTask, self).fail(request, result, traceback)
        self.endRequest()
        return res

    def getRenderer(self, request=None):
        context = self.context
        if context is None:
            return None
        if request is None:
            request = self.getCurrentRequest()
        renderer = None
        factory = self.factory
        if factory is not None:
            renderer = factory(context, request)
        else:
            renderer = zope.component.queryMultiAdapter(
                (context, request), name=self.view_name)
        return renderer

    def renderToFile(self, renderer, *args, **kwargs):
        raise NotImplemented()

    def makeReportFile(self, filename, data):
        raise NotImplemented()

    @property
    def factory(self):
        # higher versions of celery:
        # result = kombu.utils.symbol_by_name(self.factory_name)
        result = celery.utils.get_symbol_by_name(self.factory_name)
        return result

    @factory.setter
    def factory(self, value):
        try:
            self.factory_name = '%s:%s' % (value.__module__, value.__name__)
        except AttributeError, e:
            raise e

    @property
    def context(self):
        int_ids = getUtility(IIntIds)
        obj = int_ids.queryObject(self.context_intid)
        return obj

    @context.setter
    def context(self, value):
        int_ids = getUtility(IIntIds)
        intid = int_ids.getId(value)
        self.context_intid = intid


class ReportTask(AbstractReportTask):

    def renderToFile(self, renderer, *args, **kwargs):
        # XXX:
        #if not schooltool.app.pdf.isEnabled():
        #    return translate(renderer.pdf_disabled_text,
        #                     context=renderer.request)
        renderer.update()
        rml = renderer.render()
        filename = renderer.filename
        stream = rml2pdf.parseString(rml, filename=filename or None)
        data = stream.getvalue()
        pdf = self.makeReportFile(filename, data)
        return pdf

    def makeReportFile(self, filename, data):
        if not filename or not filename.strip():
            filename = 'report.pdf'
        pdf = ReportFile()
        pdf.mimeType = 'application/pdf'
        pdf.__name__ = filename
        stream = pdf.open('w')
        stream.write(data)
        stream.close()
        return pdf


class OldReportTask(ReportTask):

    def renderToFile(self, renderer, *args, **kwargs):
        # XXX:
        #if not schooltool.app.pdf.isEnabled():
        #    return translate(renderer.pdf_disabled_text,
        #                     context=renderer.request)
        filename, data = renderer.renderToFile()
        if data is None:
            return None
        pdf = self.makeReportFile(filename, data)
        return pdf


class ReportMessage(Message):
    implements(IReportMessage)

    report = None
    requested_on = None
    group = _("Reports")
    filename = None

    def __init__(self, title=None,
                 requested_on=None, filename=None):
        Message.__init__(self, title=title)
        self.requested_on = requested_on
        self.filename = filename or 'report.pdf'


class OnReportScheduled(TaskScheduledNotification):

    def __init__(self, task, http_request):
        super(TaskScheduledNotification, self).__init__(
            task, http_request)
        self.request = RemoteReportRequest(task.request_params)

    def send(self):
        renderer = self.task.getRenderer(request=self.request)
        subscribers = zope.component.getAdapters(
            (self.task, self.request, renderer),
            ITaskScheduledNotification)
        for name, subscriber in subscribers:
            subscriber(name=name)


class ReportFailedMessage(ReportMessage, TaskFailedMessage):

    def __init__(self, task, requested_on=None, filename=None):
        ReportMessage.__init__(self, requested_on=requested_on, filename=filename)
        TaskFailedMessage.__init__(self, task)


class OnPDFReportScheduled(TaskScheduledNotification):

    view = None
    message_factory = ReportMessage

    def __init__(self, task, request, view):
        super(OnPDFReportScheduled, self).__init__(task, request)
        self.view = view

    def makeReportTitle(self):
        title = getattr(self.view, 'message_title', None)
        if not title:
            title = getattr(self.view, 'filename', None)
        if not title:
            title = _(u'report')
        return title

    def send(self):
        view = self.view
        view.render_invariant = True
        task = self.task
        title = self.makeReportTitle()
        msg = self.message_factory(
            title=title,
            requested_on=task.scheduled,
            filename=view.filename,
            )
        msg.send(sender=task, recipients=[self.task.creator])


class GeneratedReportMessage(ReportMessage):

    def __init__(self, *args, **kw):
        if not kw.get('title'):
            kw['title'] = kw.get('filename', _('report'))
        report = kw.pop('report', None)
        super(GeneratedReportMessage, self).__init__(*args, **kw)
        self.report = report
        if self.report is not None:
            self.report.__parent__ = self


class OnReportGenerated(TaskCompletedNotification):

    @property
    def messages(self):
        messages = query_messages(self.task)
        return messages

    def send(self):
        messages = self.messages
        for message in messages:
            generated_msg = GeneratedReportMessage(
                title=getattr(message, 'title', None),
                requested_on=message.requested_on,
                filename=message.filename,
                report = self.task.report)
            generated_msg.updated_on = self.task.utcnow
            generated_msg.replace(
                message,
                sender=self.task.creator,
                recipients=message.recipients)
            # XXX: set message expiration date
            # message.expires_on =
