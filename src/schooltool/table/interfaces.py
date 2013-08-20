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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Interfaces for SchoolTool calendar browser views.
"""
import zope.schema
from zope.interface import Interface, Attribute
from zc.table.interfaces import IColumn

from schooltool.skin.flourish.interfaces import IContentProvider


class IBatch(Interface):

    def render():
        """ """


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

    batch = zope.schema.Object(schema=IBatch)

    filter_widget = zope.schema.Object(schema=IFilterWidget)

    def setUp(items=None, ommit=None, filter=None, columns=None, columns_before=None,
              columns_after=None, sort_on=None, prefix="", formatters=None,
              table_formatter=None, batch_size=10):
        """Populate the table with items, set up the variables for table formatter.

        After calling this method you have batch and filter_widget set
        up as well, so you can render them in the view as well.
        """

    def makeFormatter():
        """Build the zc.table formatter that can render this table."""

    def render():
        """Render the table for display in a view."""


class IIndexedTableFormatter(ITableFormatter):

    def indexItems(items):
        """Return a list of indexed items"""


class IIndexedColumn(Interface):
    """A column that operates on index dicts instead of objects.

    Index dicts are composed this way:

    context - the container containing items
    id      - the int id of the object
    catalog - the catalog that is storing relevant indexes
    key     - the key by which the object can be retrieved from the context

    XXX: information is a bit outdated
    """

class ICheckboxColumn(IColumn):
    """A column with a checkbox."""


class IRMLTable(IContentProvider):
    """Content provider that can render a table as RML."""

    table = Attribute("zc.table.interfaces.IFormatter to render")


class IRMLColumn(IColumn):

    column = Attribute("zc.table.column.Column")

    visible = zope.schema.Bool(
        title=u"Is column visible", required=False)
