#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Web-application views for the schooltool.app objects.

$Id$
"""

import sets
import datetime
from cStringIO import StringIO

from zope.app.traversing.interfaces import TraversalError
from zope.app.traversing.api import traverse, getPath

from schooltool.app import create_application
from schooltool.uris import URIOccupies
from schooltool.browser import ToplevelBreadcrumbsMixin
from schooltool.browser import ContainerBreadcrumbsMixin
from schooltool.browser import View, Template, StaticFile
from schooltool.browser import absoluteURL
from schooltool.browser import session_time_limit
from schooltool.browser import valid_name
from schooltool.browser.applog import ApplicationLogView
from schooltool.browser.auth import ManagerAccess
from schooltool.browser.auth import PublicAccess, AuthenticatedAccess
from schooltool.browser.csvimport import CSVImportView, TimetableCSVImportView
from schooltool.browser.model import PersonView, GroupView, ResourceView
from schooltool.browser.model import NoteView, ResidenceView
from schooltool.browser.model import app_object_list
from schooltool.browser.timetable import NewTimePeriodView
from schooltool.browser.timetable import TimePeriodServiceView
from schooltool.browser.timetable import TimetableSchemaServiceView
from schooltool.browser.timetable import TimetableSchemaWizard
from schooltool.browser.infofacet import DynamicFacetSchemaServiceView
from schooltool.browser.infofacet import DynamicFacetSchemaWizard
from schooltool.browser.widgets import TextWidget, PasswordWidget
from schooltool.browser.widgets import TextAreaWidget, SelectionWidget
from schooltool.browser.widgets import CheckboxWidget, MultiselectionWidget
from schooltool.browser.widgets import dateParser, intParser
from schooltool.browser.widgets import sequenceParser, sequenceFormatter
from schooltool.common import to_unicode
from schooltool.component import FacetManager
from schooltool.component import getRelatedObjects
from schooltool.component import getTicketService, getTimetableSchemaService
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IPerson, IResource, IGroup
from schooltool.interfaces import AuthenticationError
from schooltool.interfaces import IApplicationObject
from schooltool.interfaces import Everybody, ViewPermission
from schooltool.membership import Membership
from schooltool.guardian import Guardian
from schooltool.occupies import Occupies
from schooltool.noted import Noted
from schooltool.rest.model import delete_app_object
from schooltool.rest.infofacets import resize_photo, canonical_photo_size
from schooltool.translation import ugettext as _

__metaclass__ = type


class RootView(View):
    """View for the web application root.

    Presents a login page.  Redirects to the start page after a successful
    login.

    Sublocations found at / are (see `_traverse` for a full and up-to-date
    list):

        start               The authenticated user's start page.
        logout              Logout page (accessing it logs you out).

        persons             Person index.
        groups              Group index.
        resources           Resource index.
        notes               Note index.

        busysearch          Resource busy search and booking.

        ttschemas           List of timetable schemas.
        newttschema         Form to create a new timetable schema.
        time-periods        List of time periods.
        newtimeperiod       Form to create a new time period.

        options.html        Application options form.
        reset_db.html       Database clearing form.
        cvsimport.html      CVS import form
        delete.html         Application object deletion form.

        applog              Application audit log.

        schooltool.css      the stylesheet
        *.png               some images

    """

    __used_for__ = IApplication

    authorization = PublicAccess

    template = Template("www/root.pt")

    error = False
    username = ''

    def do_GET(self, request):
        logged_in = request.authenticated_user is not None
        forbidden = 'forbidden' in request.args
        community = traverse(self.context, '/groups/community')
        if logged_in and not forbidden:
            return self.redirect('/persons/'
                                 + request.authenticated_user.__name__
                                 + '/calendar', request)
        elif (community.calendar.acl.allows(Everybody, ViewPermission)
                and not forbidden):
            return self.redirect('/groups/community/calendar/daily.html',
                                 request)
        else:
            return self.redirect('/login', request)

    def _traverse(self, name, request):
        if name == 'persons':
            return PersonContainerView(self.context['persons'])
        elif name == 'groups':
            return GroupContainerView(self.context['groups'])
        elif name == 'resources':
            return ResourceContainerView(self.context['resources'])
        elif name == 'notes':
            return NoteContainerView(self.context['notes'])
        elif name == 'residences':
            return ResidenceContainerView(self.context['residences'])
        elif name == 'schooltool.css':
            return StaticFile('www/schooltool.css', 'text/css')
        elif name == 'layout.css':
            return StaticFile('www/layout.css', 'text/css')
        elif name == 'style.css':
            return StaticFile('www/style.css', 'text/css')
        elif name == 'schoolbell.js':
            return StaticFile('www/schoolbell.js', 'text/javascript')
        elif name == 'logo.png':
            return StaticFile(_('www/logo.png'), 'image/png')
        elif name == 'person.png':
            return StaticFile('www/user2.png', 'image/png')
        elif name == 'group.png':
            return StaticFile('www/group2.png', 'image/png')
        elif name == 'resource.png':
            return StaticFile('www/resource2.png', 'image/png')
        elif name == 'meeting.png':
            return StaticFile('www/meeting.png', 'image/png')
        elif name == 'booking.png':
            return StaticFile('www/booking.png', 'image/png')
        elif name == 'calendar.png':
            return StaticFile('www/calendar.png', 'image/png')
        elif name == 'information.png':
            return StaticFile('www/information.png', 'image/png')
        elif name == 'delete.png':
            return StaticFile('www/delete.png', 'image/png')
        elif name == 'day.png':
            return StaticFile('www/day.png', 'image/png')
        elif name == 'week.png':
            return StaticFile('www/week.png', 'image/png')
        elif name == 'month.png':
            return StaticFile('www/month.png', 'image/png')
        elif name == 'year.png':
            return StaticFile('www/year.png', 'image/png')
        elif name == 'previous.png':
            return StaticFile('www/previous.png', 'image/png')
        elif name == 'current.png':
            return StaticFile('www/current.png', 'image/png')
        elif name == 'next.png':
            return StaticFile('www/next.png', 'image/png')
        elif name == 'logout':
            return LogoutView(self.context)
        elif name == 'login':
            return LoginView(self.context)
        elif name == 'delete.html':
            return DeleteView(self.context)
        elif name == 'reset_db.html':
            return DatabaseResetView(self.context)
        elif name == 'options.html':
            return OptionsView(self.context)
        elif name == 'start':
            return StartView(request.authenticated_user)
        elif name == 'applog':
            return ApplicationLogView(self.context)
        elif name == 'csvimport.html':
            return CSVImportView(self.context)
        elif name == 'tt_csvimport.html':
            return TimetableCSVImportView(self.context)
        elif name == 'busysearch':
            return BusySearchView(self.context)
        elif name == 'busysearch-popup':
            return BusySearchViewPopUp(self.context)
        elif name == 'ttschemas':
            return TimetableSchemaServiceView(
                self.context.timetableSchemaService)
        elif name == 'newttschema':
            return TimetableSchemaWizard(self.context.timetableSchemaService)
        elif name == 'time-periods':
            return TimePeriodServiceView(self.context.timePeriodService)
        elif name == 'newtimeperiod':
            return NewTimePeriodView(self.context.timePeriodService)
        elif name == 'dfschemas':
            return DynamicFacetSchemaServiceView(
                self.context.dynamicFacetSchemaService)
        elif name == 'newdfschema':
            return DynamicFacetSchemaWizard(self.context.dynamicFacetSchemaService)
        raise KeyError(name)


class LoginView(View):
    """View for /login
    """

    __used_for__ = IApplication

    authorization = PublicAccess

    template = Template("www/login.pt")

    error = False
    username = ''

    def do_GET(self, request):
        logged_in = request.authenticated_user is not None
        forbidden = 'forbidden' in request.args
        if logged_in and not forbidden:
            return self.redirect('/persons/'
                                 + request.authenticated_user.__name__
                                 + '/calendar', request)
        else:
            return View.do_GET(self, request)

    def do_POST(self, request):
        username = request.args['username'][0]
        password = request.args['password'][0]

        try:
            request.authenticate(username, password)
        except AuthenticationError:
            self.error = True
            self.username = username
            return self.do_GET(request)
        else:
            ticketService = getTicketService(self.context)
            if 'remember' in request.args:
                ticket = ticketService.newTicket((username, password))
            else:
                ticket = ticketService.newTicket((username, password),
                                                  session_time_limit)
            request.addCookie('auth', ticket, path='/')
            if 'url' in request.args:
                url = request.args['url'][0]
            else:
                url = ('/persons/'
                        + request.authenticated_user.__name__
                        + '/calendar')
            return self.redirect(url, request)


class LogoutView(View):
    """View for /logout.

    Accessing this URL causes the authenticated user to be logged out and
    redirected back to the login page.
    """

    __used_for__ = IApplication

    authorization = PublicAccess

    def do_GET(self, request):
        auth_cookie = request.getCookie('auth')
        getTicketService(self.context).expire(auth_cookie)
        return self.redirect('/', request)


class StartView(View, ToplevelBreadcrumbsMixin):
    """Start page (/start).

    This is where the user is redirected after logging in.  The start page
    displays common actions.
    """

    __used_for__ = IPerson

    authorization = AuthenticatedAccess

    template = Template("www/start.pt")

    def person_url(self):
        return absoluteURL(self.request, self.context)


class PersonAddView(View, ToplevelBreadcrumbsMixin):
    """A view for adding persons."""

    __used_for__ = IApplicationObjectContainer

    authorization = ManagerAccess

    template = Template('www/person_add.pt')

    error = None
    duplicate_warning = False

    def __init__(self, context):
        View.__init__(self, context)
        self.first_name_widget = TextWidget('first_name', _('First name'))
        self.last_name_widget = TextWidget('last_name', _('Last name'))
        self.username_widget = TextWidget('optional_username', _('Username'),
                                          validator=self.name_validator)
        self.password_widget = PasswordWidget('optional_password',
                                              _('Password'))
        self.confirm_password_widget = PasswordWidget('confirm_password',
                                                      _('Confirm password'))
        self.dob_widget = TextWidget('date_of_birth', _('Birth date'),
                                     unit=_('(YYYY-MM-DD)'), parser=dateParser)
        self.comment_widget = TextAreaWidget('comment', _('Comment'))
        self.groups_widget = MultiselectionWidget('groups',
                                    _('Groups'),
                                    self._allGroups(),
                                    parser=self._parseGroups,
                                    formatter=sequenceFormatter(getPath))
        self.groups_widget.size = 5

    def name_validator(self, username):
        """Validate username and raise ValueError if it is invalid."""
        if not username:
            return
        if not valid_name(username):
            raise ValueError(_("Username can only contain English letters,"
                               " numbers, and the following punctuation"
                               " characters: - . , ' ( )"))
        elif username in self.context.keys():
            # This check is racy, but that is fixed in _addUser
            raise ValueError(_("User with this username already exists."))

    def _allGroups(self):
        """Return a sorted list of all groups."""
        groups = traverse(self.context, '/groups')
        result = [(obj.title, obj) for obj in groups.itervalues()]
        result.sort()
        return [(obj, title) for title, obj in result]

    def _parseGroups(self, raw_value):
        """Parse a list of paths and return a list of groups."""
        groups_container = traverse(self.context, '/groups')
        groups = []
        for path in raw_value:
            try:
                group = traverse(groups_container, path)
            except TraversalError:
                pass
            else:
                if IGroup.providedBy(group):
                    groups.append(group)
        return groups

    def _processForm(self, request):
        """Process and form data, return True if there were no errors."""
        widgets = [self.first_name_widget, self.last_name_widget,
                   self.username_widget, self.password_widget,
                   self.confirm_password_widget, self.dob_widget,
                   self.comment_widget, self.groups_widget]
        for widget in widgets:
            widget.update(request)

        self.first_name_widget.require()
        self.last_name_widget.require()

        if 'CONFIRM' not in request.args:
            full_name = (self.first_name_widget.value,
                         self.last_name_widget.value)
            for otheruser in self.context.itervalues():
                infofacet = FacetManager(otheruser).facetByName('person_info')
                if (infofacet.first_name, infofacet.last_name) == full_name:
                    self.error = _("User with this name already exists.")
                    self.duplicate_warning = True
                    break

        if (not self.password_widget.error and
            not self.confirm_password_widget.error and
            self.password_widget.value != self.confirm_password_widget.value):
            self.confirm_password_widget.error = _("Passwords do not match.")

        if self.error:
            return False
        for widget in widgets:
            if widget.error:
                return False
        return True

    def _processPhoto(self, request):
        """Extract and resize photo, if uploaded.

        May set self.error.
        """
        photo = request.args.get('photo', [None])[0]
        if photo:
            try:
                photo = resize_photo(StringIO(photo), canonical_photo_size)
            except IOError:
                self.error = _('Invalid photo')
                photo = None
        return photo

    def do_POST(self, request):
        """Process form submission."""
        if 'CANCEL' in request.args:
            return self.do_GET(request)

        if not self._processForm(request):
            return self.do_GET(request)

        photo = self._processPhoto(request)
        if self.error:
            return self.do_GET(request)

        person = self._addUser(self.username_widget.value,
                               self.password_widget.value)

        if request.args.get('ward',[None])[0]:
            # When we create a person to be part of the guardian relationship
            # we pass a 'ward' request varible to link it to.
            wid = to_unicode(request.args.get('ward',[None])[0])
            new_guardian = traverse(self.context, '/persons/' + wid)
            # XXX traverse might raise TraversalError
            Guardian(custodian=new_guardian, ward=person)

        if person is None:
            # Unlikely, but possible
            self.username_widget.error = _("User with this username "
                                           " already exists.")
            return self.do_GET(request)
        self._setUserInfo(person, self.first_name_widget.value,
                          self.last_name_widget.value, self.dob_widget.value,
                          self.comment_widget.value)
        self._setUserPhoto(person, photo)

        self._setUserGroups(person, self.groups_widget.value)

        url = absoluteURL(request, person)
        return self.redirect(url, request)

    def _addUser(self, username=None, password=None):
        """Add a new user."""
        username = username and str(username) or None
        password = password and str(password) or None
        try:
            person = self.context.new(username, title=username)
        except KeyError:
            return None
        if not username:
            person.title = person.__name__
        person.setPassword(password)
        # We could say 'Person created', but we want consistency
        # (wart-compatibility in this case).
        self.request.appLog(_("Object %s of type %s created") %
                            (getPath(person), person.__class__.__name__))
        return person

    def _setUserInfo(self, person, first_name, last_name, dob, comment):
        """Update user's personal information."""
        infofacet = FacetManager(person).facetByName('person_info')
        infofacet.first_name = first_name
        infofacet.last_name = last_name
        infofacet.date_of_birth = dob
        infofacet.comment = comment
        self.request.appLog(_("Person info updated on %s (%s)") %
                            (person.title, getPath(person)))

    def _setUserPhoto(self, person, photo=None):
        """Update user's photo."""
        if not photo:
            return
        infofacet = FacetManager(person).facetByName('person_info')
        infofacet.photo = photo
        self.request.appLog(_("Photo added on %s (%s)") %
                            (person.title, getPath(person)))

    def _setUserGroups(self, person, groups):
        """Add user to groups."""
        if groups is not None:
            for group in groups:
                # XXX This will not work for SchoolTool
                # Look how 
                # schooltool.browser.model.GroupEditView.createRelationship
                # does it.
                Membership(group=group, member=person)
                self.request.appLog(
                        _("Relationship 'Membership' between %s and %s created")
                        % (getPath(person), getPath(group)))


