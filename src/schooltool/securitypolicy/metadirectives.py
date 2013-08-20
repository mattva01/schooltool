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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool security policy metadirectives.

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
        title=u"Text that describes the setting")

    alt_text = fields.MessageID(
        title=u"Text that describes 'setting=False'",
        required=False)

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
        description=u"Unique identifier of the group.")

    title = fields.MessageID(
        title=u"Title",
        description=u"Group title displayed to the user.",
        required=False)

    description = fields.MessageID(
        title=u"Description",
        description=u"Group description displayed to the user.",
        required=False)

    klass = fields.GlobalObject(
        title=u"Class",
        description=u"""
        Group definition class that builds it's own title/description.
        This is an alternative to title/description defined in ZCML.
        """,
        required=False)


class IDescribeAction(Interface):

    group = DescGroupId(
        title=u"Group name",
        description=u"Identifier of the group this action belongs to.")

    name = DescActionId(
        title=u"Name",
        description=u"Unique identifier of the action within the group.")

    order = schema.Int(
        title=u"Order",
        description=u"Order in which this action should be displayed.",
        required=False)

    interface = fields.GlobalObject(
        title=u"Interface",
        required=True)

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
        title=u"Class",
        description=u"""
        Action definition class that builds it's own title/description.
        This is an alternative to title/description defined in ZCML.
        """,
        required=False)


class IDescribeCrowd(Interface):

    group = DescGroupId(
        title=u"Group",
        description=u"""
        Optional identifier of the group.  When specified, this description applies
        to the group only.
        """,
        required=False)

    action = DescActionId(
        title=u"Action",
        description=u"""
        Optional identifier of the action of the group.  If specified, this description
        applies to the action only.
        """,
        required=False)

    crowd = CrowdId(
        title=u"Crowd",
        description=u"Identifier of the crowd.",
        required=False)

    crowd_factory = fields.GlobalObject(
        title=u"Crowd factory",
        description=u"Alternative way to specify the crowd.",
        required=False)

    factory = fields.GlobalObject(
        title=u"Description class",
        description=u"Optional class that to build the title/description.",
        required=False)

    title = fields.MessageID(
        title=u"Title",
        description=u"""
        A quick way to specify the title from ZCML.
        It will be assigned to the "factory" instance dict.
        """,
        required=False)

    description = fields.MessageID(
        title=u"Description",
        description=u"""
        A quick way to specify the description from ZCML.
        It will be assigned to the "factory" instance dict.
        """,
        required=False)


class ISwitchDescription(Interface):
    """Directive to use a replacement crowd when looking up descriptions of
    a crowd.  May be used to use the replacement for a specific group or action.
    """

    group = DescGroupId(
        title=u"Group",
        description=u"""
        Optional identifier of the group.  When specified,
        the description will be switched within this group only.
        """,
        required=False)

    action = DescActionId(
        title=u"Action",
        description=u"""
        Optional identifier of the action of the group.
        When specified, the description will be switched for
        this action of the group only.
        """,
        required=False)

    crowd = CrowdId(
        title=u"Crowd to replace",
        description=u"Identifier of the crowd to replace.",
        required=False)

    crowd_factory = fields.GlobalObject(
        title=u"Crowd to replace factory",
        description=u"Alternative way to specify the crowd to replace.",
        required=False)

    use_crowd = CrowdId(
        title=u"Crowd",
        description=u"Identifier of the crowd to use for description.",
        required=False)

    use_crowd_factory = fields.GlobalObject(
        title=u"Crowd factory",
        description=u"Alternative way to specify the description crowd",
        required=False)


