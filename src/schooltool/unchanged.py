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
Persistent singleton 'Unchanged'.

$Id$
"""

__metaclass__ = type


class UnchangedClass:
    """Singleton marker object for things that are unchanged."""

    def __new__(cls):
        instance = getattr(cls, '__singleton_instance__', None)
        if instance is None:
            instance = object.__new__(cls)
            cls.__singleton_instance__ = instance
        return instance

    def __str__(self):
        return "The Unchanged singleton"

    def __lt__(self, other):
        raise TypeError("Cannot compare Unchanged using <, <=, >, >=")

    __gt__ = __le__ = __ge__ = __lt__

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other


# Register Unchanged to be a constant by identity, even when pickled and
# unpickled.
import copy_reg
copy_reg.pickle(UnchangedClass, lambda obj: 'Unchanged', UnchangedClass)

Unchanged = UnchangedClass()