class ObjectAddView(View, ToplevelBreadcrumbsMixin):
    """A view for adding a new object (usually a group or a resource)."""

    __used_for__ = IApplicationObjectContainer

    authorization = ManagerAccess

    # Subclasses can override the template attribute and still access the
    # original one as object_add_template if they want to use METAL macros
    # defined therein.
    object_add_template = Template('www/object_add.pt')
    template = object_add_template

    error = u""
    prev_name = u""
    prev_title = u""
    duplicate_warning = False

    # Subclasses should override the title attribute
    title = property(lambda self: _("Add object"))

    # Subclasses can set the parent attribute
    parent = None

    def do_GET(self, request):
        self._processExtraFormFields(request)
        return View.do_GET(self, request)

    def do_POST(self, request):
        self._processExtraFormFields(request)

        if 'CANCEL' in self.request.args:
            # Just show the form without any data.
            return self.do_GET(request)

        name = request.args['name'][0]

        if name == '':
            name = None
        else:
            if not valid_name(name):
                self.error = _("Invalid identifier")
                return self.do_GET(request)
        self.prev_name = name

        try:
            title = to_unicode(request.args['title'][0])
        except UnicodeError:
            self.error = _("Invalid UTF-8 data.")
            return self.do_GET(request)

        self.prev_title = title
        if not title:
            self.error = _("Title should not be empty.")
            return self.do_GET(request)
        add_anyway = 'CONFIRM' in self.request.args
        if self._titleAlreadyUsed(title) and not add_anyway:
            self.error = _("There is an object with this title already.")
            self.duplicate_warning = True
            return self.do_GET(request)

        try:
            obj = self.context.new(name, title=title)
        except KeyError:
            self.error = _('Identifier already taken')
            return self.do_GET(request)

        request.appLog(_("Object %s of type %s created") %
                       (getPath(obj), obj.__class__.__name__))

        if self.parent is not None:
            Membership(group=self.parent, member=obj)
            self.request.appLog(
                    _("Relationship 'Membership' between %s and %s created")
                    % (getPath(obj), getPath(self.parent)))

        url = absoluteURL(request, obj)
        return self.redirect(url, request)

    def _titleAlreadyUsed(self, title):
        """Check if there's already an object with this title."""
        for obj in self.context.itervalues():
            if obj.title == title:
                return True
        return False

    def _processExtraFormFields(self, request):
        """Process additional form fields (a hook for subclasses).

        It is assumed that no errors will occur during the extra processing.
        """
        pass


