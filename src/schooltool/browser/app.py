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

import datetime
from cStringIO import StringIO

from schooltool.app import create_application
from schooltool.browser import ToplevelBreadcrumbsMixin
from schooltool.browser import ContainerBreadcrumbsMixin
from schooltool.browser import View, Template, StaticFile
from schooltool.browser import absoluteURL
from schooltool.browser import notFoundPage
from schooltool.browser import session_time_limit
from schooltool.browser import valid_name
from schooltool.browser.applog import ApplicationLogView
from schooltool.browser.auth import ManagerAccess
from schooltool.browser.auth import PublicAccess, AuthenticatedAccess
from schooltool.browser.csv import CSVImportView
from schooltool.browser.model import PersonView, GroupView, ResourceView
from schooltool.browser.timetable import NewTimePeriodView
from schooltool.browser.timetable import TimePeriodServiceView
from schooltool.browser.timetable import TimetableSchemaServiceView
from schooltool.browser.timetable import TimetableSchemaWizard
from schooltool.browser.widgets import TextWidget, PasswordWidget
from schooltool.browser.widgets import TextAreaWidget
from schooltool.browser.widgets import dateParser, intParser
from schooltool.common import to_unicode
from schooltool.component import FacetManager
from schooltool.component import getPath, traverse
from schooltool.component import getTicketService
from schooltool.interfaces import IApplication, IApplicationObjectContainer
from schooltool.interfaces import IPerson, AuthenticationError
from schooltool.membership import Membership
from schooltool.rest.app import AvailabilityQueryView
from schooltool.rest.infofacets import resize_photo, canonical_photo_size
from schooltool.translation import ugettext as _

__metaclass__ = type


class RootView(View):
    """View for the web application root.

    Presents a login page.  Redirects to the start page after a successful
    login.

    Sublocations found at / are

        schooltool.css      the stylesheet
        logout              logout page (accessing it logs you out)
        start               a person's start page
        persons/id          person information pages
        groups/id           group information pages

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
            return self.redirect('/start', request)
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
            ticket = ticketService.newTicket((username, password),
                                             session_time_limit)
            request.addCookie('auth', ticket)
            if 'url' in request.args:
                url = request.args['url'][0]
            else:
                url = '/start'
            return self.redirect(url, request)

    def _traverse(self, name, request):
        if name == 'persons':
            return PersonContainerView(self.context['persons'])
        elif name == 'groups':
            return GroupContainerView(self.context['groups'])
        elif name == 'resources':
            return ResourceContainerView(self.context['resources'])
        elif name == 'schooltool.css':
            return StaticFile('www/schooltool.css', 'text/css')
        elif name == 'logo.png':
            return StaticFile(_('www/logo.png'), 'image/png')
        elif name == 'person.png':
            return StaticFile('www/user2.png', 'image/png')
        elif name == 'group.png':
            return StaticFile('www/group2.png', 'image/png')
        elif name == 'resource.png':
            return StaticFile('www/resource2.png', 'image/png')
        elif name == 'logout':
            return LogoutView(self.context)
        elif name == 'reset_db.html':
            return DatabaseResetView(self.context)
        elif name == 'start':
            return StartView(request.authenticated_user)
        elif name == 'applog':
            return ApplicationLogView(self.context)
        elif name == 'csvimport.html':
            return CSVImportView(self.context)
        elif name == 'busysearch':
            return BusySearchView(self.context)
        elif name == 'ttschemas':
            return TimetableSchemaServiceView(
                self.context.timetableSchemaService)
        elif name == 'newttschema':
            return TimetableSchemaWizard(self.context.timetableSchemaService)
        elif name == 'time-periods':
            return TimePeriodServiceView(self.context.timePeriodService)
        elif name == 'newtimeperiod':
            return NewTimePeriodView(self.context.timePeriodService)
        raise KeyError(name)


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

    def _processForm(self, request):
        """Process and form data, return True if there were no errors."""
        widgets = [self.first_name_widget, self.last_name_widget,
                   self.username_widget, self.password_widget,
                   self.confirm_password_widget, self.dob_widget,
                   self.comment_widget]
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

        # TODO: ensure uniqueness of (first_name, last_name)

        person = self._addUser(self.username_widget.value,
                               self.password_widget.value)
        if person is None:
            # Unlikely, but possible
            self.username_widget.error = _("User with this username "
                                           " already exists.")
            return self.do_GET(request)
        self._setUserInfo(person, self.first_name_widget.value,
                          self.last_name_widget.value, self.dob_widget.value,
                          self.comment_widget.value)
        self._setUserPhoto(person, photo)
        url = absoluteURL(request, person, 'edit.html')
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

    title = _("Add object") # should be overridden by subclasses
    parent = None           # can be set by subclasses

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

    title = _("Add group")

    def _processExtraFormFields(self, request):
        self.parent = None
        parent_id = request.args.get('parentgroup', [None])[0]
        if parent_id:
            try:
                self.parent = self.context[parent_id]
            except KeyError:
                pass
            else:
                self.title = (_("Add group (a subgroup of %s)")
                              % self.parent.title)


class ResourceAddView(ObjectAddView):
    """View for adding resources (/resources/add.html)."""

    title = _("Add resource")

    template = Template('www/resource_add.pt')

    prev_location = False

    def _processExtraFormFields(self, request):
        self.parent = None
        self.prev_location = False
        if 'location' in request.args:
            self.prev_location = True
            self.parent = traverse(self.context, '/groups/locations')


class ObjectContainerView(View, ContainerBreadcrumbsMixin):
    """View for an ApplicationObjectContainer.

    Accessing this location returns a 404 Not Found response.

    Traversing 'add.html' returns an instance of add_view on the container,
    traversing with an object's id returns an instance of obj_view on
    the object.

    XXX this implies that an object with the id 'add.html' is inaccessible.
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
    index_title = _("Person index")
    add_title = _("Add a new person")


