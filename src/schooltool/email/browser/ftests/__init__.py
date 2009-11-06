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

from schooltool.email.mail import EmailUtility


class StubEmailUtility(EmailUtility):
    """Stub implementation of the IEmailUtility.

    """

    def send(self, email):
        self.container = self.getEmailContainer()
        if not self.enabled():
            self.queue(email, 10)
            return False
        server_info = '%s:%d' % (self.container.hostname,
                                 self.container.port or 25)

        # It fakes an invalid port connection
        if email.from_address == 'disabled@example.com' and \
           self.container.port == 255:
            self.queue(email, 20, {'info': server_info})
            return False

        # It fakes an invalid from address
        if email.from_address == 'user@@example.com':
            self.queue(email, 50, {'info': server_info,
                                   'from_address': 'user@@example.com'})
            return False

        # It fakes an invalid to address
        if 'user@@@example.com' in email.to_addresses:
            self.queue(email, 60, {'info': server_info,
                                   'addresses': 'user@@@example.com'})
            return False

        # It fakes some valid and invalid recipient
        # The valid ones are delivered and removed from the queue
        if email.to_addresses == ['othervaliduser@example.com',
                                  'foo@example.com', 'bar@example.com']:
            email.to_addresses = ['foo@example.com', 'bar@example.com']
            self.queue(email, 60,
                       {'info': server_info,
                        'addresses': 'foo@example.com, bar@example.com'})
            return False

        # It fakes a bad username for login
        if self.container.username == 'wronguser':
            self.queue(email, 40, {'info': server_info,
                                   'username': self.container.username})
            return False

        # It fakes a fixing for the bad username above
        if self.container.username == 'rightuser':
            return True

        # By default it fails with a connection error
        self.queue(email, 20, {'info': server_info})
        return False
