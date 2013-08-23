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
SchoolTool flourish resource extension.
"""
import zope.schema

import zc.resourcelibrary
import zc.resourcelibrary.resourcelibrary
from zope.component import adapts, queryAdapter
from zope.interface import implements, Interface, Attribute
from zope.publisher.interfaces.browser import IBrowserRequest


class IResourceLibrary(Interface):
    """Dynamic resource library."""

    __name__ = zope.schema.TextLine(
        title=u"Library name")

    configure = Attribute("Configure the library class")

    required = zope.schema.List(
        title=u"Required libraries",
        value_type=zope.schema.TextLine())

    included = zope.schema.List(
        title=u"Included files in this library",
        value_type=zope.schema.TextLine())


_hooks = None


def getRequired(name):
    request = zc.resourcelibrary.resourcelibrary.getRequest()
    lib = queryAdapter(request, IResourceLibrary, name=name)
    if lib is None:
        global _hooks
        if _hooks is not None:
            return _hooks['getRequired'](name)
        return ()
    return lib.required


def getIncluded(name, alternative=None):
    request = zc.resourcelibrary.resourcelibrary.getRequest()
    lib = queryAdapter(request, IResourceLibrary, name=name)
    if lib is None:
        global _hooks
        if _hooks is not None:
            return _hooks['getIncluded'](name)
        return ()
    return lib.included


def patch_zc_resourcelibrary():
    global _hooks
    if _hooks is None:
        _hooks = {
            'getRequired': zc.resourcelibrary.getRequired,
            'getIncluded': zc.resourcelibrary.getIncluded,
            }
        # Monkeypatch zc.resourcelibrary
        zc.resourcelibrary.getRequired = getRequired
        zc.resourcelibrary.getIncluded = getIncluded


def unpatch_zc_resourcelibrary():
    global _hooks
    if _hooks is not None:
        zc.resourcelibrary.getRequired = _hooks['getRequired']
        zc.resourcelibrary.getIncluded = _hooks['getIncluded']
    _hooks = None


try:
    from zope.testing.cleanup import addCleanUp
except ImportError:
    pass
else:
    addCleanUp(unpatch_zc_resourcelibrary)
    del addCleanUp


class ResourceLibrary(object):
    adapts(IBrowserRequest)
    implements(IResourceLibrary)

    __name__ = None

    def __init__(self, request):
        self.request = request

    @classmethod
    def configure(cls):
        pass

    @property
    def required(self):
        global _hooks
        if _hooks is not None:
            return _hooks['getRequired'](self.__name__)
        return ()

    @property
    def included(self):
        global _hooks
        if _hooks is not None:
            return _hooks['getIncluded'](self.__name__)
        return ()