class GroupAddView(ObjectAddView):
    """View for adding groups (/groups/add.html)."""

    title = property(lambda self: self._title)
    _title = "Add group" # translation happens in _processExtraFormFields

    def _processExtraFormFields(self, request):
        self._title = _("Add group")
        self.parent = None
        parent_id = request.args.get('parentgroup', [None])[0]
        if parent_id:
            try:
                self.parent = self.context[parent_id]
            except KeyError:
                pass
            else:
                self._title = (_("Add group (a subgroup of %s)")
                               % self.parent.title)


class ResourceAddView(ObjectAddView):
    """View for adding resources (/resources/add.html)."""

    title = property(lambda self: _("Add resource"))

    template = Template('www/resource_add.pt')

    prev_location = False

    def _processExtraFormFields(self, request):
        self.parent = None
        self.prev_location = False
        if 'location' in request.args:
            self.prev_location = True
            self.parent = traverse(self.context, '/groups/locations')


class NoteAddView(View):
    """View for adding notes."""

    title = property(lambda self: _("Add note"))

    error = u""

    relname = property(lambda self: _('Noted'))

    template = Template('www/note_add.pt')

    authorization = AuthenticatedAccess

    errormessage = property(lambda self: _("Cannot add %(note)s to %(this)s"))

    def __init__(self, context):
        View.__init__(self, context)
        self.title_widget = TextWidget('title', _('Title'))
        self.body_widget = TextAreaWidget('body', _('Note'))

    def do_POST(self, request):

        if 'CANCEL' in self.request.args:
            # Just show the form without any data.
            cancelpath = self.request.args['toadd'][0]
            nobj = traverse(self.context, cancelpath)
            # XXX traverse might raise TraversalError
            url = absoluteURL(request, nobj)
            return self.redirect(url, request)

        widgets = [self.title_widget, self.body_widget]

        name = None

        for widget in widgets:
            widget.update(request)

        for widget in widgets:
            widget.require()

        if self.title_widget.error or self.body_widget.error:
            return self.do_GET(request)

        obj = self.context.new(name,
                title = self.title_widget.value,
                body = self.body_widget.value,
                owner = request.authenticated_user)

        request.appLog(_("Object %s of type %s created") %
                       (getPath(obj), obj.__class__.__name__))

        paths = filter(None, request.args.get("toadd", []))
        for path in paths:
            pobj = traverse(self.context, path)
            # XXX traverse might raise TraversalError
            try:
                Noted(notation=obj, notandum=pobj)
            except:
                return self.errormessage % {'note': pobj.title,
                                            'this': obj.title}
            request.appLog(_("Relationship '%s' between %s and %s created")
                           % (self.relname, getPath(obj),
                              getPath(pobj)))

        nexturl = absoluteURL(request, pobj)

        return self.redirect(nexturl, request)


