#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2004 Shuttleworth Foundation
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
"""
Web-application views for the schooltool.infofacets.

$Id$
"""

from schooltool.component import getPath, traverse, getDynamicFacetSchemaService
from schooltool.component import FacetManager
from schooltool.interfaces import IDynamicFacet, IDynamicFacetSchemaService
from schooltool.infofacets import DynamicFacet
from schooltool.rest import absoluteURL
from schooltool.translation import ugettext as _
from schooltool.browser import valid_name
from schooltool.browser import AppObjectBreadcrumbsMixin
from schooltool.browser import notFoundPage, ToplevelBreadcrumbsMixin
from schooltool.browser import View, Template
from schooltool.browser.auth import ManagerAccess, PrivateAccess, PublicAccess
from schooltool.browser.timetable import ContainerServiceViewBase
from schooltool.browser.widgets import TextWidget, PasswordWidget
from schooltool.browser.widgets import TextAreaWidget, SelectionWidget
from schooltool.browser.widgets import CheckboxWidget, MultiselectionWidget


class DynamicFacetView(View, AppObjectBreadcrumbsMixin):
    """View for a DynamicFacet.

    Can be accessed at /dfschemas/$id
    """

    __used_for__ = IDynamicFacet
    authorization = PrivateAccess
    template = Template("www/dfacet.pt")

    def __init__(self, context, key):
        View.__init__(self, context)
        self.key = key

    def breadcrumbs(self):
        owner = self.context.__parent__.__parent__
        breadcrumbs = AppObjectBreadcrumbsMixin.breadcrumbs(self,
                                                            context=owner)
        name = self.context.__name__
        breadcrumbs.append((_('Dynamic facet for %s, %s') % name,
                            self.request.uri))
        return breadcrumbs

    def title(self):
        infofacetd = self.context.__parent__.__parent__
        return _("%s's infofacet for %s") % (infofacetd.title,
                                             ", ".join(self.key))

    def canEdit(self):
        # RESTive timetable views only allow managers to change timetables
        return self.isManager()

    def do_POST(self, request):
        if not self.canEdit():
            return self.do_GET(request)
        for exc in self._exceptionsToRemove(request):
            tt = exc.activity.timetable
            tt.exceptions.remove(exc)
        # Cannot just call do_GET here, because self.context is most likely a
        # composite timetable that needs to be regenerated.
        return self.redirect(request.uri, request)

    def _traverse(self, name, request):
        print "GOT TO THE TRAVERSE"
        schema = self.context.__parent__.__parent__
        if name == 'setup.html' and IPerson.providedBy(schema):
            return DynamicFacetSetupView(schema, self.key)
        else:
            raise KeyError(name)
        print "er, no setup..."


class DynamicFacetSchemaView(DynamicFacetView):
    """View for a dynamic facet schema

    Can be accessed at /dfschemas/$schema.
    """

    authorization = ManagerAccess

    def __init__(self, context):
        DynamicFacetView.__init__(self, context, None)

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Dynamic facet schemas'),
             absoluteURL(self.request, app, 'dfschemas')),
            (name, absoluteURL(self.request, app, 'dfschemas', name))]

    def title(self):
        return "Dynamic facet schema %s" % self.context.__name__


class DynamicFacetSchemaServiceView(ContainerServiceViewBase):
    """View for the dynamicfacet schema service"""

    template = Template("www/dfschemas.pt")
    newpath = "/newdfschema"
    subview = DynamicFacetSchemaView

    def logDeletion(self, schema):
        """Taken from browser.timetable.TimetableSchemaServiceView"""
        self.request.appLog(_("Dynamic facet schema %s deleted")
                            % getPath(schema))

    def breadcrumbs(self):
        app = traverse(self.context, '/')
        name = self.context.__name__
        return [
            (_('Start'), absoluteURL(self.request, app, 'start')),
            (_('Dynamic facet schemas'), absoluteURL(self.request, app,
                                                 'dfschemas'))]


