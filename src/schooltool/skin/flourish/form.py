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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
SchoolTool flourish forms.
"""
import z3c.form.form

import schooltool.skin.flourish.page
from schooltool.skin import flourish


class Form(z3c.form.form.Form, flourish.page.Page):
    __call__ = flourish.page.Page.__call__

    def update(self):
        super(Form, self).update()

    def updateActions(self):
        super(Form, self).updateActions()


class DialogForm(Form):
    dialog_close_actions = ()
    dialog_submit_actions = ()

    def updateActions(self):
        super(DialogForm, self).updateActions()
        for name in self.dialog_submit_actions:
            self.actions[name].onclick = u'ST.dialogs.submit(this, this)'
        for name in self.dialog_close_actions:
            self.actions[name].onclick = u'ST.dialogs.close(this)'
