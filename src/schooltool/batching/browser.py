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
Browser mixins for batching

$Id$
"""

from batch import Batch

class MultiBatchViewMixin(object):
    """A view to handle multiple batches in a single view."""

    def __init__(self, names=[]):
        self.batches = {}
        self.batch_sizes = {}
        self.batch_starts = {}
        for name in names:
            self.batches[name] = None
            self.batch_sizes[name] = 10
            self.batch_starts[name] = 0

    def update(self):
        names = self.batches.keys()
        for name in names:
            start = self.request.get('batch_start.' + name, '0')
            size = self.request.get('batch_size.' + name, '10')
            self.batch_starts[name] = int(start)
            self.batch_sizes[name] = int(size)

    def updateBatch(self, name, lst, sort_on=None):
        """Use the provided name and iterable to create a new batch."""
        self.batches[name] = Batch(lst, self.batch_starts[name],
                                   self.batch_sizes[name], sort_on)
