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
import z3c.form.interfaces
from zope.cachedescriptors.property import Lazy
from zope.component import getMultiAdapter
from zope.i18n import translate
from zope.interface import Interface
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.security.proxy import removeSecurityProxy
from z3c.form import button, field, form, widget
from zc.table.column import GetterColumn

from schooltool import table
from schooltool.skin import flourish
from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IRelationshipStateContainer
from schooltool.app.states import RelationshipStateChoice
from schooltool.app.states import RelationshipState
from schooltool.app.states import ACTIVE
from schooltool.app.states import INACTIVE
from schooltool.app.browser.app import EditRelationships
from schooltool.app.browser.app import RelationshipAddTableMixin
from schooltool.app.browser.app import RelationshipRemoveTableMixin
from schooltool.app.browser.app import AddAllResultsButton
from schooltool.app.browser.app import RemoveAllResultsButton

from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.common import format_message, parse_date
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


class EditTemporalRelationships(EditRelationships):

    app_states_name = None

    @Lazy
    def states(self):
        if self.app_states_name is None:
            return None
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        return container.get(self.app_states_name, None)

    def add(self, item, state=None, code=None, date=None):
        collection = removeSecurityProxy(self.getCollection())
        if item not in collection:
            if date is not None:
                collection.on(date).relate(item, state.active, code)
            else:
                collection.add(item)

    def remove(self, item, state=None, code=None, date=None):
        collection = removeSecurityProxy(self.getCollection())
        if item in collection:
            if date is not None:
                collection.on(date).relate(item, state.active, code)
            else:
                collection.remove(item)

    def getSelectedItems(self):
        collection = self.getCollection()
        for person in collection.all():
            yield person

    @property
    def dialog_target(self):
        raise NotImplementedError()


class TemporalRelationshipAddTableMixin(RelationshipAddTableMixin):
    pass


def get_state_column_formatter(table):
    def cell_formatter(value, item, formatter):
        params = {
            'value': value,
            'name': '%s.%s' % (table.button_prefix, table.view.getKey(item)),
            'prefix': table.button_prefix,
            }
        return '<a class="%(prefix)s-action" name="%(name)s" href="#">%(value)s</a>' % params
    return cell_formatter


