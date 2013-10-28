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
SchoolTool flourish forms.
"""
from zope.component import adapts
from zope.interface import Interface
from zope.schema.interfaces import IBool
from zope.schema import ValidationError
import z3c.form.form
from z3c.form.error import ErrorViewSnippet
from z3c.form.term import BoolTerms
from z3c.form.interfaces import IRadioWidget

from schooltool.skin.flourish import page, content, viewlet, tal
from schooltool.common.inlinept import InheritTemplate
from schooltool.skin.flourish.interfaces import IFlourishLayer

from schooltool.common import SchoolToolMessage as _


class FlourishRadioBoolTerms(BoolTerms):

    adapts(Interface,
           IFlourishLayer,
           Interface,
           IBool,
           IRadioWidget)

    trueLabel = _('Yes')
    falseLabel = _('No')


class Form(z3c.form.form.Form, page.PageBase):
    __call__ = page.PageBase.__call__
    formErrorsMessage = _('Please correct the marked fields below.')
    template = InheritTemplate(page.PageBase.template)

    def update(self):
        super(Form, self).update()

    def updateActions(self):
        super(Form, self).updateActions()


class DisplayForm(z3c.form.form.DisplayForm, page.PageBase):
    template = InheritTemplate(page.PageBase.template)
    __call__ = page.PageBase.__call__

    def update(self):
        super(DisplayForm, self).update()


class AddForm(Form, z3c.form.form.AddForm):

    def update(self):
        super(AddForm, self).update()
        if self._finishedAdd:
            self.request.response.redirect(self.nextURL())
            return ""

    @z3c.form.button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        return z3c.form.form.AddForm.handleAdd.func(self, action)

    @z3c.form.button.buttonAndHandler(_('Cancel'), name='cancel')
    def handleCancel(self, action):
        self.request.response.redirect(self.nextURL())


class Dialog(page.PageBase):

    # Set this to False if you don't want the browser to reload the whole
    # page, but display the redirected result in the dialog instead.
    reload_parent = True

    # These will be passed to the dialog handler.
    ajax_settings = None

    def __init__(self, *args, **kw):
        super(Dialog, self).__init__(*args, **kw)
        self.ajax_settings = {}

    def initDialog(self):
        self.ajax_settings['dialog'] = {
            'autoOpen': True,
            'modal': True,
            'resizable': False,
            'draggable': False,
            'position': ['center','middle'],
            'width': '560',
            }

    def updateDialog(self):
        pass

    def update(self):
        self.initDialog()
        super(Dialog, self).update()
        self.updateDialog()

    def __call__(self, *args, **kw):
        result = super(Dialog, self).__call__(*args, **kw)

        if not self.ajax_settings.get('html'):
            self.ajax_settings['html'] = result

        response = self.request.response
        if (self.reload_parent and
            not self.ajax_settings.get('redirect') and
            response.getStatus() in [300, 301, 302, 303, 304, 305, 307]):
            self.ajax_settings['redirect'] = response.getHeader('Location')
            self.ajax_settings['dialog'] = 'close'

        response.reset()
        response.setHeader('Content-Type', 'application/json')
        encoder = tal.JSONEncoder()

        json = encoder.encode(self.ajax_settings)
        return json


class DialogForm(Dialog, Form):
    dialog_close_actions = ()
    dialog_submit_actions = ()

    def updateActions(self):
        super(DialogForm, self).updateActions()
        for name in self.dialog_submit_actions:
            action = self.actions[name]
            action.onclick = u'return ST.dialogs.submit(this, this);'
        for name in self.dialog_close_actions:
            action = self.actions[name]
            action.onclick = u'return ST.dialogs.close(this);'


class DialogAddForm(DialogForm, AddForm):
    pass


class FlourishErrorViewSnippet(ErrorViewSnippet):

    adapts(ValidationError, IFlourishLayer, None, None, None, None)

    def update(self):
        super(FlourishErrorViewSnippet, self).update()
        self.widget.addClass('error')


class FormContent(content.ContentProvider, z3c.form.form.Form):

    def update(self):
        z3c.form.form.Form.update(self)
        content.ContentProvider.update(self)

    def render(self, *args, **kw):
        return z3c.form.form.Form.render(self)


class FormViewlet(viewlet.Viewlet, z3c.form.form.Form):

    def update(self):
        z3c.form.form.Form.update(self)
        viewlet.Viewlet.update(self)

    def render(self, *args, **kw):
        return z3c.form.form.Form.render(self)