class ResidenceAddView(ObjectAddView):
    """View for adding residences """

    title = property(lambda self: _("Add residence"))

    error = u""

    relname = property(lambda self: _("Occupies"))

    template = Template('www/residence_add.pt')

    authorization = ManagerAccess

    search_results = []
    related_person = []

    def __init__(self, context):
        View.__init__(self, context)
        self.search_widget = TextWidget('search', _('Search'))
        self.title_widget = TextWidget('title', _('Title'))
        self.country_widget = TextWidget('country', _('Country'))
        self.postcode_widget = TextWidget('postcode', _('Postcode'))
        self.district_widget = TextWidget('district', _('District'))
        self.town_widget = TextWidget('town', _('Town'))
        self.streetNr_widget = TextWidget('streetNr', _('Street No'))
        self.thoroughfareName_widget = TextWidget('thoroughfareName',
                _('Thoroughfare Name'))

    def do_POST(self, request):
        """"""
        self.related_person = to_unicode(request.args.get('toadd', [None])[0])

        if 'CANCEL' in request.args:
            # Just show the form without any data.
            return self.do_GET(request)

        if 'SEARCH' in request.args:
            self.search_widget.update(request)
            self.search_results = self.doSearch(request)
            return self.do_GET(request)

        if 'RELATE' in request.args:
            rpath = to_unicode(request.args.get('residence', [None])[0])
            residence = traverse(self.context, rpath)
            # XXX traverse might raise TraversalError

            paths = filter(None, to_unicode(request.args.get("toadd", [])))
            for path in paths:
                pobj = traverse(self.context, path)
                # XXX traverse might raise TraversalError
                try:
                    Occupies(residence=residence, resides=pobj)
                except ValueError:
                    return self.errormessage % {'other': pobj.title,
                                                'this': residence.title}
                request.appLog(_("Relationship '%s' between %s and %s created")
                               % (self.relname, getPath(residence),
                                  getPath(pobj)))

            nexturl = absoluteURL(request, pobj)
            return self.redirect(nexturl, request)

        widgets = [self.title_widget, self.country_widget,
                   self.postcode_widget, self.district_widget,
                   self.town_widget, self.streetNr_widget,
                   self.thoroughfareName_widget]

        name = None

        for widget in widgets:
            widget.update(request)

        for widget in widgets:
            if widget.error:
                return self.do_GET(request)

        obj = self.context.new(name, title=self.title_widget.value,
                country=self.country_widget.value)

        info = obj.info()

        info.postcode = self.postcode_widget.value
        info.district = self.district_widget.value
        info.town = self.town_widget.value
        info.streetNr = self.streetNr_widget.value
        info.thoroughfareName = self.thoroughfareName_widget.value

        for residence in getRelatedObjects(obj, URIOccupies):
            if obj == residence:
                self.error = _("This residence already exists in the system")
                return self.do_GET(request)


        request.appLog(_("Object %s of type %s created") %
                       (getPath(obj), obj.__class__.__name__))

        paths = filter(None, request.args.get("toadd", []))
        for path in paths:
            pobj = traverse(self.context, path)
            # XXX traverse might raise TraversalError
            try:
                Occupies(residence=obj, resides=pobj)
            except ValueError:
                return self.errormessage % {'other': pobj.title,
                                            'this': obj.title}
            request.appLog(_("Relationship '%s' between %s and %s created")
                           % (self.relname, getPath(obj),
                              getPath(pobj)))

        nexturl = absoluteURL(request, pobj)
        return self.redirect(nexturl, request)

    def doSearch(self, request):
        results = []
        val = self.search_widget.value
        for residence in self.context.keys():
            # This could be a little less ugly
            if self.context[residence].contains(val):
                results.append(self.context[residence])

        return results


