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
Unit tests for email functionality.

"""
import unittest
import doctest

from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.component import provideAdapter
from zope.container.contained import NameChooser
from zope.app.testing import setup

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.email.interfaces import IEmailContainer


def doctest_EmailContainer(self):
    """Tests for toplevel container for Emails.

        >>> from zope.interface.verify import verifyObject
        >>> from schooltool.email.mail import EmailContainer
        >>> container = EmailContainer()
        >>> verifyObject(IEmailContainer, container)
        True

    It should only be able to contain emails:

        >>> from zope.container.constraints import checkObject
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

        >>> from zope.container.constraints import checkObject
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
        {}

        >>> type(myemail.status_parameters)
        <class 'persistent.mapping.PersistentMapping'>

        >>> myemail.time_created
        datetime.datetime(..., tzinfo=<UTC>)

        >>> myemail.time_sent

    """


def doctest_EmailUtility():
    """Tests for EmailUtility.

        >>> class EmailContainerStub(dict):
        ...     implements(IEmailContainer)
        ...     enabled = False
        >>> email_container = EmailContainerStub()

        >>> provideAdapter(lambda app: app.emails,
        ...                adapts=(ISchoolToolApplication, ),
        ...                provides=IEmailContainer)

        >>> from schooltool.app.interfaces import IApplicationPreferences

        >>> class AppStub(object):
        ...     implements(ISchoolToolApplication, IApplicationPreferences)
        ...     def __init__(self):
        ...         self.emails = EmailContainerStub()
        ...         self.timezone = 'UTC'
        >>> app = AppStub()
        >>> provideAdapter(lambda ignored: app,
        ...                adapts=(None, ), provides=ISchoolToolApplication)


    EmailUtility is basically a wrapper around python's smtp library.

        >>> from schooltool.email.interfaces import IEmailUtility
        >>> from schooltool.email.mail import EmailUtility

        >>> util = EmailUtility()
        >>> verifyObject(IEmailUtility, util)
        True

    It's enabled when smtp_factory is specified and email container is
    enabled.

        >>> print util.smtp_factory
        None

        >>> util.smtp_factory = 'python SMTP lib'
        >>> app.emails.enabled = False

        >>> util.enabled()
        False

        >>> app.emails.enabled = True
        >>> util.enabled()
        True

        >>> util.smtp_factory = None
        >>> util.enabled()
        False

    When the utility is disabled, emails are put to the email container instead
    of being sent.

        >>> from schooltool.email.mail import Email

        >>> mail = Email('from@test',
        ...              ['to1@test', 'to2@test'], 'World', subject='Hello')

        >>> util.send(mail)
        False

        >>> app.emails
        {u'Email': <schooltool.email.mail.Email object at ...>}

        >>> print util.emailAsString(app.emails['Email'])
        Content-Type: text/plain; charset="utf-8"
        MIME-Version: 1.0
        Content-Transfer-Encoding: 7bit
        From: from@test
        To: to1@test, to2@test
        Subject: Hello
        Date: ...
        <BLANKLINE>
        World

    Putting into the email container is done via util.queue.

        >>> util.queue(mail, status_code=15, status_parameters={'foo': 1})
        >>> sorted(app.emails)
        [u'Email', u'Email-2']

    Bad mail get's status code assigned, sometimes with paramteres.

        >>> bad_mail = app.emails[u'Email-2']
        >>> bad_mail.status_code
        15

        >>> bad_mail.status_parameters
        {'foo': 1}

    Care is taken so that passed status parameters are persistent.

        >>> type(bad_mail.status_parameters)
        <class 'persistent.mapping.PersistentMapping'>

    And here is the real-life implementation of the email utility.

        >>> from schooltool.email.mail import SMTPEmailUtility
        >>> util = SMTPEmailUtility()

        >>> verifyObject(IEmailUtility, util)
        True

        >>> util.smtp_factory
        <class smtplib.SMTP at ...>

        >>> app.emails.enabled = True

        >>> util.enabled()
        True

    """


def setUp(test=None):
    setup.placefulSetUp()
    provideAdapter(NameChooser, adapts=(IEmailContainer, ))


def tearDown(test=None):
    setup.placefulTearDown()


def test_suite():
    optionflags = (doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS |
                   doctest.REPORT_ONLY_FIRST_FAILURE)
    suite = doctest.DocTestSuite(optionflags=optionflags,
                                 setUp=setUp, tearDown=tearDown)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
