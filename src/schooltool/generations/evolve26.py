#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2008 Shuttleworth Foundation
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
Upgrade SchoolTool to generation 26.

Touch all the objects so they would update references to classes that
may have been moved to another module.
"""
import transaction

def evolve(context):
    storage = context.connection._storage
    next_oid = None
    n = 0
    while True:
        n += 1
        oid, tid, data, next_oid = storage.record_iternext(next_oid)
        obj = context.connection.get(oid)
        obj._p_activate()
        obj._p_changed = True

        if next_oid is None:
            break

        if n % 10000 == 0:
            # Some plugins can generate a lot of data, so we are
            # using savepoints to save on memory consuption.
            transaction.savepoint(optimistic=True)
