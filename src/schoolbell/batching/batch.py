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
Batching for schoolbell.

$Id$
"""

from interfaces import IBatch

class Batch(object):
    """Batching mechanism for SchoolBell.

    See schoolbell.batching.interfaces.IBatch."""

    def __init__(self, iterable, start, size, sort_by=None):
        self.list = list(iterable)
        if sort_by:
            self._sortBy(sort_by)
        self.start = start
        self.size = size
        self.batch = self.list[start:start + size]

    def __len__(self):
        return len(self.batch)

    def __iter__(self):
        return iter(self.batch)

    def __contains__(self, item):
        return bool(item in [i for i in self])

    def __eq__(self, other):
        return ((self.size, self.start, self.batch, self.list) == 
                (other.size, other.start, other.batch, other.list))

    def __ne__(self, other):
        return not self.__eq__(other)

    def first(self):
        return self.batch[0]

    def last(self):
        return self.batch[len(self) - 1]

    def next(self):
        start = self.size + self.start
        if len(self.list) > start:
            return Batch(self.list, start, self.size)

        return None

    def prev(self):
        start = self.start - self.size
        if start < 0:
            return None

        return Batch(self.list, start, self.size)

    def num(self):
        return self.start / self.size + 1

    def numBatches(self):
        num = len(self.list) / self.size
        if len(self.list) % self.size:
            num += 1
        return num

    def batches(self):
        batch = Batch(self.list, 0, self.size)
        result = [batch]
        while batch.next():
            result.append(batch.next())
            batch = batch.next()
        return result

    def _sortBy(self, attribute):
        """Sort the full batch list by specified attribute"""
        try:
            results = [(obj.get(attribute), obj) for obj in self.list]
        except AttributeError:
            results = [(getattr(obj, attribute), obj) for obj in self.list]

        results.sort()
        self.list = [obj for (key, obj) in results]

