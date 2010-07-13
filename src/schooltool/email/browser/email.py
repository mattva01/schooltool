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
Email browser views.

"""
import pytz
import urllib
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import implements, Interface, directlyProvides
from zope.interface import invariant, Invalid
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema import Text, Datetime
from zope.schema import TextLine, Int, Password, Bool
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.viewlet.viewlet import ViewletBase

from z3c.form import form, field, button
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget
from zc.table.column import GetterColumn
from zc.table.interfaces import ISortableColumn

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import SchoolToolMessage as _
from schooltool.skin.containers import TableContainerView
from schooltool.table.table import SchoolToolTableFormatter
from schooltool.email.interfaces import IEmailContainer, IEmail
from schooltool.email.interfaces import IEmailUtility
from schooltool.email.mail import Email, status_messages


# Helpers

def mail_enabled():
    utility = getUtility(IEmailUtility)
    return utility.enabled()


def to_application_timezone(dt):
    app = ISchoolToolApplication(None)
    app_timezone = pytz.timezone(IApplicationPreferences(app).timezone)
    return dt.astimezone(app_timezone)


def get_application_preferences():
    app = ISchoolToolApplication(None)
    return IApplicationPreferences(app)


def set_server_status_message(form, container):
    form.widgets['server_status'].mode = 'display'
    if container.hostname:
        info = '%s:%s' % (container.hostname,
                          container.port or '25')
        form.widgets['server_status'].value = _('Enabled on ${info}',
                                                mapping={'info': info})
        form.widgets['server_status'].style = u'color: green;'
    else:
        form.widgets['server_status'].value = _('Disabled')
        form.widgets['server_status'].style = u'color: red;'


# Email Settings

class IEmailSettingsEditForm(Interface):

    server_status = TextLine(
        title=_('Server Status'),
        description=_('Current status of the SchoolTool email service'),
        required=False)

    enabled = Bool(
        title=_('Enable'),
        description=_('Mark to enable the service.'),
        default=False,
        required=False)

    hostname = TextLine(
        title=_('Hostname'),
        description=_('SMTP server hostname. Required if the service is enabled.'),
        required=False)

    port = Int(
        title=_('Port'),
        description=_('Port of the SMTP service. Using 25 by default.'),
        min=0,
        default=25,
        required=False)

    username = TextLine(
        title=_('Username'),
        description=_('Username used for optional SMTP authentication.'),
        required=False)

    dummy_password = TextLine(
        title=_('Current Password'),
        description=_('Current password to authenticate to the SMTP server.'),
        required=False)
    
    password = Password(
        title=_('New Password'),
        description=_('The password to authenticate to the SMTP server.'),
        required=False)

    password_confirmation = Password(
        title=_('Confirm New Password'),
        description=_('Verification for the new password.'),
        required=False)

    tls = Bool(
        title=_('TLS'),
        description=_('Use TLS connection?'),
        default=False,
        required=False)

    @invariant
    def checkPasswordConfirmation(obj):
        if obj.password != obj.password_confirmation:
            raise Invalid(_("New passwords don't match"))

    @invariant
    def checkHostname(obj):
        if obj.enabled and not obj.hostname:
            raise Invalid(_("Hostname is required for enabling the service"))


class EmailSettingsEditFormAdapter(object):

    implements(IEmailSettingsEditForm)
    adapts(IEmailContainer)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __setattr__(self, name, value):
        if name in ('server_status', 'dummy_password',
                    'password_confirmation',):
            return
        if name in ('username',):
            if not value:
                self.context.password = None
        if name in ('password',):
            if not value:
                return
        setattr(self.context, name, value)

    def __getattr__(self, name):
        if name in ('server_status', 'dummy_password',
                    'password_confirmation'):
            return
        return getattr(self.context, name)


class EmailSettingsEditView(form.EditForm):

    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/email_form.pt')
    label = _('Change Email Settings')
    fields = field.Fields(IEmailSettingsEditForm)
    fields['enabled'].widgetFactory = SingleCheckBoxFieldWidget

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(EmailSettingsEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def update(self):
        super(EmailSettingsEditView, self).update()
        self.updateDisplayWidgets()

    def updateDisplayWidgets(self):
        set_server_status_message(self, self.context)
        self.widgets['dummy_password'].mode = 'display'
        if self.context.password:
            mask = '*'*len(self.context.password)
            self.widgets['dummy_password'].value = mask
        else:
            self.widgets['dummy_password'].value = _('Unset')


# Email

class IEmailDisplayForm(Interface):

    server_status = TextLine(
        title=_('Server Status'),
        description=_('Current status of the SchoolTool email service'),
        required=False)

    from_address = TextLine(
        title=_(u'From'),
        description=_(u'The sender address'),
        required=False)

    to_addresses = TextLine(
        title=_(u'To'),
        description=_(u'Recipient addresses comma separated'),
        required=False)

    time_created = Datetime(
        title=_(u'Created on'),
        description=_(u'Date and time when the message was created'),
        required=False)

    subject = TextLine(
        title=_(u'Subject'),
        description=_(u'Subject of the message'),
        required=False)

    body = Text(
        title=_(u'Body'),
        description=_(u'Body of the message'),
        required=False)

    status = TextLine(
        title=_(u'Email Status'),
        description=_(u'Status of the message'),
        required=False)

    time_sent = Datetime(
        title=_(u'Last time tried'),
        description=_(u'Date and time when the message was last tried'),
        required=False)


class EmailDisplayFormAdapter(object):

    implements(IEmailDisplayForm)
    adapts(IEmail)

    def __init__(self, context):
        self.__dict__['context'] = context

    def __getattr__(self, name):
        if name in ('server_status', 'status',):
            return
        if name == 'to_addresses':
            return ', '.join(getattr(self.context, name))
        if name in ('time_created', 'time_sent',):
            return to_application_timezone(getattr(self.context, name))
        return getattr(self.context, name)


class EmailView(form.Form):

    template = ViewPageTemplateFile('templates/email_form.pt')
    label = _('Email View')
    fields = field.Fields(IEmailDisplayForm)
    mode = 'display'

    def getDeleteURL(self, email):
        params = [('delete.%s' % (email.__name__.encode('utf-8')), ''),
                  ('CONFIRM', 'Confirm')]
        return '%s?%s' % (absoluteURL(email.__parent__, self.request),
                          urllib.urlencode(params),)
        
    @button.buttonAndHandler(_('Retry'))
    def handle_retry_action(self, action):
        utility = getUtility(IEmailUtility)
        email = removeSecurityProxy(self.context)
        success = utility.send(email)
        if success:
            url = self.getDeleteURL(email)
        else:
            url = absoluteURL(email.__parent__, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Delete'))
    def handle_delete_action(self, action):
        url = self.getDeleteURL(self.context)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context.__parent__, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(EmailView, self).updateActions()
        if mail_enabled():
            self.actions['retry'].addClass('button-ok')
        else:
            self.actions['retry'].mode = 'display'
        self.actions['delete'].addClass('button-cancel')
        self.actions['cancel'].addClass('button-cancel')

    def update(self):
        super(EmailView, self).update()
        self.updateDisplayWidgets()

    def updateDisplayWidgets(self):
        set_server_status_message(self, self.context.__parent__)
        if self.context.status_code is not None:
            # XXX: mapping is a read-only attribute for MessageIDs
            # and translate doesn't use the mapping parameter
            message = _(status_messages[self.context.status_code],
                        mapping=self.context.status_parameters)
            self.widgets['status'].value = translate(message,
                                                     context=self.request)
            self.widgets['status'].style = u'color: red;'


# Email Container View and Table Formatter

def to_addresses_formatter(value, item, formatter):
    return ', '.join(item.to_addresses)


def datetime_formatter(value, item, formatter):
    preferences = get_application_preferences()
    preferred_datetime_format = '%s %s' % (preferences.dateformat,
                                           preferences.timeformat)
    return to_application_timezone(value).strftime(preferred_datetime_format)


def subject_formatter(value, item, formatter):
    if value is None:
        return ''
    return value


def email_container_table_columns():
    from_address = GetterColumn(name='from_address',
                                title=_(u'From'),
                                getter=lambda i, f: i.from_address,
                                subsort=True)
    directlyProvides(from_address, ISortableColumn)
    to_addresses = GetterColumn(name='to_addresses',
                                title=_(u'To'),
                                getter=lambda i, f: i.to_addresses,
                                cell_formatter=to_addresses_formatter,
                                subsort=True)
    directlyProvides(to_addresses, ISortableColumn)
    subject = GetterColumn(name='subject',
                           title=_(u'Subject'),
                           getter=lambda i, f: i.subject,
                           cell_formatter=subject_formatter,
                           subsort=True)
    directlyProvides(subject, ISortableColumn)    
    time_created = GetterColumn(name='time_created',
                                title=_(u'Created on'),
                                getter=lambda i, f: i.time_created,
                                cell_formatter=datetime_formatter,
                                subsort=True)
    directlyProvides(time_created, ISortableColumn)
    time_sent = GetterColumn(name='time_sent',
                                title=_(u'Last time tried'),
                                getter=lambda i, f: i.time_sent,
                                cell_formatter=datetime_formatter,
                                subsort=True)
    directlyProvides(time_sent, ISortableColumn)
    return [from_address, to_addresses, subject, time_created, time_sent]


class EmailContainerViewTableFormatter(SchoolToolTableFormatter):

    columns = lambda self: email_container_table_columns()

    def sortOn(self):
        return (('time_created', True),)


class EmailContainerView(TableContainerView):

    template = ViewPageTemplateFile('templates/email_container.pt')
    delete_template = ViewPageTemplateFile('templates/email_delete.pt')
    index_title = _('Email Queue')

    @property
    def itemsToDelete(self):
        return sorted(
            super(EmailContainerView, self)._listItemsForDeletion(),
            key=lambda obj: obj.time_created)

    def mailEnabled(self):
        return mail_enabled()

    def serverStatus(self):
        result = {}
        if self.context.hostname:
            info = '%s:%s' % (self.context.hostname,
                              self.context.port or '25')
            result['status'] = _('Enabled on ${info}',
                                 mapping={'info': info})
            result['color'] = 'green'
        else:
            result['status'] = _('Disabled')
            result['color'] = 'red'
        return result

    def __call__(self):
        if 'RETRY' in self.request:
            utility = getUtility(IEmailUtility)
            for key in self.listIdsForDeletion():
                email = removeSecurityProxy(self.context[key])
                success = utility.send(email)
                if success:
                    del self.context[key]
        return super(EmailContainerView, self).__call__()


# URL Adapter

class EmailContainerAbsoluteURLAdapter(BrowserView):

    adapts(IEmailContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/email'

    __call__ = __str__


# Action viewlets

class QueueActionMenuViewlet(ViewletBase):

    @property
    def title(self):
        count = len(self.context)
        if count:
            return _('Queue (${count} failed)', mapping={'count': count})
        else:
            return _('Queue')


# XXX: remove Send Email form?

class ISendEmailForm(Interface):

    server_status = TextLine(
        title=_('Server Status'),
        description=_('Current status of the SchoolTool email service'),
        required=False)
    
    from_address = TextLine(
        title=_(u'From'),
        description=_(u'The sender address'))

    to_addresses = TextLine(
        title=_(u'To'),
        description=_(u'Recipient addresses comma separated'))

    subject = TextLine(
        title=_(u'Subject'),
        description=_(u'Subject of the message'),
        required=False)

    body = Text(
        title=_(u'Body'),
        description=_(u'Body of the message'))


class SendEmailFormAdapter(object):

    implements(ISendEmailForm)
    adapts(IEmailContainer)

    def __init__(self, context):
        self.context = context


class SendEmailView(form.Form):

    template = ViewPageTemplateFile('templates/email_form.pt')
    label = _('Send Email')
    fields = field.Fields(ISendEmailForm)

    @button.buttonAndHandler(_('Send'))
    def handle_send_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = _('There were some errors.')
            return
        from_address = data['from_address']
        to_addresses = [address.strip()
                        for address in data['to_addresses'].split(',')]
        body = data['body']
        subject = data['subject']
        email = Email(from_address, to_addresses, body, subject)
        utility = getUtility(IEmailUtility)
        success = utility.send(email)
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(SendEmailView, self).updateActions()
        if not mail_enabled():
            self.actions['send'].mode = 'display'
        else:
            self.actions['send'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def update(self):
        super(SendEmailView, self).update()
        self.updateDisplayWidgets()

    def updateDisplayWidgets(self):
        set_server_status_message(self, self.context)
