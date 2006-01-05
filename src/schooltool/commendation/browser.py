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
"""Commendation Browser Views

$Id$
"""
__docformat__ = 'reStructuredText'
from zope.app import annotation
from zope.app import container
from zope.app import security
from zope.app import zapi
from zope.app.form.browser.add import AddView
from zope.app.publisher import browser

# Import the 'commendation' message id factory
from schooltool.commendation import interfaces, commendation
from schooltool.commendation.interfaces import _
from schooltool.app import app

# This is a simple view class that provides the information of a commendation
# in a user-readable format.
class CommendationDetails(object):
    """Commendation View Support"""

    # Decorators (the statement starting with '@') are a new feature in Python
    # 2.4. `property` is a function that creates a property from a set of
    # given functions. In this case the `title` method is used as the getter
    # function for the `title` property.
    @property
    def title(self):
        """Return the title of the commendation."""
        return self.context.title

    @property
    def description(self):
        """Return the description of the commendation."""
        return self.context.description

    @property
    def grantor(self):
        # Here we try to look up the title for a principal, whose id we saved.
        # The first step is to look up the closest authentication utility.
        auth = zapi.getUtility(security.interfaces.IAuthentication)

        # We then try to find the principal. When, during initialization of
        # the commendation, no principal was found, we stored the string
        # '<unknown>', which clearly is not a valid id and the lookup will
        # fail. The same is true for deleted users. In those cases we simply
        # return '<unknwon>' as the title of the grantor.
        try:
            principal = auth.getPrincipal(self.context.grantor)
        except security.interfaces.PrincipalLookupError:
            return _('<unknown>')
        return principal.title

    @property
    def date(self):
        # Date/times are stored as date, time or datetime objects. Thus, when
        # we want to display them, we need to convert them to a string. Since
        # SchoolTool is an international tool that is used in many regions of
        # the world, we need to ensure that we create the correct date/time
        # representation of the region of the user making the request.
        #
        # Zope 3 provides the utilities to do just that. Zope 3 determines the
        # locale of the user from the HTTP header information and stores the
        # locale object in the request. One of the locale's features is the
        # formatting of date/times and numbers. The code below formats only
        # the date in the locale's short format. Every locale has several
        # formats defined: short, medium, long, full.
        formatter = self.request.locale.dates.getFormatter('date', 'short')
        return formatter.format(self.context.date)


class CommendationAddView(AddView):
    """A view for adding a commendation."""

    __used_for__ = interfaces.IHaveCommendations

    # Form error message for the page template
    error = None

    # Override some fields of AddView
    schema = interfaces.ICommendation
    _factory = commendation.Commendation
    _arguments = ['title', 'description', 'scope']
    _keyword_arguments = []
    _set_before_add = []
    _set_after_add = []

    fieldNames = ['title', 'description', 'scope']

    def create(self, title, description, scope):
        """Create a commmendation from the collected information."""
        comm = self._factory(title, description, scope)
        return comm

    def add(self, comm):
        """Add ``comm`` to the object."""
        # Get the commendations adapter for the context object.
        commendations = interfaces.ICommendations(self.context)
        # It is often not necessary/desirable to ask the user for the name of
        # the component, since it is immaterial to the interaction of the user
        # with the application. For those scenarios Zope 3 provides a
        # component that will choose the name for you. It is simply an adapter
        # from the container to ``INameChooser`` and is used as shown below.
        chooser = container.interfaces.INameChooser(commendations)
        commendations[chooser.chooseName('', comm)] = comm
        return comm

    def update(self):
        """Process the form data and actions."""
        # We extend the ``update()`` method by supporting a cancel action,
        # which willbring us back to the context's default view.
        if 'CANCEL' in self.request:
            url = zapi.absoluteURL(self.context, self.request)
            return self.request.response.redirect(url)
        return super(CommendationAddView, self).update()

    def nextURL(self):
        """See zope.app.container.interfaces.IAdding"""
        return zapi.absoluteURL(self.context, self.request)


class CommendationsView(browser.BrowserView):
    """Commendations View

    A view that shows all commendations of an ``IHaveCommendations`` object.
    """

    def __init__(self, context, request):
        super(CommendationsView, self).__init__(context, request)
        # Since this is a view for ``IHaveCommendations`` components and not
        # for ``ICommendations`` components, we have to explicitely look up
        # the commendations and store them in a class attribute.
        commendations = interfaces.ICommendations(context)
        self.commendations = commendations.values()


class CommendationsOverview(browser.BrowserView):
    """SchoolTool Application Commendations Overview"""

    # Give each scope entry a value, so that we can easily compate them. The
    # higher the number, the more available/open/larger the scope.
    scopeDict = {'group': 0, 'school-wide': 1, 'community': 2,
                 'state': 3, 'national': 4, 'global': 5}

    def commendations(self):
        """Get all the available commendations after the filters were
        applied."""
        # Retrieve the filter options from the request.
        search_text = self.request.get('search_text', '')
        search_scope = self.scopeDict[
            self.request.get('search_scope', 'group')]

        # Get the SchoolTool application instance and access its annotations.
        stapp = app.getSchoolToolApplication()
        annotations = annotation.interfaces.IAnnotations(stapp)
        # A list comprehension that iterates through all the commendations and
        # applies the filter one-by-one.
        result = [
            c
            for c in annotations.get(commendation.CommendationsCacheKey, [])
            if ((search_text in c.title or search_text in c.description) and
                search_scope <= self.scopeDict[c.scope]) ]

        # Make sure that the commendations are sorted in reverse chronological
        # order.
        result.sort(lambda x, y: cmp(y.date, x.date))
        return result