class DynamicFacetSchemaWizard(View):

    __used_for__ = IDynamicFacetSchemaService

    authorization = ManagerAccess

    template = Template("www/dfschema-wizard.pt")

    error = None

    def __init__(self, context):
        View.__init__(self, context)
        self.newlabel_widget = TextWidget('newlabel', _('Label'))
        self.newfield_widget = SelectionWidget('newfield', _('Add New Field'),
                (
                    ('text', 'Text (a single line)'),
                    ('textarea', 'Text Area'),
                    ('selection', 'Selection'),
                    ('multiselection', 'Multiselection'),
                    ('checkbox', 'Checkbox')
                    )
                )

        self.name_widget = TextWidget('name', _('Dynamic Facet Name'))
        self.name_widget = TextWidget('name', _('Name'), self.name_parser,
                                      self.name_validator)

    def name_parser(name):
        """Strip whitespace from names.

        This was taken from browser.timetable.TimeTableSchemaWizard and should
        probably be refactored.
        """
        if name is None:
            return None
        return name.strip()

    name_parser = staticmethod(name_parser)

    def name_validator(self, name):
        """Validate the name given to the schema. 

        This was taken from browser.timetable.TimeTableSchemaWizard and should
        probably be refactored.
        """
        if name is None:
            return
        if not name:
            raise ValueError(_("Schema name must not be empty"))
        elif not valid_name(name):
            raise ValueError(_("Schema name can only contain"
                               " English letters, numbers, and the"
                               " following punctuation characters:"
                               " - . , ' ( )"))
        elif name in self.context.keys():
            raise ValueError(_("Schema with this name already exists."))

    def schema(self):
        if hasattr(self, 'dfschema'):
            return self.dfschema
        return None

    def do_POST(self, request):
        self.name_widget.update(request)

        if self.name_widget.value is None:
            self.name_widget.value = 'default'
            self.name_widget.raw_value = 'default'

        self.model_error = None

        if 'ADDFIELD' in request.args:
            if self.newlabel_widget is None:
                self.error = _("Please specify a label for the new field")
            self.dfschema = self._buildSchema()
            return self.do_GET(request)

        if 'CREATE' in request.args:
            self.dfschema = self._buildSchema()
            service = getDynamicFacetSchemaService(self.context)
            service[self.name_widget.value] = self.dfschema
            request.appLog(_("Dynamic Facet schema %s created") %
                           getPath(self.context))
            return self.redirect("/dfschemas", request)

    def _buildSchema(self):
        """Build the dynamicfacet schema from the data contained in the
        request.
        """

        if self.schema():
            schema = self.dfschema
        else:
            schema = DynamicFacet()

        labels = self.request.args.get('newlabel', [])
        ftypes = self.request.args.get('newfield', [])

        for i in range(len(labels)):
            if labels[i]:
                name = labels[i].replace(' ','_').lower()
                value = None
                vocabulary = []

                if name in self.request.args:
                    value = self.request.args[name][0]

                if ftypes[i] in ('selection', 'multiselection'):
                    vocab_field = '%s_vocabulary' % name
                    if vocab_field in self.request.args:
                        vocabulary = self.request.args[vocab_field][0].split('\n')

                schema.addField(name, labels[i], ftypes[i], value, vocabulary)

        return schema


class PersonEditFacetView(View, AppObjectBreadcrumbsMixin):
    """Page for changing information about a person.

    Can be accessed at /persons/$id/edit-facet.html.
    """

    __used_for__ = IDynamicFacet
    authorization = ManagerAccess
    template = Template('www/person_edit-facet.pt')
    error = None
    duplicate_warning = False
    back = True

    def __init__(self, context):
        View.__init__(self, context)
        self.service = getDynamicFacetSchemaService(self.context)

    def do_GET(self, request):
        try:
            facet_name = self.request.args.get('facet', [None])[0]
            self.facet = self.service[facet_name]
            self.title = facet_name
        except KeyError:
            self.error = "Invalid facet specified"
        return View.do_GET(self, request)

    def do_POST(self, request):
        facet_name = self.request.args.get('facet', [None])[0]
        if 'SAVE' in request.args:
            facets = FacetManager(self.context).iterFacets()

            # Test for existance of the facet on this person
            if not [facet for facet in facets if facet.__name__ == facet_name]:
                self.createFacet(facet_name)

            self.updateFacet(facet_name)

            url = absoluteURL(request, self.context)
            return self.redirect(url, request)

        return self.do_GET(request)

    def createFacet(self, facet_name):
        facet = self.service[facet_name].cloneEmpty()
        FacetManager(self.context).setFacet(facet, self.context, facet_name)

    def updateFacet(self, facet_name):
        facet = FacetManager(self.context).facetByName(facet_name)
        for field in facet.fields:
            if field.name in self.request.args:
                field.value = self.request.args[field.name][0]

