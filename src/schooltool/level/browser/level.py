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
from zope.app import zapi
from zope.app.form.browser import add
from zope.app.publisher import browser

from schooltool.level import interfaces
from schooltool import SchoolToolMessageID as _
from schooltool.browser import app
from schoolbell.app.browser import app as sb_app

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


class LevelAddView(add.AddView):
    """A view for adding Levels."""

    def nextURL(self):
        return zapi.absoluteURL(self.context.context, self.request)

    def update(self):
        if 'CANCEL' in self.request:
            self.request.response.redirect(self.nextURL())
        else:
            return add.AddView.update(self)


class LevelEditView(sb_app.BaseEditView):
    """View for editing Levels."""

    __used_for__ = interfaces.ILevel
