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
Batching interfaces.

$Id$
"""

from zope.interface import Interface

class IBatch(Interface):
    """Provides batching of large lists into more manageable slices."""

    def __len__():
        """Length of the batch."""

    def __iter__():
        """An iterator over the batch"""

    def __eq__(other):
        """Compare this batch to another to see if they are the same.

        Compares size, start, list and the current batch list."""

    def __ne__(other):
        """Compare this batch to another to see if they are not equal.

        Returns the boolean opposite of __eq__."""

    def next():
        """The next batch from the list."""

    def prev():
        """The previous batch from the list."""

    def first():
        """The first item in the batch."""

    def last():
        """The last item in the batch."""

    def numBatches():
        """The number of batches required to cover the entire list."""