class ObjectContainerView(View, ContainerBreadcrumbsMixin):
    """View for an ApplicationObjectContainer.

    Accessing this location returns a 404 Not Found response.

    Traversing 'add.html' returns an instance of add_view on the container,
    traversing with an object's id returns an instance of obj_view on
    the object.

    Note: this implies that an object with the id 'add.html' is inaccessible.
    """

    __used_for__ = IApplicationObjectContainer

    authorization = PublicAccess

    template = Template('www/container.pt')

    # Must be overridden by actual subclasses.
    add_view = None     # The add view class
    obj_view = None     # The object view class
    index_title = ""    # The title of the container index view
    add_title = ""      # The title of the link to add a new object

    def _traverse(self, name, request):
        if name == 'add.html':
            return self.add_view(self.context)
        else:
            return self.obj_view(self.context[name])

    def sortedObjects(self):
        """Return a list of contained objects sorted by title."""
        objs = list(self.context.itervalues())
        objs.sort(lambda x, y: cmp(x.title, y.title))
        return objs


class PersonContainerView(ObjectContainerView):
    """View for traversing to persons (/persons)."""

    add_view = PersonAddView
    obj_view = PersonView
    index_title = property(lambda self: _("Person index"))
    add_title = property(lambda self: _("Add a new person"))


