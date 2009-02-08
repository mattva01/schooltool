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

from zope.interface import Interface
from zope.publisher.browser import BrowserView
from zope.schema import TextLine, Bool
from zope.traversing.api import getName
from zope.traversing.browser.absoluteurl import absoluteURL
from zope.app.container.interfaces import INameChooser
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile


from z3c.form import form, field, button

from schooltool.basicperson.demographics import FieldDescription
from schooltool.basicperson.demographics import TextFieldDescription
from schooltool.basicperson.demographics import DateFieldDescription
from schooltool.basicperson.demographics import EnumFieldDescription
from schooltool.basicperson.interfaces import IFieldDescription
from schooltool.common import SchoolToolMessage as _

class DemographicsView(BrowserView):
    """A Demographics List view."""
    
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
            
class IFieldDescriptionAddForm(Interface):

    title = TextLine(
        title=_("Title"))

    name = PythonIdentifier(
        title=u"Name")

    required = Bool(
        title=u"Required")


class FieldDescriptionAddView(form.AddForm):
    """Add form for Field Descriptions."""
    label = _("Add new Field")
    #template = ViewPageTemplateFile('templates/field_add.pt')
    
    fields = field.Fields(IFieldDescription)

    def updateActions(self):
        super(FieldDescriptionAddView, self).updateActions()
        self.actions['add'].addClass('button-ok')
        self.actions['cancel'].addClass('button-cancel')
        
    @button.buttonAndHandler(_('Add'), name='add')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        obj = self.createAndAdd(data)

        if obj is not None:
            # mark only as finished if we get the new object
            self._finishedAdd = True

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
        fd = TextFieldDescription(data['title'], str(data['name']), data['required'])
        form.applyChanges(self, fd, data)
        self._fd = fd
        return fd


WidgetsValidatorDiscriminators(
    AddSchoolYearOverlapValidator,
    view=FieldDescriptionAddView,
    schema=getSpecification(IFieldDescriptionAddForm, force=True))


