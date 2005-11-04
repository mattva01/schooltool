#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
API doc views

$Id$
"""
__docformat__ = 'restructuredtext'

import zope.interface

import zope.app.apidoc.ifacemodule.menu
import zope.app.apidoc.codemodule.browser.menu
import zope.app.apidoc.bookmodule.browser
from zope.app.apidoc import apidoc
from zope.app.apidoc import ifacemodule, codemodule, bookmodule, zcmlmodule
from zope.app.apidoc.browser.skin import APIDOC

from schooltool.devmode.skin import IDevModeLayer


class schooltoolApidocNamespace(apidoc.apidocNamespace):
    """Used to traverse to an API Documentation."""
    def __init__(self, ob, request=None):
        super(schooltoolApidocNamespace, self).__init__(ob, request)
        # A small hack to ensure that SchoolTool stuff is available.
        if request:
            zope.interface.directlyProvides(
                request, [IDevModeLayer, APIDOC])

    def traverse(self, name, ignore):
        return apidoc.handleNamespace(self.context, name)



class InterfaceMenu(ifacemodule.menu.Menu):

    def findInterfaces(self):
        for entry in super(InterfaceMenu, self).findInterfaces():
            if 'schooltool' not in entry['name']:
                continue
            entry['name'] = entry['name'].replace('schooltool', 'st')
            yield entry


class CodeMenu(codemodule.browser.menu.Menu):

    def findClasses(self):
        for entry in super(CodeMenu, self).findClasses():
            if 'schooltool' not in entry['path']:
                continue
            entry['path'] = entry['path'].replace('schooltool', 'st')
            yield entry


class BookMenu(bookmodule.browser.Menu):

    def getMenuLink(self, node):
        link = super(BookMenu, self).getMenuLink(node)
        return link and '../' + link or None


def patchZCMLModule():
    from schooltool.app import main
    from zope.configuration import docutils, xmlconfig, config

    def _makeDocStructure(self):
        context = config.ConfigurationMachine()
        context.provideFeature('devmode')
        xmlconfig.registerCommonDirectives(context)
        context = xmlconfig.file(main.SCHOOLTOOL_SITE_DEFINITION,
                                 context=context,
                                 execute=False)
        namespaces, subdirs = docutils.makeDocStructures(context)

        # Empty keys are not so good for a container
        if namespaces.has_key(''):
            namespaces['ALL'] = namespaces['']
            del namespaces['']

        # Some trivial caching
        zcmlmodule.namespaces = namespaces
        zcmlmodule.subdirs = subdirs

    zcmlmodule.ZCMLModule._makeDocStructure = _makeDocStructure