class GroupContainerView(ObjectContainerView):
    """View for traversing to groups (/groups)."""

    add_view = GroupAddView
    obj_view = GroupView
    index_title = property(lambda self: _("Group index"))
    add_title = property(lambda self: _("Add a new group"))


class ResourceContainerView(ObjectContainerView):
    """View for traversing to resources (/resources)."""

    add_view = ResourceAddView
    obj_view = ResourceView
    index_title = property(lambda self: _("Resource index"))
    add_title = property(lambda self: _("Add a new resource"))


class NoteContainerView(ObjectContainerView):
    """View for traversing to notes (/notes)."""

    template = Template('www/note_container.pt')

    add_view = NoteAddView
    obj_view = NoteView
    index_title = property(lambda self: _("Notes"))
    add_title = property(lambda self: _("Add a new note"))


class ResidenceContainerView(ObjectContainerView):
    """View for traversing to residences (/residences)."""

    template = Template('www/residence_container.pt')
    add_view = ResidenceAddView
    obj_view = ResidenceView
    index_title = property(lambda self: _("Residences"))
    add_title = property(lambda self: _("Add a new residence"))


class BusySearchView(View, ToplevelBreadcrumbsMixin):
    """View for resource search (/busysearch)."""

    __used_for__ = IApplication

    authorization = AuthenticatedAccess

    template = Template("www/busysearch.pt")

    default_duration = 30 # minutes

    def __init__(self, context):
        View.__init__(self, context)
        self.resources_widget = MultiselectionWidget('resources',
                                    _('Resource'),
                                    self._allResources(),
                                    parser=self._parseResources,
                                    formatter=sequenceFormatter(getPath))
        self.resources_widget.size = 5
        self.hours_widget = MultiselectionWidget('hours', _('Hours'),
                                    [(hour, '%02d:00' % hour)
                                    for hour in range(24)],
                                    parser=sequenceParser(intParser))
        self.hours_widget.size = 5
        self.periods_widget = MultiselectionWidget('periods', _('Periods'),
                                    [(p, p) for p in self._allPeriods()])
        self.periods_widget.size = 5
        self.first_widget = TextWidget('first', _('First'), parser=dateParser,
                                    value=datetime.date.today())
        self.last_widget = TextWidget('last', _('Last'), parser=dateParser,
                                    value=datetime.date.today())
        self.duration_widget = TextWidget('duration', _('Duration'),
                                    unit=_('min.'), parser=intParser,
                                    validator=duration_validator,
                                    value=self.default_duration)

    def _allResources(self):
        """Return a sorted list of all resources."""
        resources = traverse(self.context, '/resources')
        result = [(obj.title, obj) for obj in resources.itervalues()]
        result.sort()
        return [(obj, title) for title, obj in result]

    def _allPeriods(self):
        """Return a sorted list of all timetable period IDs."""
        ttservice = getTimetableSchemaService(self.context)
        if ttservice.default_id is None:
            return []
        tt = ttservice.getDefault()
        periods = sets.Set()
        for day_id, day in tt.items():
            periods.update(day.periods)
        periods = list(periods)
        periods.sort()
        return periods

    def _parseResources(self, raw_value):
        """Parse a list of paths and return a list of resources."""
        resource_container = traverse(self.context, '/resources')
        resources = []
        for path in raw_value:
            try:
                resource = traverse(resource_container, path)
            except (TraversalError, UnicodeError):
                pass
            else:
                if IResource.providedBy(resource):
                    resources.append(resource)
        return resources

    def do_GET(self, request):
        """Process the request."""
        if 'HOURS' in self.request.args:
            self.by_periods = False
            request.addCookie('cal_periods', 'no', path='/')
        elif 'PERIODS' in self.request.args:
            self.by_periods = True
            request.addCookie('cal_periods', 'yes', path='/')
        else:
            self.by_periods = bool(request.getCookie('cal_periods') != 'no')
        self.searching = False
        if self.by_periods:
            widgets = [self.resources_widget, self.periods_widget,
                       self.first_widget, self.last_widget]
        else:
            widgets = [self.resources_widget, self.hours_widget,
                       self.first_widget, self.last_widget,
                       self.duration_widget]
        for widget in widgets:
            widget.update(request)
        if 'SEARCH' in request.args:
            self.first_widget.require()
            self.last_widget.require()
            if not self.by_periods:
                self.duration_widget.require()
            errors = False
            for widget in widgets:
                if widget.error:
                    errors = True
            if not errors:
                self._doSearch()
        return View.do_GET(self, request)

    def _doSearch(self):
        """Perform resource busy search."""
        self.searching = True
        resources = self.resources_widget.value
        if not resources:
            resource_container = traverse(self.context, '/resources')
            resources = list(resource_container.itervalues())
        if self.by_periods:
            periods = self.periods_widget.value
            if not periods:
                periods = self._allPeriods()
            self.results = self._queryByPeriods(resources, periods,
                                                self.first_widget.value,
                                                self.last_widget.value)
        else:
            if not self.hours_widget.value:
                hours = [(datetime.time(0), datetime.timedelta(hours=24))]
            else:
                hours = [(datetime.time(h), datetime.timedelta(hours=1))
                         for h in self.hours_widget.value]
            duration = datetime.timedelta(minutes=self.duration_widget.value)
            self.results = self._query(resources, hours,
                                       self.first_widget.value,
                                       self.last_widget.value, duration)

    def _query(self, resources, hours, first, last, min_duration):
        """Perform resource busy search."""
        resources = [(r.title, r) for r in resources]
        resources.sort()
        results = []
        for title, resource in resources:
            slots = resource.getFreeIntervals(first, last, hours, min_duration)
            if not slots:
                continue
            res_slots = []
            for start, duration in slots:
                mins = duration.days * 60 * 24 + duration.seconds // 60
                end = start + duration
                res_slots.append(
                    {'start': start.strftime("%Y-%m-%d %H:%M"),
                     'end': end.strftime("%Y-%m-%d %H:%M"),
                     'start_date': start.strftime("%Y-%m-%d"),
                     'start_time': start.strftime("%H:%M"),
                     'duration': mins,
                     'suggested_duration': self.duration_widget.value,
                     })
            results.append({'title': title,
                            'href': absoluteURL(self.request, resource),
                            'slots': res_slots})
        return results

    def _queryByPeriods(self, resources, periods, first, last):
        """Perform resource busy search."""
        resources = [(r.title, r) for r in resources]
        resources.sort()
        results = []
        for title, resource in resources:
            slots = resource.getFreePeriods(first, last, periods)
            if not slots:
                continue
            res_slots = []
            for start, duration, period in slots:
                mins = duration.days * 60 * 24 + duration.seconds // 60
                end = start + duration
                res_slots.append(
                    {'start': start.strftime("%Y-%m-%d %H:%M"),
                     'end': end.strftime("%Y-%m-%d %H:%M"),
                     'start_date': start.strftime("%Y-%m-%d"),
                     'start_time': start.strftime("%H:%M"),
                     'duration': mins,
                     'suggested_duration': mins,
                     'period': period,
                     })
            results.append({'title': title,
                            'href': absoluteURL(self.request, resource),
                            'slots': res_slots})
        return results


