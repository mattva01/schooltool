#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
SchoolTool flourish skin common helpers.
"""
import urllib

import zope.security
import zope.container.interfaces


class Empty(object):

    __name__ = None
    __parent__ = None

    def __init__(self, context, request, *args, **kw):
        self.__parent__ = context
        self.context = context
        self.request = request

    def update(self):
        pass

    def render(self, *args, **kw):
        return ''

    def __call__(self, *args, **kw):
        return ''


class EmptyContent(Empty):

    def __init__(self, context, request, view, **kw):
        Empty.__init__(self, context, request, **kw)
        self.__parent__ = view
        self.view = view


class EmptyViewlet(EmptyContent):

    def __init__(self, context, request, view, manager, **kw):
        EmptyContent.__init__(self, context, request, view, **kw)
        self.__parent__ = manager
        self.manager = manager


def canView(context):
    return zope.security.checkPermission('schooltool.view', context)


def canEdit(context):
    return zope.security.checkPermission('schooltool.edit', context)


def canDelete(context):
    container = context.__parent__
    if not zope.container.interfaces.IWriteContainer.providedBy(container):
        raise NotImplementedError()
    # XXX: if context has dependents, deletion may be prevented
    return zope.security.canAccess(container, '__delitem__')


def hasPermission(context, permission):
    return zope.security.checkPermission(permission, context)


def quoteFilename(filename):
    if not filename:
        return filename
    if type(filename) is unicode:
        encoded = filename.encode('UTF-8')
    else:
        encoded = str(filename)
    return urllib.quote(encoded)
