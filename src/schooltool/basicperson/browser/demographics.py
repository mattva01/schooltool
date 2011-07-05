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
from zope.schema.interfaces import IList
from zope.interface import Interface
from zope.interface import implements
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.browser import BrowserView
from zope.traversing.api import getName
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.container.interfaces import INameChooser
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from z3c.form.interfaces import ITextAreaWidget
from z3c.form import form, field, button
from z3c.form.converter import BaseDataConverter, FormatterValidationError

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.basicperson.demographics import TextFieldDescription
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.demographics import BoolFieldDescription
from schooltool.basicperson.demographics import EnumFieldDescription
from schooltool.basicperson.interfaces import IEnumFieldDescription
from schooltool.basicperson.interfaces import IDemographicsFields
from schooltool.basicperson.interfaces import IFieldDescription
from schooltool.basicperson.interfaces import EnumValueList
from schooltool.skin import flourish
from schooltool.skin.flourish.interfaces import IViewletManager
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManager
from schooltool.skin.flourish.content import ContentProvider

from schooltool.common import format_message
from schooltool.common import SchoolToolMessage as _


class CustomEnumDataConverter(BaseDataConverter):
    """A special data converter for iso enums."""

    adapts(EnumValueList, ITextAreaWidget)

    def toWidgetValue(self, value):
        """See interfaces.IDataConverter"""
        if value is self.field.missing_value:
            return u''
        return unicode('\n'.join(value))

    def toFieldValue(self, value):
        """See interfaces.IDataConverter"""
        if value == u'':
            return self.field.missing_value
        lines = filter(None, [s.strip() for s in unicode(value).splitlines()])
        if not lines:
            return self.field.missing_value
        field_value = []
        for line in lines:
            if line in field_value:
                raise FormatterValidationError(
                    format_message(_('Duplicate entry "${value}"'),
                                   mapping={'value': line}),
                    line)
            if len(line) >= 64:
                raise FormatterValidationError(
                    format_message(_('Value too long "${value}"'),
                                   mapping={'value': line}),
                    line)
            field_value.append(line)
        return field_value


class DemographicsFieldsAbsoluteURLAdapter(BrowserView):

    adapts(IDemographicsFields, IBrowserRequest)
    implements(IAbsoluteURL)

    def __str__(self):
        app = ISchoolToolApplication(None)
        url = str(getMultiAdapter((app, self.request), name='absolute_url'))
        return url + '/demographics'

    __call__ = __str__


class DemographicsView(BrowserView):
    """A Demographics List view."""

    title = _('Demographics Container')

    def demographics(self):
        pos = 0
        for demo in list(self.context.values()):
            pos += 1
            yield {'name': demo.__name__,
                   'title': demo.name,
                   'url': absoluteURL(demo, self.request),
                   'pos': pos}

    def positions(self):
        return range(1, len(self.context.values())+1)

    def update(self):
        if 'DELETE' in self.request:
            for name in self.request.get('delete', []):
                del self.context[name]
        elif 'form-submitted' in self.request:
            old_pos, new_pos, move_detected = 0, 0, False
            for activity in self.context.values():
                old_pos += 1
                name = getName(activity)
                if 'pos.'+name not in self.request:
                    continue
                new_pos = int(self.request['pos.'+name])
                if new_pos != old_pos:
                    move_detected = True
                    break
            old_pos, new_pos = old_pos-1, new_pos-1
            keys = list(self.context.keys())
            moving = keys[old_pos]
            keys.remove(moving)
            keys.insert(new_pos,moving)
            self.context.updateOrder(keys)


class FieldDescriptionAddView(form.AddForm):
    """Add form for Field Descriptions."""

    label = _("Add new Field")
    form.extends(form.AddForm)
    template = ViewPageTemplateFile('templates/person_add.pt')
    fields = field.Fields(IFieldDescription)

    def updateActions(self):
        super(FieldDescriptionAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    def nextURL(self):
        return absoluteURL(self._fd, self.request)

    def add(self, fd):
        """Add `schoolyear` to the container."""
        chooser = INameChooser(self.context)
        name = chooser.chooseName(fd.name, fd)
        self.context[name] = fd
        return fd

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)


class TextFieldDescriptionAddView(FieldDescriptionAddView):

    def create(self, data):
        fd = TextFieldDescription(data['title'],
                                  str(data['name']),
                                  data['required'])
        form.applyChanges(self, fd, data)
        self._fd = fd
        return fd


class DateFieldDescriptionAddView(FieldDescriptionAddView):

    def create(self, data):
        fd = DateFieldDescription(data['title'],
                                  str(data['name']),
                                  data['required'])
        form.applyChanges(self, fd, data)
        self._fd = fd
        return fd


class BoolFieldDescriptionAddView(FieldDescriptionAddView):

    def create(self, data):
        fd = BoolFieldDescription(data['title'],
                                  str(data['name']),
                                  data['required'])
        form.applyChanges(self, fd, data)
        self._fd = fd
        return fd


class EnumFieldDescriptionAddView(FieldDescriptionAddView):

    fields = field.Fields(IEnumFieldDescription)

    def create(self, data):
        fd = EnumFieldDescription(data['title'],
                                  str(data['name']),
                                  data['required'])
        form.applyChanges(self, fd, data)
        self._fd = fd
        return fd


