#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2006 Shuttleworth Foundation
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
SchoolTool security policy metadirectives.

$Id$

"""

from zope.interface import Interface
from zope import schema
from zope.configuration import fields
from zope.security.zcml import Permission


CrowdId = fields.PythonIdentifier
DescGroupId = fields.PythonIdentifier
DescActionId = fields.PythonIdentifier


class ICrowdDirective(Interface):

    name = CrowdId(
        title=u"Name",
        description=u"Identifier of the crowd")

    factory = fields.GlobalObject(
        title=u"Factory",
        description=u"The factory for the crowd")


class IAllowDirective(Interface):

    interface = fields.GlobalObject(
        title=u"Interface",
        required=False,
        description=u"An interface of the object")

    crowds = fields.Tokens(
        title=u"Crowds",
        value_type=CrowdId(title=u"Crowd"),
        required=True)

    permission = Permission(
        title=u"Permission",
        required=True)


class ISettingDirective(Interface):

    key = fields.PythonIdentifier(
        title=u"Key")

    text = fields.MessageID(
        title=u"Text")

    default = fields.Bool(
        title=u"Default setting",
        required=True,
        default=False)


class IAggregateCrowdDirective(Interface):

    name = CrowdId(
        title=u"Name",
        description=u"Identifier of the crowd")

    crowds = fields.Tokens(
        title=u"Crowds",
        value_type=CrowdId(title=u"Crowd"),
        required=True)


class IDescribeGroup(Interface):

    name = DescGroupId(
        title=u"Name",
        description=u"Identifier of the user-level access group")

    title = fields.MessageID(
        title=u"Title",
        required=False)

    description = fields.MessageID(
        title=u"Description",
        required=False)

    klass = fields.GlobalObject(
        title=u"Implementation of the group description",
        required=False)


class IDescribeAction(Interface):

    group = DescGroupId(
        title=u"Name",
        description=u"Identifier of the user-level access group")

    name = DescActionId(
        title=u"Name",
        description=u"Identifier of the action")

    order = schema.Int(
        title=u"Order",
        required=False)

    interface = fields.GlobalObject(
        title=u"Interface",
        required=True,
        description=u"An interface of the object")

    permission = Permission(
        title=u"Permission",
        required=True)

    title = fields.MessageID(
        title=u"Title",
        required=False)

    description = fields.MessageID(
        title=u"Description",
        required=False)

    klass = fields.GlobalObject(
        title=u"Implementation of the action description",
        required=False)


class IDescribeCrowd(Interface):

    group = DescGroupId(
        title=u"Group",
        description=u"Optional identifier of the user-level access group",
        required=False)

    action = DescActionId(
        title=u"Action",
        description=u"Optional identifier of the action",
        required=False)

    crowd = CrowdId(
        title=u"Crowd",
        description=u"Identifier of the crowd",
        required=False)

    crowd_factory = fields.GlobalObject(
        title=u"Crowd factory",
        description=u"Alternative way to specify the crowd",
        required=False)

    factory = fields.GlobalObject(
        title=u"Description class",
        required=False)

    title = fields.MessageID(
        title=u"Title",
        required=False)

    description = fields.MessageID(
        title=u"Description",
        required=False)


class IParentCrowd(Interface):

    provides = fields.GlobalObject(
        title=u"Parent crowd interface",
        required=True)

    for_ = fields.GlobalObject(
        title=u"Object parent's interface",
        required=True)

    permission = Permission(
        title=u"Permission",
        required=True)

    factory = fields.GlobalObject(
        title=u"Factory",
        description=u"The factory for the crowd",
        required=True)


class ISwitchDescription(Interface):

    group = DescGroupId(
        title=u"Group",
        description=u"Optional identifier of the user-level access group",
        required=False)

    action = DescActionId(
        title=u"Action",
        description=u"Optional identifier of the action",
        required=False)

    crowd = CrowdId(
        title=u"Crowd to replace",
        description=u"Identifier of the crowd to replace",
        required=False)

    crowd_factory = fields.GlobalObject(
        title=u"Crowd to replace factory",
        description=u"Alternative way to specify the crowd",
        required=False)

    use_crowd = CrowdId(
        title=u"Crowd",
        description=u"Identifier of the crowd to use for description",
        required=False)

    use_crowd_factory = fields.GlobalObject(
        title=u"Crowd factory",
        description=u"Alternative way to specify the other crowd",
        required=False)


