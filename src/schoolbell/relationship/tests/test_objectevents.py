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
Unit tests for schoolbell.relationship.objectevents

$Id$
"""

import unittest

from zope.testing import doctest


def doctest_delete_breaks_relationships():
    """When you delete an object, all of its relationships should be removed

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schoolbell.relationship.objectevents import unrelateOnDeletion
        >>> zope.event.subscribers.append(unrelateOnDeletion)

    Suppose we have two related objects

        >>> from schoolbell.relationship.tests import SomeObject
        >>> apple = SomeObject('apple')
        >>> orange = SomeObject('orange')

        >>> from schoolbell.relationship import getRelatedObjects, relate
        >>> relate('example:Relationship',
        ...             (apple, 'example:One'),
        ...             (orange, 'example:Two'))
        >>> getRelatedObjects(apple, 'example:Two')
        [orange]

    We put those objects to a Zope 3 container.

        >>> from zope.app.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> container['apple'] = apple
        >>> container['orange'] = orange

    When we delete an object, all of its relationships should disappear

        >>> del container['orange']
        >>> getRelatedObjects(apple, 'example:Two')
        []

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def doctest_copy_breaks_relationships():
   """When you copy an object, all of its relationships should be removed

   (An alternative solution would be to clone the relationships, but I'm
   wary of that path.  What happens if you copy and paste objects between
   different application instances?)

        >>> from schoolbell.relationship.tests import setUp, tearDown
        >>> setUp()

        >>> import zope.event
        >>> old_subscribers = zope.event.subscribers[:]
        >>> from schoolbell.relationship.objectevents import unrelateOnCopy
        >>> zope.event.subscribers.append(unrelateOnCopy)

    Suppose we have two related objects.  We must have objects that are
    IContained, otherwise ObjectCopier will happily duplicate all related
    objects as well as relationship links.

        >>> from schoolbell.relationship.tests import SomeContained
        >>> apple = SomeContained('apple')
        >>> orange = SomeContained('orange')

        >>> from schoolbell.relationship import getRelatedObjects, relate
        >>> relate('example:Relationship',
        ...             (apple, 'example:One'),
        ...             (orange, 'example:Two'))
        >>> getRelatedObjects(apple, 'example:Two')
        [orange]

    We put those objects to a Zope 3 container.

        >>> from zope.app.container.btree import BTreeContainer
        >>> container = BTreeContainer()
        >>> container['apple'] = apple
        >>> container['orange'] = orange

    We copy one of the objects to another container.

        >>> from zope.app.copypastemove import ObjectCopier
        >>> another_container = BTreeContainer()
        >>> copier = ObjectCopier(container['orange'])
        >>> new_name = copier.copyTo(another_container)
        >>> copy_of_orange = another_container[new_name]

    When we copy an object, all of its relationships should disappear

        >>> from schoolbell.relationship.interfaces import IRelationshipLinks
        >>> list(IRelationshipLinks(copy_of_orange))
        []

    The old relationships should still work

        >>> getRelatedObjects(apple, 'example:Two')
        [orange]
        >>> getRelatedObjects(orange, 'example:One')
        [apple]

        >>> zope.event.subscribers[:] = old_subscribers
        >>> tearDown()

    """


def test_suite():
    return unittest.TestSuite([
                doctest.DocTestSuite(),
           ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
