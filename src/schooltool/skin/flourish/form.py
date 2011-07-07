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
import schooltool.skin.flourish.tal
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

    # Set this to False if you don't want the browser to reload the whole
    # page, but display the redirected result in the dialog instead.
    reload_parent = True

    # These will be passed to the dialog handler.
    ajax_settings = None

    def __init__(self, *args, **kw):
        super(DialogForm, self).__init__(*args, **kw)
        self.ajax_settings = {}

    def initModalDialog(self):
        self.ajax_settings['dialog'] = {
            'autoOpen': True,
            'modal': True,
            'resizable': False,
            'draggable': False,
            'position': ['center','middle'],
            'width': 'auto',
            }

    def updateModalDialog(self):
        pass

    def update(self):
        self.initModalDialog()
        super(Form, self).update()
        self.updateModalDialog()

    def updateActions(self):
        super(DialogForm, self).updateActions()
        for name in self.dialog_submit_actions:
            self.actions[name].onclick = u'ST.dialogs.submit(this, this)'
        for name in self.dialog_close_actions:
            self.actions[name].onclick = u'ST.dialogs.close(this)'

    def __call__(self, *args, **kw):
        result = super(DialogForm, self).__call__(*args, **kw)

        self.ajax_settings['html'] = result

        response = self.request.response
        if (self.reload_parent and
            not self.ajax_settings.get('redirect') and
            response.getStatus() in [300, 301, 302, 303, 304, 305, 307]):
            self.ajax_settings['redirect'] = response.getHeader('Location')
            self.ajax_settings['dialog'] = 'close'

        response.reset()
        response.setHeader('Content-Type', 'application/json')
        encoder = flourish.tal.JSONEncoder()

        json = encoder.encode(self.ajax_settings)
        return json