class GroupContainerView(ObjectContainerView):
    """View for traversing to groups (/groups)."""

    add_view = GroupAddView
    obj_view = GroupView
    index_title = _("Group index")
    add_title = _("Add a new person")


class ResourceContainerView(ObjectContainerView):
    """View for traversing to resources (/resources)."""

    add_view = ResourceAddView
    obj_view = ResourceView
    index_title = _("Resource index")
    add_title = _("Add a new resource")


class BusySearchView(View, AvailabilityQueryView, ToplevelBreadcrumbsMixin):
    """View for resource search (/busysearch)."""

    # Only one methods from AvailabilityQueryView is used:
    #   update

    __used_for__ = IApplication

    authorization = AuthenticatedAccess

    template = Template("www/busysearch.pt")

    defaultDur = 30

    def __init__(self, context):
        View.__init__(self, context)
        self.first_widget = TextWidget('first', _('First'), parser=dateParser,
                                       value=datetime.date.today())
        self.last_widget = TextWidget('last', _('Last'), parser=dateParser,
                                      value=datetime.date.today())
        self.duration_widget = TextWidget('duration', _('Duration'),
                                          unit=_('min.'), parser=intParser,
                                          validator=self.duration_validator,
                                          value=self.defaultDur)

    def duration_validator(value):
        """Check if duration is acceptable.

          >>> duration_validator = BusySearchView.duration_validator
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
    duration_validator = staticmethod(duration_validator)

    def do_GET(self, request):
        self.status = None
        self.can_search = False
        if 'SUBMIT' in request.args:
            self.first_widget.update(request)
            self.last_widget.update(request)
            self.duration_widget.update(request)
            self.first_widget.require()
            self.last_widget.require()
            self.duration_widget.require()
            error = (self.first_widget.error or self.last_widget.error or
                     self.duration_widget.error)
            if not error:
                self.status = self.update()
                self.can_search = self.status is None
        return View.do_GET(self, request)

    def today(self):
        return str(datetime.date.today())

    def allResources(self):
        """Return a list of resources"""
        resources = traverse(self.context, '/resources')
        result = [(obj.title, obj) for obj in resources.itervalues()]
        result.sort()
        return [obj for title, obj in result]

    def listResources(self):
        """Return sorted results of the availability query."""
        resources = [(r.title, r) for r in self.resources]
        resources.sort()
        results = []
        for title, resource in resources:
            slots = resource.getFreeIntervals(self.first, self.last,
                                              self.hours, self.duration)
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
                     })
            results.append({'title': title,
                            'href': absoluteURL(self.request, resource),
                            'slots': res_slots})
        return results


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