class BusySearchViewPopUp(BusySearchView):
    """Frameless version of BusySearch for popups"""

    template = Template("www/busysearch-popup.pt")


def duration_validator(value):
    """Check if duration is acceptable.

      >>> duration_validator(None)
      >>> duration_validator(42)
      >>> duration_validator(0)
      Traceback (most recent call last):
        ...
      ValueError: Duration cannot be zero.
      >>> duration_validator(-1)
      Traceback (most recent call last):
        ...
      ValueError: Duration cannot be negative.

    """
    if value is None:
        return
    if value < 0:
        raise ValueError(_("Duration cannot be negative."))
    if value == 0:
        raise ValueError(_("Duration cannot be zero."))


class DatabaseResetView(View, ToplevelBreadcrumbsMixin):
    """View for clearing the database (/reset_db.html)."""

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template('www/resetdb.pt')

    def do_POST(self, request):
        if 'confirm' in request.args:
            old_ticket_service = self.context.ticketService
            root = request.zodb_conn.root()
            rootname = request.site.rootName
            root[rootname] = create_application()
            self.context = root[rootname]
            self.context.ticketService = old_ticket_service
        return self.redirect('/', request)


class OptionsView(View, ToplevelBreadcrumbsMixin):

    __used_for__ = IApplication

    authorization = ManagerAccess

    title = property(lambda self: _("System options"))

    template = Template('www/options.pt')

    def __init__(self, context):
        View.__init__(self, context)

        def privacy_validator(value):
            if value not in ('private', 'public', 'hidden'):
                raise ValueError('Invalid value')

        self.new_event_privacy_widget = SelectionWidget(
            'new_event_privacy',
            _('Default visibility of new events to other users'),
            (('public', _('Public')),
             ('private',  _('Busy block')),
             ('hidden', _('Hidden'))),
            label_class="wide",
            value=self.context.new_event_privacy,
            validator=privacy_validator)

        self.timetable_privacy_widget = SelectionWidget(
            'timetable_privacy',
            _('Visibility of timetable events to other users'),
            (('public', _('Public')),
             ('private',  _('Busy block')),
             ('hidden', _('Hidden'))),
            label_class="wide",
            value=self.context.timetable_privacy,
            validator=privacy_validator)

        tts_service = getTimetableSchemaService(self.context)
        self.ttschemas = tts_service.keys()
        self.default_tts_widget = SelectionWidget(
            'default_tts',
            _('The default timetable schema'),
            [(k, k) for k in self.ttschemas],
            label_class="wide",
            value=tts_service.default_id)

        self.restrict_membership_widget = CheckboxWidget(
            'restrict_membership',
            _('Restrict group membership to  members of immediate parents.'),
            value=self.context.restrict_membership)

    def update(self, request):
        self.new_event_privacy_widget.update(request)
        self.timetable_privacy_widget.update(request)
        self.default_tts_widget.update(request)
        self.restrict_membership_widget.update(request)

    def do_POST(self, request):
        self.update(request)
        self.new_event_privacy_widget.require()
        self.timetable_privacy_widget.require()
        self.restrict_membership_widget.require()

        if (self.new_event_privacy_widget.error or
            self.timetable_privacy_widget.error or
            self.default_tts_widget.error):
            self.error = "There were errors"
            return self.do_GET(request)

        newpriv = self.new_event_privacy_widget.value
        ttpriv = self.timetable_privacy_widget.value
        restrict = self.restrict_membership_widget.value
        default_tts = self.default_tts_widget.value
        if newpriv is not None:
            self.context.new_event_privacy = newpriv
        if ttpriv is not None:
            self.context.timetable_privacy = ttpriv
        self.context.restrict_membership = restrict
        service = getTimetableSchemaService(self.context)
        if default_tts:
            service.default_id = default_tts

        return self.redirect('/', request)