class FieldDescriptionEditView(form.EditForm):
    """Edit form for basic person."""
    form.extends(form.EditForm)
    template = ViewPageTemplateFile('templates/person_add.pt')
    fields = field.Fields(IFieldDescription).omit('name')

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        url = absoluteURL(self.context, self.request)
        self.request.response.redirect(url)

    def updateActions(self):
        super(FieldDescriptionEditView, self).updateActions()
        self.actions['apply'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')

    @property
    def label(self):
        return _(u'Change information for ${field_title}',
                 mapping={'field_title': self.context.title})


class EnumFieldDescriptionEditView(FieldDescriptionEditView):

    fields = field.Fields(IEnumFieldDescription).omit('name')


class FieldDescriptionView(form.DisplayForm):
    """Display form for a field description."""
    template = ViewPageTemplateFile('templates/field_description_view.pt')
    fields = field.Fields(IFieldDescription)

    def __call__(self):
        self.update()
        return self.render()


class TextFieldDescriptionView(FieldDescriptionView):
    """Display form for a text field description."""


class DateFieldDescriptionView(FieldDescriptionView):
    """Display form for a date field description."""


class BoolFieldDescriptionView(FieldDescriptionView):
    """Display form for a bool field description."""


class EnumFieldDescriptionView(FieldDescriptionView):
    """Display form for an enum field description."""

    fields = field.Fields(IEnumFieldDescription)


class FlourishDemographicsFieldsLinks(flourish.page.RefineLinksViewlet):
    """demographics fields add links viewlet."""


class FlourishDemographicsFieldsActions(flourish.page.RefineLinksViewlet):
    """demographics fields action links viewlet."""


class FlourishDemographicsView(flourish.page.Page):

    def table(self):
        result = []
        bool_dict = {True: 'x', False: ''}
        for demo in list(self.context.values()):
            classname = demo.__class__.__name__
            teacher, student, admin = False, False, False
            limited = bool(demo.limit_keys)
            for key in demo.limit_keys:
                if key == 'teachers':
                    teacher = True
                if key == 'students':
                    student = True
                if key == 'administrators':
                    admin = True
            result.append({
               'title': demo.title,
               'url': '%s/edit.html' % absoluteURL(demo, self.request),
               'id': demo.name,
               'type': classname[:classname.find('FieldDescription')],
               'required': bool_dict[demo.required],
               'limited': bool_dict[limited],
               'teacher': bool_dict[teacher],
               'student': bool_dict[student],
               'admin': bool_dict[admin],
               })
        return result


class FlourishReorderDemographicsView(flourish.page.Page, DemographicsView):

    def demographics(self):
        pos = 0
        for demo in self.context.values():
            pos += 1
            yield {'name': demo.__name__,
                   'title': demo.title,
                   'pos': pos}

    def update(self):
        if 'DONE' in self.request:
            url = absoluteURL(self.context, self.request)
            self.request.response.redirect(url)
        elif 'form-submitted' in self.request:
            for demo in self.context.values():
                name = 'delete.%s' % demo.__name__
                if name in self.request:
                    del self.context[demo.__name__]
                    return
            old_pos, new_pos, move_detected = 0, 0, False
            for demo in self.context.values():
                old_pos += 1
                name = getName(demo)
                if 'pos.'+name not in self.request:
                    continue
                new_pos = int(self.request['pos.'+name])
                if new_pos != old_pos:
                    move_detected = True
                    break
            old_pos, new_pos = old_pos-1, new_pos-1
            keys = list(self.context.keys())
            moving = keys[old_pos]
            keys.remove(moving)
            keys.insert(new_pos,moving)
            self.context.updateOrder(keys)


class FlourishFieldDescriptionAddView(flourish.page.Page, FieldDescriptionAddView):

    label = None
    title = 'Demographics'
    legend = 'Field Details' 

    def update(self):
        FieldDescriptionAddView.update(self)

    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        super(FlourishFieldDescriptionAddView, self).handleAdd.func(self, action)
        # XXX: hacky sucessful submit check
        if (self._finishedAdd):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context, self.request)


class FlourishTextFieldDescriptionAddView(FlourishFieldDescriptionAddView, TextFieldDescriptionAddView):
    pass


class FlourishDateFieldDescriptionAddView(FlourishFieldDescriptionAddView, DateFieldDescriptionAddView):
    pass


class FlourishBoolFieldDescriptionAddView(FlourishFieldDescriptionAddView, BoolFieldDescriptionAddView):
    pass


class FlourishEnumFieldDescriptionAddView(FlourishFieldDescriptionAddView, EnumFieldDescriptionAddView):
    pass


class FlourishFieldDescriptionEditView(flourish.page.Page, FieldDescriptionEditView):

    def update(self):
        FieldDescriptionEditView.update(self)

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handleApply(self, action):
        super(FlourishFieldDescriptionEditView, self).handleApply.func(self, action)
        # XXX: hacky sucessful submit check
        if (self.status == self.successMessage or
            self.status == self.noChangesMessage):
            self.request.response.redirect(self.nextURL())

    @button.buttonAndHandler(_("Cancel"))
    def handle_cancel_action(self, action):
        self.request.response.redirect(self.nextURL())

    def nextURL(self):
        return absoluteURL(self.context.__parent__, self.request)


class FlourishEnumFieldDescriptionEditView(FlourishFieldDescriptionEditView, EnumFieldDescriptionEditView):

    def update(self):
        EnumFieldDescriptionEditView.update(self)


class FlourishTextFieldDescriptionView(flourish.page.Page, TextFieldDescriptionView):

    def update(self):
        TextFieldDescriptionView.update(self)


class FlourishDateFieldDescriptionView(flourish.page.Page, DateFieldDescriptionView):

    def update(self):
        DateFieldDescriptionView.update(self)


class FlourishBoolFieldDescriptionView(flourish.page.Page, BoolFieldDescriptionView):

    def update(self):
        BoolFieldDescriptionView.update(self)


class FlourishEnumFieldDescriptionView(flourish.page.Page, EnumFieldDescriptionView):

    def update(self):
        EnumFieldDescriptionView.update(self)

