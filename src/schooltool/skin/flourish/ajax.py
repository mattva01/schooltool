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
Schooltool page AJAX parts.
"""
import zope.contentprovider.interfaces
import zope.event
from zope.component import adapts
from zope.interface import implements
from zope.location.interfaces import LocationError
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.traversing.api import traverseName
from zope.traversing.interfaces import ITraversable

from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish import tal
from schooltool.skin.flourish import form
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManagerBase
from schooltool.skin.flourish.viewlet import ManagerViewlet


class AJAXPart(Viewlet):
    implements(interfaces.IAJAXPart, IBrowserPublisher)

    fromPublication = False

    @property
    def ignoreRequest(self):
        return not self.fromPublication

    def browserDefault(self, request):
        self.fromPublication = True
        return self, ()

    def publishTraverse(self, request, name):
        raise NotFound(self, name, request)

    def setJSONResponse(self, data):
        """
        Switch response to JSON.  Return encoded payload.
        Resets the original response. Yes, I know, this method is evil.
        Sorry.
        """
        response = self.request.response

        # Bye bye birdie.
        response.reset()

        response.setHeader('Content-Type', 'application/json')
        encoder = tal.JSONEncoder()
        json = encoder.encode(data)
        return json


class CompositeAJAXPart(ManagerViewlet, AJAXPart):
    implements(interfaces.IAJAXPart, IBrowserPublisher)

    def publishTraverse(self, request, name):
        part = self.get(name)
        if part is None:
            raise NotFound(self, name, request)
        return part


class AJAXParts(ViewletManagerBase):
    implements(interfaces.IAJAXParts)

    def render(self, *args, **kw):
        raise NotFound(self.__parent__, self.__name__, self.request)

    def publishTraverse(self, request, name):
        try:
            part = traverseName(self, name)
        except LocationError:
            raise NotFound(self, name, self.request)
        return part


class AJAXPartsTraversable(object):
    adapts(AJAXParts)
    implements(ITraversable)

    def __init__(self, parts):
        self.parts = parts

    def traverse(self, name, furtherPath):
        __traceback_info__ = (self.parts, name, furtherPath)
        try:
            return self.parts[name]
        except (KeyError, TypeError):
            raise LocationError(self.parts, name)


class SubContextParts(CompositeAJAXPart, AJAXParts):

    render = AJAXParts.render
    publishTraverse = AJAXParts.publishTraverse


class ViewContextParts(SubContextParts):

    def __init__(self, context, request, view, manager):
        SubContextParts.__init__(self, view, request, view, manager)


class ContextTraversable(object):
    adapts(SubContextParts)
    implements(ITraversable)

    def __init__(self, parts):
        self.parts = parts

    def traverse(self, name, furtherPath):
        __traceback_info__ = (self.parts, name, furtherPath)
        try:
            return self.parts[name]
        except (KeyError, TypeError):
            pass

        try:
            next = traverseName(self.parts.context, name)
        except LocationError:
            raise

        parts = SubContextParts(
            next, self.parts.request, self.parts.view, self.parts)
        parts.__name__ = name
        return parts


class AJAXDialog(form.Dialog, AJAXPart):

    def update(self):
        AJAXPart.update(self)
        form.Dialog.update(self)

    def __call__(self, *args, **kw):
        if not self._updated:
            event = zope.contentprovider.interfaces.BeforeUpdateEvent
            zope.event.notify(event(self, self.request))
            self.update()
        return form.Dialog.__call__(self, *args, **kw)


class AJAXDialogForm(AJAXDialog, form.DialogForm):
    pass


class AJAXDialogAddForm(AJAXDialog, form.DialogAddForm):
    pass
