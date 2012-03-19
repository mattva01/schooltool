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
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.i18n import translate
from zope.interface import implements, Interface, directlyProvides
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.schema import Text, Datetime
from zope.schema import TextLine, Int, Password, Bool
from zope.schema.interfaces import ValidationError
from zope.security.proxy import removeSecurityProxy
from zope.traversing.browser import absoluteURL
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.viewlet.viewlet import ViewletBase

from z3c.form import form, field, button, validator
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget
from z3c.form.interfaces import DISPLAY_MODE
from zc.table.column import GetterColumn
from zc.table.interfaces import ISortableColumn

from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.skin.containers import TableContainerView
from schooltool.skin import flourish
from schooltool.skin.flourish.form import Form
from schooltool.table import table
from schooltool.email.interfaces import IEmailContainer, IEmail
from schooltool.email.interfaces import IEmailUtility
from schooltool.email.mail import Email, status_messages

from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


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
    if container.enabled:
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
        required=False)

    enabled = Bool(
        title=_('Enable'),
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
        title=_('Password'),
        description=_('Current password to authenticate to the SMTP server.'),
        required=False)
    
    password = Password(
        title=_('New Password'),
        description=_('The password to authenticate to the SMTP server.'),
        required=False)

    password_confirmation = Password(
        title=_('Confirm New Password'),
        required=False)

    tls = Bool(
        title=_('TLS'),
        description=_('Use TLS connection?'),
        default=False,
        required=False)


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


