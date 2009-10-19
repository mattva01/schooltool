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
Unit tests for email functionality.

"""
import unittest
from zope.testing import doctest

from schooltool.schoolyear.testing import setUp, tearDown
from schooltool.email.ftesting import email_functional_layer


def doctest_EmailContainer(self):
    """Tests for toplevel container for Emails.

        >>> from zope.interface.verify import verifyObject
        >>> from schooltool.email.interfaces import IEmailContainer
        >>> from schooltool.email.mail import EmailContainer
        >>> container = EmailContainer()
        >>> verifyObject(IEmailContainer, container)
        True

    It should only be able to contain emails:

        >>> from zope.app.container.constraints import checkObject
        >>> from schooltool.email.mail import Email
        >>> from schooltool.course.section import Section
        >>> myemail = Email('sender@example.com', ['user@example.com',],
        ...                 'Hello')
        >>> checkObject(container, 'email', myemail)
        >>> checkObject(container, 'section', Section())
        Traceback (most recent call last):
          ...
        InvalidItemType: ...

    Its attributes:

        >>> container.hostname
        >>> container.port
        >>> container.username
        >>> container.password
        >>> container.tls

    """

def doctest_Email(self):
    """Tests for Emails.

        >>> from zope.interface.verify import verifyObject
        >>> from schooltool.email.interfaces import IEmail
        >>> from schooltool.email.interfaces import IEmailContained
        >>> from schooltool.email.mail import Email
        >>> myemail = Email('sender@example.com', ['user@example.com',],
        ...                 'Hello', 'Hi, how are you?')
        >>> verifyObject(IEmail, myemail)
        True
        >>> verifyObject(IEmailContained, myemail)
        True

    Emails should only be contained in EmailContainers:

        >>> from zope.app.container.constraints import checkObject
        >>> from schooltool.email.mail import EmailContainer
        >>> real_container = EmailContainer()
        >>> fake_container = {}
        >>> checkObject(real_container, 'email', myemail)
        >>> checkObject(fake_container, 'email', myemail)
        Traceback (most recent call last):
          ...
        InvalidContainerType: ...

    Its attributes:

        >>> myemail.from_address
        'sender@example.com'

        >>> myemail.to_addresses
        ['user@example.com']

        >>> myemail.body
        'Hello'

        >>> myemail.subject
        'Hi, how are you?'

        >>> myemail.status_code

        >>> myemail.status_parameters
        <persistent.dict.PersistentDict object at ...>

        >>> myemail.time_created
        datetime.datetime(..., tzinfo=<UTC>)

        >>> myemail.time_sent

    """


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    suite.layer = email_functional_layer
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
