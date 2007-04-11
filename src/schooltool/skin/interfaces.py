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
"""
Interfaces for SchoolTool calendar browser views.

$Id$
"""
from zope.schema import Object, TextLine, Bool, URI
from zope.interface import Interface, Attribute

from schooltool.batching.interfaces import IBatch


class IBreadcrumbs(Interface):
    """An object providing breadcrumbs.

    This object will use the ``IBreadcrumbInfo`` adapter to get its
    information from each entry.
    """

    crumbs = Attribute('An iteratable of all breadcrumbs.')


class IBreadcrumbInfo(Interface):
    """Provides pieces of information about a breadcrumb."""

    name = TextLine(
        title=u'Name',
        description=u'The name of the breadcrumb.',
        required=True)

    url = URI(
        title=u'URL',
        description=u'The url of the breadcrumb.',
        required=True)

    active = Bool(
        title=u'Active',
        description=u'Tells whether the breadcrumb link should active.',
        required=True,
        default=True)


class IFilterWidget(Interface):

    def render():
        """Render the HTML representation of the filtering widget. """

    def filter(list):
        """Process the list leaving only those elements that match the query."""

    def active():
        """Returns True if there is at least one search parameter in the request."""

    def extra_url():
        """String that should be appended to the url to preserve query parameters."""


class ITableFormatter(Interface):

    batch = Object(schema=IBatch)

    filter_widget = Object(schema=IFilterWidget)

    def setUp(items=None, filter=None, columns=None, columns_before=None,
              columns_after=None, sort_on=None, prefix="", formatters=None,
              table_formatter=None):
        """Populate the table with items, set up the variables for table formatter.

        After calling this method you have batch and filter_widget set
        up as well, so you can render them in the view as well.
        """

    def render():
        """Render the table for display in a view."""
