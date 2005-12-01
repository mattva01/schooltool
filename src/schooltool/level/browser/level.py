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
Level views.

$Id: app.py 3481 2005-04-21 15:28:29Z bskahan $
"""
import zope.component
import zope.interface
import zope.schema
from zope.security import proxy
from zope.app import zapi
from zope.app.form.browser import add
from zope.app.publisher import browser

from schooltool.level import interfaces
from schooltool import SchoolToolMessage as _
from schooltool.app.browser import app

class LevelContainerView(app.ContainerView):
    """A Level Container view."""

    __used_for__ = interfaces.ILevelContainer

    index_title = _("Level index")
    add_title = _("Add a new level")
    add_url = "+/addSchoolToolLevel.html"


class LevelValidationView(browser.BrowserView):
    """Validate the level graphs."""

    def validate(self):
        if 'VALIDATE' in self.request:
            try:
                self.context.validate()
            except interfaces.LevelValidationError, error:
                return zapi.getMultiAdapter((error, self.request), name="info")


class IEditLevelSchema(interfaces.ILevel):

    previousLevel = zope.schema.Choice(
        title=_("Previous Level"),
        description=_("The previous level in the school. If None, then "
                      "there is no previous level."),
        vocabulary="Levels",
        required=False,
        default=None)


class EditLevelAdapter(object):
    """Adapter to allow us display the previous level as an option."""

    zope.interface.implements(IEditLevelSchema)
    zope.component.adapts(interfaces.ILevel)

    def __init__(self, context):
        # Make sure we are not using setattr to set the context
        self.__dict__['context'] = context

    def __getattr__(self, name):
        return getattr(self.context, name)

    def __setattr__(self, name, value):
        if name is 'previousLevel':
            prevLevel = self.getPreviousLevel()
            if prevLevel is not None:
                prevLevel.nextLevel = None
            if value is not None:
                value.nextLevel = proxy.removeSecurityProxy(self.context)
        else:
            setattr(self.context, name, value)

    def getPreviousLevel(self):
        parent = zapi.getParent(self.context)
        for level in parent.values():
            if level.nextLevel == self.context:
                return level

    previousLevel = property(getPreviousLevel)


class LevelAddView(add.AddView):
    """A view for adding Levels."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return add.AddView.update(self)


class LevelEditView(app.BaseEditView):
    """View for editing Levels."""

    __used_for__ = interfaces.ILevel
