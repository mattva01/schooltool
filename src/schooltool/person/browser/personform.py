from zope.formlib import form
from zope.app.pagetemplate import ViewPageTemplateFile

from schooltool.traverser.traverser import SingleAttributeTraverserPlugin
from schooltool.person import interfaces

nameinfo_traverser = SingleAttributeTraverserPlugin('nameinfo')

class PageEditForm(form.PageEditForm):
    template = ViewPageTemplateFile('edit_form.pt')
    
class NameInfoEdit(PageEditForm):
    form_fields = form.Fields(interfaces.INameInfo)
