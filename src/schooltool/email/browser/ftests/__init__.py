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
Functional tests for schooltool.email

"""
import smtplib
import socket

from schooltool.email.mail import EmailUtility


class StubConnection(object):

    reject_mail_to = 'reject.com'

    host = None
    port = None

    def connect(self, host, port):
        self.host, self.port = host, port
        if port == '255':
            raise socket.error('StubConnection failed successfuly')

    def ehlo(self):
        return 200, 'okay'

    def helo(self):
        return 200, 'okay'

    def has_extn(self, extention):
        return True

    @property
    def does_esmtp(self):
        return True

    def login(self, username, password):
        if self.host == 'fail_login':
            raise smtplib.SMTPException('Purposefully failed to log in')

    def quit(self):
        pass

    def sendmail(self, from_address, to_addresses, message):
        if self.reject_mail_to in from_address:
            raise smtplib.SMTPSenderRefused(
                -1, 'Failed successfuly', from_address)
        rejected_recipients = dict([
            (addr, 'Fail') for addr in to_addresses
            if self.reject_mail_to in addr])
        if rejected_recipients:
            if len(rejected_recipients) == to_addresses:
                raise smtplib.SMTPRecipientsRefused(rejected_recipients)
            else:
                return rejected_recipients
        if self.host == 'reject_malformed':
            raise smtplib.SMTPDataError(-1, 'I pretend that this is bad data')


class SentMessages(list):
    """This is basically a list of email messages with a helper to
    ease writing of functional tests.
    """

    def print_mail(self, emails=None):
        """Pass an email or list of emails to print.
        Alternatively don't pass anything to print them all.
        """
        if emails is None:
            emails = self
        elif not hasattr(emails, '__iter__'):
            emails = [emails]

        for email in emails:
            headers = [
                'From: %s' % email.from_address,
                'To: %s' % ', '.join(email.to_addresses),
                'Subject: %s' % email.subject]
            maxlen = max(
                [len(s) for s in headers + email.body.split('\n')])
            print '\n'.join(
                ['=' * maxlen] +
                headers +
                ['-' * maxlen,
                 '%s' % email.body]
                )


class StubEmailUtility(EmailUtility):
    """Implementation of IEmailUtility that fails in variety of ways depending
    on the contents of email being sent and logs the messages that are
    successfuly sent.
    """

    smtp_factory = StubConnection

    def __init__(self, *args, **kw):
        super(StubEmailUtility, self).__init__(*args, **kw)
        self.sent = SentMessages()

    def send(self, email):
        result = EmailUtility.send(self, email)
        if result:
            self.sent.append(email)
        return result
