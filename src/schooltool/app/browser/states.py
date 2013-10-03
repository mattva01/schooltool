#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2013 Shuttleworth Foundation
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
import urllib

import zope.schema
from zope.cachedescriptors.property import Lazy
from zope.i18n import translate
from zope.interface import Interface
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security.proxy import removeSecurityProxy
from z3c.form import button, field, form, widget

from schooltool import table
from schooltool.skin import flourish
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IRelationshipStateContainer
from schooltool.app.states import RelationshipStateChoice
from schooltool.app.states import RelationshipState
from schooltool.app.browser.app import EditRelationships
from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.browser.app import RelationshipRemoveTableMixin

from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


class RelationshipStateContainerView(table.table.TableContainerView):

    content_template = flourish.templates.Inline('''
      <div>
        <tal:block content="structure view/container/schooltool:content/ajax/table" />
      </div>
    ''')

    @property
    def container(self):
        app = ISchoolToolApplication(None)
        return IRelationshipStateContainer(app)


class RelationshipStatesEditView(flourish.page.Page):

    content_template = flourish.templates.File('templates/f_states_edit.pt')

    @property
    def title(self):
        return self.target.title

    def update(self):
        self.message = ''

        if 'form-submitted' in self.request:
            if 'CANCEL' in self.request:
                self.request.response.redirect(self.nextURL())

            self.buildRequestStateRows()

            if 'UPDATE_SUBMIT' in self.request:
                if not self.validateStates():
                    return
                self.updateStates()
                self.request.response.redirect(self.nextURL())
        else:
            self.buildStateRows()

    @property
    def target(self):
        return self.context

    def nextURL(self):
        return absoluteURL(self.context.__parent__, self.request)

    def buildRequestStateRows(self):
        results = []
        rownum = -1
        for rownum, (title, code, active) in enumerate(self.getRequestStates()):
            results.append(self.buildStateRow(rownum+1, title, code, active))
        results.append(self.buildStateRow(rownum+2, '', '', True))
        self.states = results

    def buildStateRows(self):
        results = []
        rownum = -1
        for rownum, state in enumerate(self.target.states.values()):
            results.append(
                self.buildStateRow(
                    rownum+1, state.title, state.code, state.active))
        results.append(self.buildStateRow(rownum+2, '', '', True))
        self.states = results

    def buildStateRow(self, rownum, title, code, active):
        return {
            'title_name': u'title_%d' % rownum,
            'title_value': title,
            'code_name': u'code_%d' % rownum,
            'code_value': code,
            'active_name': u'active_%d' % rownum,
            'active_checked': active and 'checked' or None,
            }

    def getRequestStates(self):
        rownum = 0
        results = []
        while True:
            rownum += 1
            title_name = u'title_%d' % rownum
            code_name = u'code_%d' % rownum
            active_name = u'active_%d' % rownum
            if code_name not in self.request:
                break
            if (not len(self.request.get(code_name, '')) or
                not len(self.request.get(title_name, ''))):
                continue
            result = (self.request.get(title_name, ''),
                      self.request.get(code_name, ''),
                      bool(self.request.get(active_name, '')))
            results.append(result)
        return results

    def validateStates(self):
        states = []
        unique = set()
        for rownum, (code, title, active) in enumerate(self.getRequestStates()):
            if code in unique:
                return self.setMessage(
                    _('Duplicate code ${code} in ${row}.',
                      mapping={'code': code, 'row': rownum+1}))
            if not len(code):
                return self.setMessage(
                    _('Code field must not be empty in row ${row}.',
                      mapping={'row': rownum+1}))
            if not len(title):
                return self.setMessage(
                    _('Title field must not be empty in row ${row}.',
                      mapping={'row': rownum+1}))
            states.append(RelationshipState(title, active, code))
            unique.add(code)

        if not any([state.active for state in states]):
            return self.setMessage(_('Must have at least one active state.'))

        if not any([not state.active for state in states]):
            return self.setMessage(_('Must have at least one inactive state.'))

        self.validStates = states
        return True

    def setMessage(self, message):
        self.message = message
        return False

    def updateStates(self):
        target = self.target
        codes = set([state.code for state in self.validStates])
        for code in set(target.states).difference(codes):
            del target.states[code]
        for state in self.validStates:
            target.states[state.code] = state
        target.states.updateOrder([state.code for state in self.validStates])

    @property
    def title_value(self):
        if 'form-submitted' in self.request:
            return self.request['title']
        else:
            return ''



class EditTemporalRelationships(EditRelationships):

    app_states_name = None

    @Lazy
    def states(self):
        if self.app_states_name is None:
            return {}
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        return container.get(self.app_states_name, None)

    def relate(self, item, code, date=None):
        collection = removeSecurityProxy(self.getCollection())
        if item not in collection:
            collection.add(item)

    def remove(self, item, code, date=None):
        collection = removeSecurityProxy(self.getCollection())
        if item in collection:
            collection.remove(item)

    def getSelectedItems(self):
        collection = self.getCollection()
        for person in collection.any():
            yield person


class TemporalRelationshipAddTableMixin(RelationshipAddTableMixin):
    pass


class TemporalRelationshipRemoveTableMixin(RelationshipRemoveTableMixin):

    button_title = _('Status')
    button_image = 'edit-icon.png'

    def makeTextGetter(self):
        settings = self.view.states
        if settings is None:
            return None
        collection = self.view.getCollection()
        def text(item):
            state = collection.state(item)
            if state is None:
                return ''
            active, code = state
            description = settings.states.get(code)
            if description is None:
                return ''
            return description.title
        return text