class TemporalRelationshipRemoveTableMixin(RelationshipRemoveTableMixin):

    button_title = _('Update')
    button_image = 'edit-icon.png'

    def makeTextGetter(self):
        settings = self.view.states
        if settings is None:
            return None
        collection = self.view.getCollection()
        def text(item, formatter=None):
            state = collection.state(removeSecurityProxy(item))
            if state is None:
                return ''
            state_today = state.today
            if state_today is None:
                return ''
            active, code = state_today
            description = settings.states.get(code)
            if description is None:
                return ''
            return description.title
        return text

    def columns(self):
        default = super(TemporalRelationshipRemoveTableMixin, self).columns()
        state = GetterColumn(
            name='state',
            title=_('State'),
            getter=self.makeTextGetter(),
            cell_formatter=get_state_column_formatter(self),
            )
        return default + [state]


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
    dialog_title_template = _("${target}")
    action_prefix = None
    states_source = None

    @property
    def selector(self):
        return 'a.%s' % (self.manager.button_prefix + '-action');

    def getContent(self):
        return self.settings

    @Lazy
    def app_states(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        states = container.get(self.states_source, None)
        if states is None:
            return {}
        return states

    @Lazy
    def current_states(self):
        target = self.target
        if target is None:
            return []
        app_states = self.app_states
        relationships = removeSecurityProxy(self.view.getCollection())
        states = []
        for date, active, code in relationships.state(target) or ():
            state = app_states.states.get(code)
            title = state.title if state is not None else ''
            states.append({
                'date': date,
                'active': app_states.system_titles.get(active, active),
                'code': code,
                'title': title,
                })
        return states

    @property
    def default_state(self):
        target = self.target
        if target is None:
            return None
        app_states = self.app_states
        relationships = removeSecurityProxy(self.view.getCollection())
        target_state = relationships.state(target)
        if target_state is not None:
            app_state = app_states.getState(target_state.today)
            if app_state is not None:
                return app_state
        for state in app_states.states.values():
            if state.active:
                return state
        if app_states.states:
            return app_states.states.values()[0]
        return None

    @button.buttonAndHandler(_("Apply"), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        target = self.target
        if target is None:
            self.status = self.formErrorsMessage
            # XXX: silently close the dialog and pretend that nothing happened
            self.ajax_settings['dialog'] = 'close'
            return
        date = data['date']
        state = data['state']
        relationships = removeSecurityProxy(self.view.getCollection())
        relationships.on(date).relate(target, state.active, state.code)
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

    def updateWidgets(self, prefix=None):
        self.fields['state'].field.source = self.states_source
        super(StateActionDialog, self).updateWidgets(prefix=prefix)

    def updateActions(self):
        super(StateActionDialog, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def initDialog(self):
        self.settings = {}
        super(StateActionDialog, self).initDialog()

    @property
    def target(self):
        keys = [key[len(self.action_prefix)+1:]
                for key in self.request
                if key.startswith(self.action_prefix+'.')]
        targets = self.view.getTargets(keys)
        if targets:
            return targets[0]
        return None

    def updateDialog(self):
        if self.ajax_settings['dialog'] == 'close':
            return
        target = self.target
        if target is not None:
            target_title = getMultiAdapter((target, self.request), name='title')
            dialog_title = translate(
                format_message(
                    self.dialog_title_template, mapping={'target': target_title()}),
                context=self.request)
            self.ajax_settings['dialog']['title'] = dialog_title

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
    action_prefix = 'add_item'

    @property
    def dialog_title_template(self):
        template = (getattr(self.view, 'add_dialog_title_template', None) or
                    getattr(self.view, 'dialog_title_template', None) or
                    _("Assign ${target}"))
        return template

    @property
    def states_source(self):
        source = getattr(self.view, 'app_states_name', None)
        return source


class RemoveStateActionDialog(StateActionDialog):

    action_prefix = 'remove_item'

    @property
    def dialog_title_template(self):
        template = (getattr(self.view, 'add_dialog_title_template', None) or
                    getattr(self.view, 'dialog_title_template', None) or
                    _("Assign ${target}"))
        return template

    @property
    def states_source(self):
        source = getattr(self.view, 'app_states_name', None)
        return source


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
                data = self.getRequestStates()
                if not self.extractStates(data):
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
        for rownum, values in enumerate(self.getRequestStates()):
            results.append(self.buildStateRow(rownum+1, *values))
        results.append(self.buildStateRow(rownum+2, *self.unpack(None)))
        self.states = results

    def buildStateRows(self):
        results = []
        rownum = -1
        for rownum, state in enumerate(self.target.states.values()):
            results.append(
                self.buildStateRow(rownum+1, *self.unpack(state)))
        results.append(self.buildStateRow(rownum+2, *self.unpack(None)))
        self.states = results

    def setMessage(self, message):
        self.message = message
        return False

    def updateStates(self):
        target = self.target
        codes = set([state.code for state in self.validStates])
        for code in set(target.states).difference(codes):
            del target.states[code]
        for state in self.validStates:
            if state.code in target.states:
                del target.states[state.code]
            target.states[state.code] = state
        target.states.updateOrder([state.code for state in self.validStates])

    def getRequestStates(self):
        rownum = 0
        results = []
        while True:
            rownum += 1
            values = self.extract(rownum)
            if values is None:
                break
            if self.isEmpty(*values):
                continue
            results.append(values)
        return results

    def extractStates(self, data):
        states = []
        unique = set()
        for rownum, values in enumerate(data):
            code, title, active = values[:3]
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
            state = self.createState(*values)
            states.append(state)
            unique.add(code)


        used_active = set([state.active for state in states])
        available_active = set(self.target.system_titles.keys())
        missing_active = sorted(available_active.difference(used_active))
        if missing_active:
            return self.setMessage(
                    _('Must have at least one ${title} state.',
                      mapping={'title':
                               translate(removeSecurityProxy(
                                    self.target.system_titles[missing_active[0]]),
                                         context=self.request)
                               }))

        self.validStates = states
        return True

    @property
    def title_value(self):
        if 'form-submitted' in self.request:
            return self.request['title']
        else:
            return ''

    def isEmpty(self, title, code, active, *values):
        return not (len(title) and len(code))

    def unpack(self, state):
        if state is None:
            return '', '', True
        return state.title, state.code, state.active

    def buildStateRow(self, rownum, title, code, active, *values):
        return {
            'title_name': u'title_%d' % rownum,
            'title_value': title,
            'code_name': u'code_%d' % rownum,
            'code_value': code,
            'active_name': u'active_%d' % rownum,
            'active_items': [
                {'syscode': syscode,
                 'selected': 'selected' if syscode == active else None,
                 'title': systitle}
                for syscode, systitle in removeSecurityProxy(self.target.system_titles).items()]
            }

    def extract(self, rownum):
        code_name = u'code_%d' % rownum
        if code_name not in self.request:
            return None
        values = (
            self.request.get(u'title_%d' % rownum, ''),
            self.request.get(code_name, ''),
            self.request.get(u'active_%d' % rownum, ''),
            )
        return values

    def createState(self, title, code, active, *values):
        return removeSecurityProxy(self.context).factory(title, active, code)


class TemporalResultsButton(object):

    states = ()
    default_state = None

    template = InlineViewPageTemplate('''
      <div i18n:domain="schooltool">
        <p>
          <a href="#" onclick="return ST.table.select_all(event);" i18n:translate="">Select All</a> |
          <a href="#" onclick="return ST.table.select_none(event);" i18n:translate="">Select None</a>
        </p>
      </div>
      <div class="temporal-relationship-button-options">
        <select tal:attributes="name view/state_name">
          <option tal:repeat="option view/states"
                  tal:attributes="value option/value;
                                  selected option/selected"
                  tal:content="option/title" />
        </select>
        <input type="text" class="date-field"
               tal:attributes="name view/date_name;
                               value view/date" />
      </div>
      <div class="buttons">
        <input class="submit-widget button-field button-ok" type="submit"
               tal:attributes="name view/button_name;
                               value view/title" />
      </div>
    ''')

    @property
    def state_name(self):
        return self.manager.html_id + '-state'

    @property
    def date_name(self):
        return self.manager.html_id + '-date'

    @property
    def date(self):
        try:
            return parse_date(self.request.get(self.date_name))
        except (ValueError, AttributeError):
            pass
        return self.request.util.today

    @property
    def state(self):
        if self.state_name not in self.request:
            return self.default_state
        for state in self.app_states:
            if state.code ==self.request[self.state_name]:
                return state

    @Lazy
    def app_states(self):
        app = ISchoolToolApplication(None)
        container = IRelationshipStateContainer(app)
        states = container.get(self.view.app_states_name, None)
        if states is None:
            return {}
        return states

    @property
    def states(self):
        result = []
        for state in self.app_states:
            is_selected = state.code == self.request.get(self.state_name)
            is_default = state == self.default_state
            result.append({
                    'title': state.title,
                    'selected': is_selected or is_default,
                    'value': state.code,
                    })
        return result


class TemporalAddAllResultsButton(TemporalResultsButton,
                                  AddAllResultsButton):

    @property
    def default_state(self):
        app_states = self.app_states
        for state in app_states.states.values():
            if state.active == ACTIVE:
                return state
        if app_states.states:
            return app_states.states.values()[0]

    def process_item(self, relationship_view, item):
        item = removeSecurityProxy(item)
        relationship_view.add(item, self.state, self.state.code, self.date)


class TemporalRemoveAllResultsButton(TemporalResultsButton,
                                     RemoveAllResultsButton):

    title = _('Update')

    @property
    def default_state(self):
        app_states = self.app_states
        for state in app_states.states.values():
            if state.active == INACTIVE:
                return state
        if app_states.states:
            return app_states.states.values()[0]

    def process_item(self, relationship_view, item):
        item = removeSecurityProxy(item)
        relationship_view.remove(item, self.state, self.state.code, self.date)
