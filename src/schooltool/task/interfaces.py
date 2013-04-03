#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
Group interfaces
"""

from zope.interface import Interface, Attribute
import zope.schema
from zope.container.interfaces import IContainer, IContained
from zope.container.constraints import contains, containers

from schooltool.person.interfaces import IPerson
from schooltool.common import SchoolToolMessage as _


class ITask(Interface):

    task_id = zope.schema.TextLine(title=_("Task ID"))

    routing_key = zope.schema.TextLine(title=_("Celery routing key"),
                                       required=False)

    working = zope.schema.Bool(title=_("Working"))
    finished = zope.schema.Bool(title=_("Finished"))
    succeeded = zope.schema.Bool(title=_("Succeeded"))
    failed = zope.schema.Bool(title=_("Failed"))
    internal_state = zope.schema.TextLine(title=_("Internal state"))

    scheduled = zope.schema.Datetime(title=_("Time Scheduled"))

    creator_username = zope.schema.TextLine(
        title=_("Creator username"),
        required=False)

    creator = zope.schema.Object(
        title=_("Creator"),
        schema=IPerson, required=False)

    def execute(request):
        """Called remotely."""

    def complete(request, result):
        """Called remotely."""

    def fail(request, result, traceback):
        """Called remotely."""


class IRemoteTask(ITask, IContained):
    pass


class ITaskContainer(IContainer):
    contains(IRemoteTask)


class IMessageBase(Interface):

    sender = zope.schema.Object(
        title=u"Sender",
        schema=Interface,
        required=False)

    sender_id = zope.schema.Int(
        title=u"Sender int id",
        description=u"Int ID of the sender",
        required=False)

    recipients = zope.schema.Set(
        title=u"Recipients",
        description=u"Recipient users or other objects",
        value_type=zope.schema.Object(title=u"Recipient", schema=Interface),
        required=False)

    recipient_ids = zope.schema.Set(
        title=u"Recipient int ids",
        description=u"Int IDs of recipient users or other objects",
        value_type=zope.schema.Int(title=u"Recipient"),
        required=False)

    created_on = zope.schema.Datetime(
       title=_("Created on"),
       required=False)

    updated_on = zope.schema.Datetime(
       title=_("Updated on"),
       required=False)

    expires_on = zope.schema.Datetime(title=_("Expires on"))

    title = zope.schema.TextLine(title=u"Title")

    group = zope.schema.TextLine(title=u"Message group")

    #is_read = zope.schema.Bool(
    #    title=u"Read",
    #    description=u"Message has been read",
    #    )


class IMessage(IMessageBase, IContained):
    pass


class IMessageContainer(IContainer):
    contains(IMessage)


class ITaskNotification(Interface):

    task = zope.schema.Object(
        title=u"Remote task",
        schema=IRemoteTask,
        required=False)

    request = Attribute('Request')

    def send(*args, **kw):
        """Send out the messages."""


class ITaskScheduledNotification(ITaskNotification):
    pass


class ITaskFailedNotification(ITaskNotification):

    traceback = Attribute('Task traceback')
    result = Attribute('Task result')


class ITaskCompletedNotification(ITaskNotification):

    result = Attribute('Task result')