class TemporalRelationshipTableEditDialog(flourish.ajax.AJAXDialogForm):

    template = flourish.templates.File('templates/f_edit_relationship_state.pt')


class DialogFormWithScript(flourish.ajax.AJAXDialogForm):

    script_template = None
    template = None

    def update(self):
        if not self.fromPublication:
            self.updateScript()
            return
        super(DialogFormWithScript, self).update()

    def updateScript(self):
        flourish.ajax.AJAXPart.update(self)

    def renderScript(self, *args, **kw):
        return self.script_template(*args, **kw)

    def render(self, *args, **kw):
        return self.template(*args, **kw)

    def __call__(self, *args, **kw):
        if not self.fromPublication:
            return self.renderScript()
        return flourish.ajax.AJAXDialogForm.__call__(self, *args, **kw)


class IEditMembership(Interface):

    state = RelationshipStateChoice(
        source="section-membership",
        title=_("Status"),
        required=True)

    date = zope.schema.Date(
        title=_(u"Apply on"),
        description=_(u"(yyyy-mm-dd)"),
        required=True,
        )


class StateActionDialog(DialogFormWithScript):

    script_template = flourish.templates.File('templates/f_edit_relationship_state_script.pt')
    template = flourish.templates.File('templates/f_edit_relationship_state.pt')

    dialog_submit_actions = ('apply',)
    dialog_close_actions = ('cancel',)
    label = None

    settings = None
    fields = field.Fields(IEditMembership)

    # Dialog settings
    dialog_title_template = _("${person}")
    action_prefix = None
    states_source = None

    @property
    def selector(self):
        return 'button.%s' % (self.manager.button_prefix + '-action');

    def getContent(self):
        return self.settings

    @Lazy
    def app_states(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        states = container.get(self.states_source, None)
        if states is None:
            return {}
        return states.states

    @Lazy
    def current_states(self):
        person = self.person
        if person is None:
            return []
        app_states = self.app_states
        relationships = removeSecurityProxy(self.view.getCollection())
        states = []
        for date, active, code in relationships.states(person) or ():
            state = app_states.get(code)
            title = state.title if state is not None else ''
            states.append({
                'date': date,
                'active': active,
                'code': code,
                'title': title,
                })
        return states

    @property
    def default_state(self):
        person = self.person
        if person is None:
            return []
        app_states = self.app_states
        relationships = removeSecurityProxy(self.view.getCollection())
        person_state = relationships.state(person)
        if person_state is not None:
            active, code = person_state
            return app_states.get(code)
        for state in app_states.values():
            if state.active:
                return state
        if app_states:
            app_states.values()[0]
        return None

    @button.buttonAndHandler(_("Apply"), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        person = self.person
        if person is None:
            self.status = self.formErrorsMessage
            # XXX: silently close the dialog and pretend that nothing happened
            self.ajax_settings['dialog'] = 'close'
            return
        date = data['date']
        state = data['state']
        relationships = removeSecurityProxy(self.view.getCollection())
        relationships.on(date).relate(person, state.active, state.code)
        self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        pass

    def nextURL(self):
        prefixes = [
            self.manager.__name__,
            self.manager.extras_prefix,
            ]
        params = []
        for name, value in self.request.items():
            if any([name.startswith(prefix) for prefix in prefixes]):
                if isinstance(value, (list, tuple)):
                    name += ":tokens"
                    value = ' '.join(value)
                params.append('%s=%s' % (
                    urllib.quote(name), urllib.quote_plus(value)))
        url = absoluteURL(self.view, self.request)
        if params:
            url += '?' + '&'.join(params)
        return url

    def updateActions(self):
        super(StateActionDialog, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def initDialog(self):
        self.settings = {}
        super(StateActionDialog, self).initDialog()

    @property
    def person(self):
        entries = [key for key in self.request if key.startswith(self.action_prefix)]
        if not entries:
            return None
        username = sorted(entries)[0][len(self.action_prefix)+1:]
        app = ISchoolToolApplication(None)
        person = app['persons'].get(username)
        return person

    def updateDialog(self):
        if self.ajax_settings['dialog'] == 'close':
            return
        person = self.person
        if person is not None:
            title = translate(
                format_message(
                    self.dialog_title_template, mapping={'person': person.title}),
                context=self.request)
            self.ajax_settings['dialog']['title'] = title

    def postback_form(self):
        prefixes = [
            self.manager.__name__,
            self.action_prefix,
            self.manager.extras_prefix,
            ]
        result = []
        for name, value in self.request.items():
            if any([name.startswith(prefix) for prefix in prefixes]):
                if isinstance(value, (list, tuple)):
                    for part in value:
                        result.append({
                                'name': name,
                                'value': part,
                                })
                else:
                    result.append({
                            'name': name,
                            'value': value,
                            })
        return result


class AddStateActionDialog(StateActionDialog):
    dialog_title_template = _("Enroll ${person}")
    action_prefix = 'add_item'
    states_source = "section-membership"


class RemoveStateActionDialog(StateActionDialog):

    dialog_title_template = _("Enroll ${person}")
    action_prefix = 'remove_item'
    states_source = "section-membership"


EditMembership_date = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.request.util.today,
    view=StateActionDialog,
    field=IEditMembership['date']
    )

EditMembership_state = widget.ComputedWidgetAttribute(
    lambda adapter: adapter.view.default_state,
    view=StateActionDialog,
    field=IEditMembership['state']
    )
