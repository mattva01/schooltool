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
Implementation of notes for IAnnotatable objects.

Notes are stored as a PersistentList of Note objects on IAnnotatable objects.
A Note is a simple object that stores a brief note or comment about an object
to be entered by a user.

TODO: It might be a good idea to add some ACL to notes:

    Person A from Cafeteria group wishes to create a note about an annual event
    for employees.  The note is useful to other memebers of the Cafeteria
    group, but not useful (or should not be seen) to others. 

"""

from zope.app.annotation.interfaces import IAnnotations
from schoolbell.app.app import Notes


def getNotes(context):
    """Adapt an IAnnotatable object to INotes."""
    annotations = IAnnotations(context)
    key = 'schoolbell.app.app.Notes'
    try:
        return annotations[key]
    except KeyError:
        annotations[key] = Notes()
        return annotations[key]