class FlourishEmailSettingsEditView(Form, form.EditForm):

    label = None
    legend = _('Settings')
    fields = field.Fields(IEmailSettingsEditForm)
    fields = fields.omit('server_status', 'dummy_password')

    def update(self):
        form.EditForm.update(self)

    @button.buttonAndHandler(_('Apply'))
    def handle_apply_action(self, action):
        super(FlourishEmailSettingsEditView,
              self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def updateActions(self):
        super(FlourishEmailSettingsEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class HostnameIsRequired(ValidationError):
    __doc__ = _('Hostname is required for enabling the service')


# XXX: logic very similar to that in 
#      schooltool.person.browser.person
class PasswordsDontMatch(ValidationError):
    __doc__ = _('Supplied new passwords are not identical')


class PasswordsMatchValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the validation error next to the widget!
        name = self.view.widgets['password_confirmation'].name
        verify = self.request.get(name)
        if value is not None and value not in (verify,):
            raise PasswordsDontMatch(value)


class FlourishPasswordsMatchValidator(validator.SimpleFieldValidator):
    pass


validator.WidgetValidatorDiscriminators(PasswordsMatchValidator,
                                        view=EmailSettingsEditView,
                                        field=IEmailSettingsEditForm['password'])


validator.WidgetValidatorDiscriminators(FlourishPasswordsMatchValidator,
                                        view=FlourishEmailSettingsEditView,
                                        field=IEmailSettingsEditForm['password'])


class HostnameValidator(validator.SimpleFieldValidator):

    def validate(self, value):
        # XXX: hack to display the validation error next to the widget!
        name = self.view.widgets['enabled'].name
        enabled = self.request.get(name)
        if enabled and enabled[0] in ('true', 'selected') and not value:
            raise HostnameIsRequired(value)


class FlourishHostnameValidator(HostnameValidator):
    pass


validator.WidgetValidatorDiscriminators(HostnameValidator,
                                        view=EmailSettingsEditView,
                                        field=IEmailSettingsEditForm['hostname'])


validator.WidgetValidatorDiscriminators(FlourishHostnameValidator,
                                        view=FlourishEmailSettingsEditView,
                                        field=IEmailSettingsEditForm['hostname'])


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
        required=False)

    body = Text(
        title=_(u'Body'),
        required=False)

    status = TextLine(
        title=_(u'Email Status'),
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
            status_text = translate(
                format_message(
                    status_messages[self.context.status_code],
                    mapping=self.context.status_parameters),
                context=self.request)
            self.widgets['status'].value = status_text
            self.widgets['status'].style = u'color: red;'


class FlourishEmailView(flourish.page.Page):

    def preferred_datetime_format(self):
        preferences = get_application_preferences()
        return '%s %s' % (preferences.dateformat, preferences.timeformat)

    def update(self):
        attrs = ['from_address', 'to_addresses', 'time_created',
                 'subject', 'body', 'status', 'time_sent']
        self.attrs = []
        datetime_format = self.preferred_datetime_format()
        info_adapter = IEmailDisplayForm(self.context)
        for attr in attrs:
            info = {'label': IEmailDisplayForm[attr].title}
            if attr != 'status':
                value = getattr(info_adapter, attr)
                if attr in ('time_created', 'time_sent'):
                    value = value.strftime(datetime_format)
            else:
                value = None
                if self.context.status_code is not None:
                    value = translate(
                        format_message(
                            status_messages[self.context.status_code],
                            mapping=self.context.status_parameters),
                        context=self.request)
            info['value'] = value
            self.attrs.append(info)

    def nextURL(self):
        return '%s/queue.html' % absoluteURL(self.context.__parent__,
                                             self.request)


class FlourishEmailRetryView(flourish.page.Page):

    def getDeleteURL(self, email):
        params = [('delete.%s' % (email.__name__.encode('utf-8')), ''),
                  ('CONFIRM', 'Confirm')]
        return '%s/%s?%s' % (absoluteURL(email.__parent__, self.request),
                             'queue.html',
                             urllib.urlencode(params),)

    def __call__(self):
        utility = getUtility(IEmailUtility)
        email = removeSecurityProxy(self.context)
        success = utility.send(email)
        if success:
            url = self.getDeleteURL(email)
        else:
            url = '%s/queue.html' % absoluteURL(self.context.__parent__,
                                                self.request)
        self.request.response.redirect(url)


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


class EmailContainerViewTableFormatter(table.SchoolToolTableFormatter):

    columns = lambda self: email_container_table_columns()

    def sortOn(self):
        return (('time_created', True),)


class FlourishEmailContainerViewTableFormatter(
    EmailContainerViewTableFormatter):

    def columns(self):
        from_address = GetterColumn(
            name='from_address',
            title=_(u'From'),
            getter=lambda i, f: i.from_address,
            subsort=True)
        time_created = GetterColumn(
            name='time_created',
            title=_(u'Created on'),
            getter=lambda i, f: i.time_created,
            cell_formatter=datetime_formatter,
            subsort=True)
        time_sent = GetterColumn(
            name='time_sent',
            title=_(u'Last time tried'),
            getter=lambda i, f: i.time_sent,
            cell_formatter=datetime_formatter,
            subsort=True)
        directlyProvides(from_address, ISortableColumn)
        directlyProvides(time_created, ISortableColumn)
        directlyProvides(time_sent, ISortableColumn)
        return [from_address, time_created, time_sent]


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


class FlourishEmailContainerView(flourish.page.Page):

    pass


class FlourishEmailContainerDetails(flourish.form.FormViewlet):

    fields = field.Fields(IEmailSettingsEditForm)
    fields = fields.omit('server_status',
                         'enabled',
                         'password',
                         'password_confirmation')
    template = ViewPageTemplateFile("templates/f_email_container.pt")
    mode = DISPLAY_MODE

    @property
    def status(self):
        if self.context.enabled:
            return _('Enabled')
        else:
            return  _('Disabled')

    def updateWidgets(self):
        super(FlourishEmailContainerDetails, self).updateWidgets()
        if self.context.password:
            mask = '*'*len(self.context.password)
            self.widgets['dummy_password'].value = mask

    def done_link(self):
        app = ISchoolToolApplication(None)
        return '%s/settings' % absoluteURL(app, self.request)


class FlourishEmailQueueView(table.TableContainerView):

    def getColumnsAfter(self):
        action = table.ImageInputColumn(
            'delete', name='action', title=_('Delete'),
            library='schooltool.skin.flourish',
            image='remove-icon.png',
            id_getter=table.simple_form_key)
        return [action]

    def update(self):
        super(FlourishEmailQueueView, self).update()
        # XXX: deletion without confirmation is quite dangerous
        delete = [key for key, item in self.container.items()
                  if "delete.%s" % table.simple_form_key(item) in self.request]
        for key in delete:
            del self.container[key]
        if delete:
            url = absoluteURL(self.context, self.request) + '/queue.html'
            self.request.response.redirect(url)


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
            self.status = self.formErrorsMessage
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


class FlourishSendEmailView(Form, SendEmailView):

    label = None
    legend = _('Email')
    fields = field.Fields(ISendEmailForm).omit('server_status')

    def update(self):
        form.Form.update(self)

    @button.buttonAndHandler(_('Send'))
    def handle_send_action(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        from_address = data['from_address']
        to_addresses = [address.strip()
                        for address in data['to_addresses'].split(',')]
        body = data['body']
        subject = data['subject']
        email = Email(from_address, to_addresses, body, subject)
        utility = getUtility(IEmailUtility)
        success = utility.send(email)
        if success:
            url = absoluteURL(self.context, self.request)
        else:
            url = '%s/queue.html' % absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_('Cancel'))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class EmailActionsLinks(flourish.page.RefineLinksViewlet):
    """Email actions links viewlet."""


class EmailViewActionsLinks(flourish.page.RefineLinksViewlet):
    """Email view actions links viewlet."""

    body_template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/renderable_items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    # We don't want this manager rendered at all
    # if there are no renderable viewlets
    @property
    def renderable_items(self):
        result = []
        for item in self.items:
            render_result = item['viewlet']()
            if render_result and render_result.strip():
                result.append({
                        'class': item['class'],
                        'viewlet': render_result,
                        })
        return result

    def render(self):
        if self.renderable_items:
            return super(EmailViewActionsLinks, self).render()


class RetryLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        return self.context.__parent__.enabled


class SendTestLinkViewlet(flourish.page.LinkViewlet):

    @property
    def enabled(self):
        return self.context.enabled


class EmailQueueLinkViewlet(flourish.page.LinkViewlet):

    @property
    def title(self):
        count = len(self.context)
        if count:
            return _('Email Queue (${count})', mapping={'count': count})
        else:
            return _('Email Queue')


class FlourishEmailSettingsOverview(flourish.form.FormViewlet):

    fields = field.Fields(IEmailSettingsEditForm)
    fields = fields.select('server_status', 'hostname')
    template = ViewPageTemplateFile(
        'templates/f_email_settings_overview.pt')
    mode = DISPLAY_MODE

    def getContent(self):
        return IEmailContainer(self.context)

    def updateWidgets(self):
        super(FlourishEmailSettingsOverview, self).updateWidgets()
        email_container = self.getContent()
        status = email_container.enabled and _('Enabled') or _('Disabled')
        self.widgets['server_status'].value = status
