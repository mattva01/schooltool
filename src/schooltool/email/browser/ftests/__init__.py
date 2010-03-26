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
Functional tests for schooltool.email

"""
import smtplib
import socket

from schooltool.email.mail import EmailUtility


class StubConnection(object):

    reject_addresses = [
        'user@@example.com',
        'user@@@example.com',
        'foo@@example.com',
        'bar@@example.com',
        ]

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
        if from_address in self.reject_addresses:
            raise smtplib.SMTPSenderRefused(
                -1, 'Failed successfuly', from_address)
        rejected_recipients = dict([(addr, 'Fail') for addr in to_addresses
                                    if addr in self.reject_addresses])
        if rejected_recipients:
            if len(rejected_recipients) == to_addresses:
                raise smtplib.SMTPRecipientsRefused(rejected_recipients)
            else:
                return rejected_recipients
        if self.host == 'reject_malformed':
            raise smtplib.SMTPDataError(-1, 'I pretend that this is bad data')


class SentMessages(list):

    def _print_email(self, email):
        s_from = 'From: %s' % email.from_address
        s_to = 'To: %s' % ', '.join(email.to_addresses)
        maxlen = max(
            [len(s) for s in [s_from, s_to] + email.body.split('\n')])
        print '\n'.join([
            s_from,
            s_to,
            '=' * maxlen,
            '%s' % email.body,
            '-' * maxlen,
            '',
            ])

    def print_message(self, index):
        email = self[index]
        self._print_email(email)

    def print_messages(self, last=None):
        """Specify amount of last messages to print, None for all."""
        if last is None:
            last = len(self)
        for email in self[len(self)-last:]:
            self._print_email(email)


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