class DeleteView(View, ToplevelBreadcrumbsMixin):
    """View for deleting application objects (/delete.html).

    The manager can perform a search for a person/group/resource whose title
    or ID contains a substring and then select one or more of the objects for
    deletion.  There is also a confirmation form.

    Deleting application objects is a serious matter that should only be done
    to undo mistakes such as accidentally entering the same person in the
    system twice.  When an object is deleted, all data associated with the
    object (relationships, timetables, calendars, resource bookings etc.) is
    gone forever.
    """

    __used_for__ = IApplication

    authorization = ManagerAccess

    template = Template("www/delete.pt")

    def __init__(self, context):
        View.__init__(self, context)
        self.search_widget = TextWidget('q', _('Search string'))

    def do_GET(self, request):
        """Process the request.

          1. Request is empty: present an empty search form and a SEARCH
             button.

          2. Request contains 'SEARCH': perform a search and present a list of
             results as checkboxes and a DELETE button.

          3. Request contains 'DELETE': show a confirmation form with CONFIRM
             and CANCEL buttons.

          4. Request contains 'CONFIRM': delete the selected objects and
             present an empty search form with an informational message.

          5. Request contains 'CANCEL': present an empty search form with an
             informational message.

        """
        self.status = None
        self.show_confirmation_form = 'DELETE' in request.args
        if 'SEARCH' in request.args:
            self.search_widget.update(request)
        if 'DELETE' in request.args and not self.selectedObjects():
            self.show_confirmation_form = False
            self.status = _('Nothing was selected.')
        if 'CANCEL' in request.args:
            self.status = _('Cancelled.')
        if 'CONFIRM' in request.args:
            status = []
            for info in self.selectedObjects():
                info['path'] = getPath(info['obj'])
                delete_app_object(info['obj'], request.appLog)
                status.append(_("Deleted %(title)s (%(path)s).") % info)
            self.status = "\n".join(status)
        return View.do_GET(self, request)

    def search(self):
        """Return application objects that match the search query.

        Returns None if there is no search query in the request.

        Returns a list of dicts (see `app_object_list`) with results if the
        query is present in the request.
        """
        if 'SEARCH' in self.request.args and not self.search_widget.error:
            return app_object_list(self._search(self.search_widget.value))
        else:
            return None

    def _search(self, q):
        """Find all application objects that match a given substring.

        Returns an iterator.

        Substring matching is case insensitive.  Substrings can match either
        in titles or in IDs.
        """
        q = q.lower()
        for container in 'persons', 'groups', 'resources':
            for obj in self.context[container].itervalues():
                if q in obj.__name__.lower() or q in obj.title.lower():
                    yield obj

    def selectedObjects(self):
        """Return application objects that were selected for deletion.

        Returns a list of dicts (see `app_object_list`) with results if the
        query is present in the request.
        """
        objs = []
        for path in self.request.args.get('path', []):
            try:
                obj = traverse(self.context, to_unicode(path))
                if IApplicationObject.providedBy(obj):
                    objs.append(obj)
            except (TraversalError, UnicodeError):
                pass
        return app_object_list(objs)

