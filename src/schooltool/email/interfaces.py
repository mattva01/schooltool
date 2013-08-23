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
Email interfaces

"""

from zope.container.constraints import contains, containers
from zope.location.interfaces import IContained
from zope.container.interfaces import IReadContainer, IWriteContainer
from zope.interface import Interface
from zope.location.interfaces import ILocation
from zope.schema import Bool, Datetime, Dict
from zope.schema import TextLine, List, Text, Int, Password

from schooltool.common import SchoolToolMessage as _


class IEmail(Interface):
    """An email"""

    from_address = TextLine(
        title=_(u'From'),
        description=_(u'The sender address'))

    to_addresses = List(
        title=_(u'To'),
        description=_(u'Recipient addresses'),
        value_type=TextLine(title=_(u'Recipient address')),
        min_length=1)

    body = Text(
        title=_(u'Body'),
        description=_(u'Body of the message'))

    subject = TextLine(
        title=_(u'Subject'),
        description=_(u'Subject of the message'),
        required=False)

    status_code = TextLine(
        title=_(u'Status'),
        description=_(u'Code for the status of the message'),
        required=False)

    status_parameters = Dict(
        title=_(u'Status Parameters'),
        description=_(u'Parameters for the status of the message'),
        key_type=TextLine(title=_(u'Parameter key')),
        value_type=TextLine(title=_(u'Parameter value')),
        required=False)

    time_created = Datetime(
        title=_(u'Created on'),
        description=_(u'Date and time when the message was created'))

    time_sent = Datetime(
        title=_(u'Sent on'),
        description=_(u'Date and time when the message was sent'),
        required=False)


class IWriteEmailContainer(IWriteContainer):
    """Write interface for the IEmailContainer"""


class IReadEmailContainer(IReadContainer, ILocation):
    """Read interface for the IEmailContainer"""

    enabled = Bool(
        title=_('Enable'),
        description=_('Mark to enable the service.'),
        default=False)

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

    password = Password(
        title=_('New Password'),
        description=_('The password to authenticate to the SMTP server.'),
        required=False)

    tls = Bool(
        title=_('TLS'),
        description=_('Use TLS connection?'),
        default=False,
        required=False)


class IEmailContainer(IWriteEmailContainer, IReadEmailContainer):
    """A container for IEmail objects"""

    contains(IEmail)


class IEmailContained(IEmail, IContained):
    """An IEmail object that is contained in a IEmailContainer"""

    containers(IEmailContainer)


class IEmailUtility(Interface):
    """An utility to send IEmail objects"""

    def send(email):
        """Sends an email message.

        `email` is a IEmail object.

        Returns True if the email is sent successfully to all its
        recipients. False otherwise.

        If this method returns False, the `email` object is added to
        the IEmailContainer if it is not there.

        """

    def enabled():
        """Checks if the email service is enabled.

        Returns True if the service is enabled. False otherwise.

        """
