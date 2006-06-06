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

import pytz
import datetime
from zope.app import zapi
from zope.interface import implements
from zope import event
from zope.formlib import form
from zope.formlib.interfaces import IAction
from zope.lifecycleevent import ObjectModifiedEvent
from zope.interface.common import idatetime
from zope.schema import TextLine
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.form.browser.interfaces import ITerms
from zope.app.publisher.browser.menu import getMenu, BrowserMenu
from zope.schema.interfaces import ITitledTokenizedTerm
from zope.app.form.browser.interfaces import ITerms
from zope.publisher.browser import BrowserView

from schooltool.skin.form import AttributeEditForm
from schooltool.traverser.traverser import SingleAttributeTraverserPlugin
from schooltool.person.interfaces import IReadPerson
from schooltool.demographics.person import Person
from schooltool.demographics import interfaces
from schooltool import SchoolToolMessage as _
from schooltool.app.app import ISchoolToolApplication

class PersonDisplayForm(form.PageDisplayForm):
    """Base class for all person display forms.
    """
    template = ViewPageTemplateFile('display_form.pt')

    def actualContext(self):
        return self.context.__parent__
    
    def getMenu(self):
        return getMenu('person_display_menu', self.context, self.request)


class AttributeMenu(BrowserMenu):
    """A special menu that can:

    * display the menu in context of the parent of the current
      attribute object.

    * displays relative links for the parent object

    * can show which attribute is currently highlighted
    """
    
    def getMenuItems(self, object, request):
        # all rather hackish, but functional
        obj_url = zapi.absoluteURL(object.__parent__, request)
        items = super(AttributeMenu, self).getMenuItems(object, request)
        for item in items:
            action = item['action']
            if action.startswith('/'):
                # determine which attribute we're viewing by looking at
                # the action supplied..
                attribute_name = action.split('/')[1]
                if attribute_name == object.__name__:
                    item['selected'] = True
                item['action'] = '%s%s' % (obj_url, item['action'])
        return items

    
class PersonEditForm(AttributeEditForm):
    """Base class of all person edit forms.
    """
    def getMenu(self):
        return getMenu('person_edit_menu', self.context, self.request)

    def fullname(self):
        return IReadPerson(self.context.__parent__).title
        

nameinfo_traverser = SingleAttributeTraverserPlugin('nameinfo')


class PersonView(BrowserView):
    """The default view of the person. Redirects to the nameinfo view.
    """
    def __call__(self):
        url = zapi.absoluteURL(self.context.nameinfo, self.request)
        return self.request.response.redirect(url)


class PersonEditView(BrowserView):
    """The default edit view of the person. Redirects to the edit view
    of nameinfo.
    """
    def __call__(self):
        url = (zapi.absoluteURL(self.context.nameinfo, self.request) +
               '/edit.html')
        return self.request.response.redirect(url)
    

class NameInfoEdit(PersonEditForm):
    def title(self):
        return _(u'Change name information for ${fullname}',
                 mapping={'fullname':self.fullname()})
    
    form_fields = form.Fields(interfaces.INameInfo)


class NameInfoDisplay(PersonDisplayForm):
    def title(self):
        return _(u'Change name')
    
    form_fields = form.Fields(interfaces.INameInfo)


demographics_traverser = SingleAttributeTraverserPlugin('demographics')


class DemographicsEdit(PersonEditForm):
    def title(self):
        return _(u'Change demographics for ${fullname}',
                 mapping={'fullname': self.fullname()})
    
    form_fields = form.Fields(interfaces.IDemographics)
    

class DemographicsDisplay(PersonDisplayForm):
    def title(self):
        return _(u'Demographics')
    form_fields = form.Fields(interfaces.IDemographics)


schooldata_traverser = SingleAttributeTraverserPlugin('schooldata')


class SchoolDataEdit(PersonEditForm):
    template = ViewPageTemplateFile("schooldata_edit.pt")
    
    def title(self):
        return _(u'Change school data for ${fullname}',
                 mapping={'fullname': self.fullname()})
    
    form_fields = form.Fields(interfaces.ISchoolData)
    

class SchoolDataDisplay(PersonDisplayForm):
    template = ViewPageTemplateFile("schooldata_view.pt")
    
    def title(self):
        return _(u'School data')
    
    form_fields = form.Fields(interfaces.ISchoolData)


parent1_traverser = SingleAttributeTraverserPlugin('parent1')
parent2_traverser = SingleAttributeTraverserPlugin('parent2')
emergency1_traverser = SingleAttributeTraverserPlugin('emergency1')
emergency2_traverser = SingleAttributeTraverserPlugin('emergency2')
emergency3_traverser = SingleAttributeTraverserPlugin('emergency3')


class ContactInfoEdit(PersonEditForm):
    # XXX need to distinguish between the different contact informations
    # somehow. Is there a sane way to do this without introducing an
    # abundance of views *and* interfaces *and* change the content
    # model?
    def title(self):
        return _(u"Change contact information for ${fullname}",
                 mapping={'fullname': self.fullname()})
    
    form_fields = form.Fields(interfaces.IContactInfo)


class ContactInfoDisplay(PersonDisplayForm):
    def title(self):
        return _(u"Contact information")
    
    form_fields = form.Fields(interfaces.IContactInfo)


class Term(object):
    """Simplistic term that uses value as token.
    """
    def __init__(self, value):
        self.title = value
        self.token = value
        self.value = value
        

class Terms(object):
    """Simplistic term that just uses the value as the token.
    """
    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def getTerm(self, value):
        return Term(value)

    def getValue(self, token):
        return token

from schooltool.person.browser.person import IPersonAddForm as IPersonAddForm_
from schooltool.person.browser.person import PersonAddView as PersonAddView_
from schooltool.person.browser.person import setUpPersonAddCustomWidgets


class IPersonAddForm(IPersonAddForm_):
    """Like schooltool.app.person's addform, but add the last name field.
    """
    last_name = TextLine(
        title=_("Last name"))
    

class PersonAddView(PersonAddView_):
    """Like schooltool.app.person's addform, but add last_name field.
    """
    form_fields = form.Fields(IPersonAddForm, render_context=False)
    form_fields = form_fields.select('title', 'last_name', 'username',
                                     'password', 'photo', 'groups')
    # use the setup code from schooltool.app.person
    setUpPersonAddCustomWidgets(form_fields)

    # extra initialization
    def initPerson(self, person, data):
        person.nameinfo.last_name = data['last_name']


class TeachersTerm(object):
    """A term for displaying a teacher.
    """
    implements(ITitledTokenizedTerm)
    
    def __init__(self, value):
        persons = ISchoolToolApplication(None)['persons']
        if value in persons:
            self.title = persons[value].title
        else:
            self.title = _(
                u"Invalid teacher. Possible causes: deleted or renamed.")
        self.token = value
        self.value = value
        

class TeachersTerms(object):
    """Displaying teachers.
    """
    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def getTerm(self, value):
        return TeachersTerm(value)

    def getValue(self, token):
        return token


class GroupsTerm(object):
    """A term for displaying a group.
    """
    implements(ITitledTokenizedTerm)
    
    def __init__(self, value):
        groups = ISchoolToolApplication(None)['groups']
        if value in groups:
            self.title = groups[value].title
        else:
            self.title = _(
                u"Invalid group. Possible causes: deleted or renamed.")
        self.token = value
        self.value = value


class GroupsTerms(object):
    """Displaying groups.
    """
    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def getTerm(self, value):
        return GroupsTerm(value)

    def getValue(self, token):
        return token
