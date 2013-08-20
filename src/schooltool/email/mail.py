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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Email functionality

"""

import email.Charset
from email.MIMEText import MIMEText
from datetime import datetime
import pytz
import smtplib
import socket

from persistent import Persistent
from persistent.dict import PersistentDict
from zope.container.btree import BTreeContainer
from zope.container.contained import Contained
from zope.container.interfaces import INameChooser
from zope.component import adapter
from zope.interface import implements, implementer

from schooltool.app.app import InitBase, StartUpBase
from schooltool.app.interfaces import IApplicationPreferences
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common import SchoolToolMessage as _
from schooltool.email.interfaces import IEmailContained, IEmailContainer
from schooltool.email.interfaces import IEmailUtility


email.Charset.add_charset('utf-8', email.Charset.SHORTEST, None, None)
EMAIL_KEY = 'schooltool.email'


status_messages = {
    10: _('The SchoolTool mail service is disabled'),
    20: _("Couldn't connect to the SMTP server (${info})"),
    30: _('Error sending HELO to the SMTP server (${info})'),
    40: _("Couldn't login as ($username) to SMTP server (${info})"),
    50: _('The server (${info}) rejected the From address: ${from_address}'),
    60: _('The server (${info}) rejected the following recipient addresses: '
          '${addresses}'),
    70: _('The server (${info}) replied that the message data was malformed'),
    }


class Email(Persistent, Contained):

    implements(IEmailContained)

    def __init__(self, from_address, to_addresses, body, subject=None):
        self.from_address = from_address
        self.to_addresses = to_addresses
        self.body = body
        self.subject = subject
        self.status_code = None
        self.status_parameters = PersistentDict()
        self.time_created = pytz.utc.localize(datetime.utcnow())
        self.time_sent = None


class EmailContainer(BTreeContainer):

    implements(IEmailContainer)

    enabled = None
    hostname = None
    port = None
    username = None
    password = None
    tls = None


class EmailAppStartup(StartUpBase):

    def __call__(self):
        if EMAIL_KEY not in self.app:
            self.app[EMAIL_KEY] = EmailContainer()


class EmailInit(InitBase):

    def __call__(self):
        self.app[EMAIL_KEY] = EmailContainer()


@implementer(IEmailContainer)
@adapter(ISchoolToolApplication)
def getEmailContainer(app):
    return app.get(EMAIL_KEY)


class EmailUtility(object):

    implements(IEmailUtility)

    smtp_factory = None

    def getEmailContainer(self):
        app = ISchoolToolApplication(None)
        return IEmailContainer(app)

    def getApplicationTimezone(self):
        app = ISchoolToolApplication(None)
        return pytz.timezone(IApplicationPreferences(app).timezone)

    def emailAsString(self, email):
        message = MIMEText(email.body.encode('utf-8'), 'plain', 'utf-8')
        message['From'] = email.from_address.encode('utf-8')
        message['To'] = ', '.join([address.encode('utf-8')
                                   for address in email.to_addresses])
        if email.subject is not None:
            message['Subject'] = email.subject.encode('utf-8')
        time_format = '%a, %d %b %Y %H:%M:%S %z'
        application_timezone = self.getApplicationTimezone()
        time_created = email.time_created.astimezone(application_timezone)
        message['Date'] = time_created.strftime(time_format).encode('utf-8')
        return message.as_string()

    def queue(self, email, status_code=None, status_parameters={}):
        email.status_code = status_code
        email.status_parameters.update(status_parameters)
        email.time_sent = pytz.utc.localize(datetime.utcnow())
        if email.__parent__ is not self.container:
            name = INameChooser(self.container).chooseName('', email)
            self.container[name] = email

    def enabled(self):
        if self.smtp_factory is None:
            return False
        container = self.getEmailContainer()
        return container.enabled

    def send(self, email):
        self.container = self.getEmailContainer()
        if not self.enabled():
            self.queue(email, 10)
            return False
        server_info = '%s:%d' % (self.container.hostname,
                                 self.container.port or 25)
        try:
            connection = self.smtp_factory()
            if self.container.port:
                port = str(self.container.port)
            else:
                port = '25'
            connection.connect(self.container.hostname, port)
            code, response = connection.ehlo()
            if code < 200 or code >= 300:
                code, response = connection.helo()
                if code < 200 or code >= 300:
                    raise smtplib.SMTPHeloError(code, response)
            if connection.has_extn('starttls') and self.container.tls:
                connection.starttls()
                connection.ehlo()
            if connection.does_esmtp:
                if self.container.username is not None and \
                   self.container.password is not None:
                    connection.login(self.container.username,
                                     self.container.password)
        except (socket.error,), e:
            self.queue(email, 20, {'info': server_info})
            return False
        except (smtplib.SMTPHeloError,), e:
            self.queue(email, 30, {'info': server_info})
            connection.quit()
            return False
        except (smtplib.SMTPException,), e:
            self.queue(email, 40, {'info': server_info,
                                   'username': self.container.username})
            connection.quit()
            return False
        message = self.emailAsString(email)
        result = {}
        try:
            result = connection.sendmail(email.from_address,
                                         email.to_addresses,
                                         message)
        except (smtplib.SMTPSenderRefused,), e:
            self.queue(email, 50, {'info': server_info,
                                   'from_address': e.sender})
            connection.quit()
            return False
        except (smtplib.SMTPRecipientsRefused,), e:
            addresses = e.recipients.keys()
            self.queue(email, 60, {'info': server_info,
                                   'addresses': ', '.join(addresses)})
            connection.quit()
            return False
        except (smtplib.SMTPHeloError,), e:
            self.queue(email, 30, {'info': server_info})
            connection.quit()
            return False
        except (smtplib.SMTPDataError,), e:
            self.queue(email, 70, {'info': server_info})
            connection.quit()
            return False
        if result:
            addresses = [address for address in email.to_addresses
                         if address in result.keys()]
            email.to_addresses = addresses[:]
            self.queue(email, 60, {'info': server_info,
                                   'addresses': ', '.join(addresses)})
            connection.quit()
            return False
        connection.quit()
        return True


class SMTPEmailUtility(EmailUtility):

    smtp_factory = smtplib.SMTP
