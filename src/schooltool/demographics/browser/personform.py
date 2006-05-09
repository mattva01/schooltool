from zope.formlib import form
from zope.app.pagetemplate import ViewPageTemplateFile

from schooltool.traverser.traverser import SingleAttributeTraverserPlugin
from schooltool.person.browser.person import PersonAddView as PersonAddViewBase
from schooltool.demographics.person import Person
from schooltool.demographics import interfaces

nameinfo_traverser = SingleAttributeTraverserPlugin('nameinfo')

class PageDisplayForm(form.PageDisplayForm):
    template = ViewPageTemplateFile('display_form.pt')

class PageEditForm(form.PageEditForm):
    template = ViewPageTemplateFile('edit_form.pt')

class NameInfoEdit(PageEditForm):
    form_fields = form.Fields(interfaces.INameInfo)

class NameInfoDisplay(PageDisplayForm):
    form_fields = form.Fields(interfaces.INameInfo)
    
class PersonAddView(PersonAddViewBase):
    _factory = Person

