#
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
SchoolTool application views.
"""

import zope.schema


def vocabulary(choices):
    """Create a SimpleVocabulary from a list of values and titles.

    >>> v = vocabulary([('value1', u"Title for value1"),
    ...                 ('value2', u"Title for value2")])
    >>> for term in v:
    ...   print term.value, '|', term.token, '|', term.title
    value1 | value1 | Title for value1
    value2 | value2 | Title for value2

    """
    return zope.schema.vocabulary.SimpleVocabulary(
        [zope.schema.vocabulary.SimpleTerm(v, title=t) for v, t in choices])


def vocabulary_titled(items):
    """Create a SimpleVocabulary from a list of objects having __name__ and
    title attributes.  Such items are common in many containers in SchoolTool.

    >>> class Item(object):
    ...     def __init__(self, name, title):
    ...         self.__name__ = name
    ...         self.title = title
    ...     def __repr__(self):
    ...         return '<Item "%s">' % self.title

    >>> v = vocabulary_titled([Item(u'thevalue1', u"Title one"),
    ...                        Item(u'\xc5\xa0amas', u"Title two")])
    >>> for term in v:
    ...   print term.value, '|', term.token, '|', term.title
    <Item "Title one"> | thevalue1- | Title one
    <Item "Title two"> | amas-uea5t | Title two

    """
    return zope.schema.vocabulary.SimpleVocabulary(
        [zope.schema.vocabulary.SimpleTerm(
                    item,
                    token=unicode(item.__name__).encode('punycode'),
                    title=item.title)
         for item in items])
