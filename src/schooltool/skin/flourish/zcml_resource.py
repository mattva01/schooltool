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
SchoolTool flourish zcml directives.
"""

import zope.component.zcml
import zope.configuration.fields
import zc.resourcelibrary.zcml
from zope.interface import Interface

from schooltool.skin.flourish.resource import patch_zc_resourcelibrary
from schooltool.skin.flourish.resource import IResourceLibrary
from schooltool.skin.flourish import IFlourishLayer


class IDynamicLibraryDirective(Interface):

    class_ = zope.configuration.fields.GlobalObject(
        title=u"Class",
        description=u"A class that selects dependencies and includes.",
        required=True,
        )


IDynamicLibraryDirective.setTaggedValue('keyword_arguments', True)


class ResourceLibrary(zc.resourcelibrary.zcml.ResourceLibrary):

    def library(self, _context, class_, **kwargs):
        patch_zc_resourcelibrary()
        class_dict = dict(kwargs)
        class_dict['__name__'] = self.name
        class_ = type(class_.__name__, (class_, ), class_dict)
        class_.configure()

        _context.action(
            discriminator=('schooltool.skin.flourish.resource-library',
                           self.layer, self.name),
            callable=zope.component.zcml.handler,
            args=('registerAdapter',
                  class_,
                  (self.layer, ),
                  IResourceLibrary,
                  self.name,
                  _context.info),
            )
