#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Schooltool grade level views.
"""

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.container.interfaces import INameChooser
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL

from z3c.form import form, field, button

import schooltool.skin.flourish.page
import schooltool.skin.flourish.form
import schooltool.skin.flourish.content
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.common.inlinept import InheritTemplate
from schooltool.table.table import simple_form_key
from schooltool.level.interfaces import ILevel, ILevelContainer
from schooltool.level.level import Level
from schooltool.skin import flourish

from schooltool.common import SchoolToolMessage as _


class LevelAddForm(form.AddForm):
    """Contact add form for basic contact."""

    label = _("Add new level")
    template = ViewPageTemplateFile('templates/add_level_subform.pt')
    fields = field.Fields(ILevel)

    def updateActions(self):
        super(LevelAddForm, self).updateActions()
        self.actions['add'].addClass('button-ok')

    @button.buttonAndHandler(_("Add"), name='add')
    def handleAdd(self, action):
        # Pretty, isn't it?
        form.AddForm.handleAdd.func(self, action)

    def create(self, data):
        level = Level()
        form.applyChanges(self, level, data)
        return level

    def add(self, level):
        container = self.getContent()
        name = INameChooser(container).chooseName('', level)
        container[name] = level

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class LevelEditView(form.EditForm):
    template = ViewPageTemplateFile('templates/level_edit.pt')
    fields = field.Fields(ILevel)

    def redirectToContainer(self):
        url = absoluteURL(self.context.__parent__, self.request)
        self.request.response.redirect(url)

    @button.buttonAndHandler(_("Apply"), name='apply')
    def handleApply(self, action):
        # Pretty, isn't it?
        form.EditForm.handleApply.func(self, action)
        self.redirectToContainer()

    @button.buttonAndHandler(_("Cancel"), name='cancel')
    def handle_cancel_action(self, action):
        self.redirectToContainer()

    def updateActions(self):
        super(LevelEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')


class LevelContainerView(BrowserView):
    template = ViewPageTemplateFile('templates/levels.pt')

    def __init__(self, context, request):
        super(LevelContainerView, self).__init__(context, request)
        self.addform = LevelAddForm(context, request)

    def redirectToContainer(self):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def levels(self):
        levels = self.context.values()
        result = []
        positions = range(len(levels))
        for n, level in enumerate(levels):
            pos_numbers = [
                {'value': pos+1,
                 'selected': (pos==n and 'selected' or None)}
                for pos in positions]
            result.append({
                'form_key': simple_form_key(level),
                'level': level,
                'positions': pos_numbers})
        return result

    def handleApply(self):
        keys = list(self.context.keys())
        new_keys = keys[:]
        for old_pos, level in enumerate(self.context.values()):
            form_key = 'pos.%s' % simple_form_key(level)
            if form_key not in self.request:
                continue
            new_pos = int(self.request[form_key]) - 1
            if new_pos != old_pos:
                new_keys.remove(level.__name__)
                new_keys.insert(new_pos, level.__name__)
        if keys != new_keys:
            self.context.updateOrder(new_keys)

    def handleDelete(self):
        formkey_to_name = dict(
            [(simple_form_key(level), level.__name__)
             for level in self.context.values()])
        for form_key in self.request.get('delete', []):
            if form_key in formkey_to_name:
                del self.context[formkey_to_name[form_key]]
        self.redirectToContainer()

    def update(self):
        if 'DELETE' in self.request:
            self.handleDelete()
        elif 'form-submitted' in self.request:
            self.handleApply()

    def __call__(self):
        self.update()
        return self.template()


class FlourishReorderLevelsView(flourish.page.Page, LevelContainerView):

    deleted = False

    def handleDelete(self):
        form_items = dict(
            [(simple_form_key(level), level.__name__)
             for level in self.context.values()])
        for form_key, name in form_items.items():
            if 'delete.%s' % form_key in self.request:
                del self.context[name]
                self.deleted = True

    def update(self):
        self.handleDelete()
        if self.deleted:
            self.request.response.redirect(self.request.URL)
        elif 'form-submitted' in self.request:
            self.handleApply()
            self.request.response.redirect(self.request.URL)


class LevelContainerAbsoluteURLAdapter(BrowserView):
    adapts(ILevelContainer, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = absoluteURL(app, self.request)
        return url + '/levels'

    __call__ = __str__


def appTitleContentFactory(context, request, view, name):
    app = ISchoolToolApplication(None)
    return flourish.content.queryContentProvider(
        app, request, view, 'title')


class FlourishLevelsView(flourish.page.Page):

    @property
    def title(self):
        app = ISchoolToolApplication(None)
        title = flourish.content.queryContentProvider(
            app, self.request, self, 'title')
        return title.title

    def table(self):
        result = []
        for level in list(self.context.values()):
            result.append({
               'level': level,
               })
        return result


class FlourishLevelAddView(flourish.form.AddForm, LevelAddForm):
    template = flourish.templates.Inherit(flourish.page.Page.template)
    label = None
    legend = _('Level information')

    def updateActions(self):
        super(FlourishLevelAddView, self).updateActions()
        self.actions['cancel'].addClass('button-cancel')

class FlourishLevelEditView(flourish.form.Form, LevelEditView):
    template = InheritTemplate(flourish.page.Page.template)
    label = None
    legend = _('Level information')


class LevelsAddLinks(flourish.page.RefineLinksViewlet):
    """Manager for Add links."""


class LevelsActionsLinks(flourish.page.RefineLinksViewlet):
    """Manager for Actions links."""
