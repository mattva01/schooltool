from zope.interface import implements
from zope.formlib import form
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.app.form.browser.interfaces import ITerms
from schooltool.traverser.traverser import SingleAttributeTraverserPlugin
from schooltool.person.browser.person import PersonAddView as PersonAddViewBase
from schooltool.demographics.person import Person
from schooltool.demographics import interfaces

class PageDisplayForm(form.PageDisplayForm):
    template = ViewPageTemplateFile('display_form.pt')

class PageEditForm(form.PageEditForm):
    template = ViewPageTemplateFile('edit_form.pt')

nameinfo_traverser = SingleAttributeTraverserPlugin('nameinfo')

class NameInfoEdit(PageEditForm):
    form_fields = form.Fields(interfaces.INameInfo)

class NameInfoDisplay(PageDisplayForm):
    form_fields = form.Fields(interfaces.INameInfo)

demographics_traverser = SingleAttributeTraverserPlugin('demographics')

class DemographicsEdit(PageEditForm):
    form_fields = form.Fields(interfaces.IDemographics)

class DemographicsDisplay(PageDisplayForm):
    form_fields = form.Fields(interfaces.IDemographics)

schooldata_traverser = SingleAttributeTraverserPlugin('schooldata')

class SchoolDataEdit(PageEditForm):
    form_fields = form.Fields(interfaces.ISchoolData)
    
class SchoolDataDisplay(PageDisplayForm):
    form_fields = form.Fields(interfaces.ISchoolData)

parent1_traverser = SingleAttributeTraverserPlugin('parent1')
parent2_traverser = SingleAttributeTraverserPlugin('parent2')
emergency1_traverser = SingleAttributeTraverserPlugin('emergency1')
emergency2_traverser = SingleAttributeTraverserPlugin('emergency2')
emergency3_traverser = SingleAttributeTraverserPlugin('emergency3')

class ContactInfoEdit(PageEditForm):
    form_fields = form.Fields(interfaces.IContactInfo)
    
class ContactInfoDisplay(PageDisplayForm):
    form_fields = form.Fields(interfaces.IContactInfo)
    
class PersonAddView(PersonAddViewBase):
    _factory = Person

class Term(object):
    def __init__(self, title, value):
        self.title = title
        self.token = value
        self.value = value
        
class Terms(object):
    implements(ITerms)

    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def getTerm(self, value):
        return Term(value, value)

    def getValue(self, token):
        return token
