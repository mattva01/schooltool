##############################################################################
#
# Copyright (c) 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""XXX short summary goes here.

$Id: test_adapter.py,v 1.5 2004/04/05 19:43:41 jim Exp $
"""
import unittest, doctest
import zope.interface
from zope.interface.adapter import AdapterRegistry
import zope.interface

class IF0(zope.interface.Interface):
    pass
class IF1(IF0):
    pass

class IB0(zope.interface.Interface):
    pass
class IB1(IB0):
    pass

class IR0(zope.interface.Interface):
    pass
class IR1(IR0):
    pass

def test_multi_adapter_w_default():
    """
    >>> registry = AdapterRegistry()
    
    >>> registry.register([None, IR0], IB1, 'bob', 'A1')

    >>> registry.lookup((IF1, IR1), IB0, 'bob')
    'A1'
    
    >>> registry.lookup((IF1, IR1), IB0, 'bruce')

    >>> registry.register([None, IR1], IB1, 'bob', 'A2')
    >>> registry.lookup((IF1, IR1), IB0, 'bob')
    'A2'
    """

def test_multi_adapter_w_inherited_and_multiple_registrations():
    """
    >>> registry = AdapterRegistry()

    >>> class IX(zope.interface.Interface):
    ...    pass

    >>> registry.register([IF0, IR0], IB1, 'bob', 'A1')
    >>> registry.register([IF1, IX], IB1, 'bob', 'AX')

    >>> registry.lookup((IF1, IR1), IB0, 'bob')
    'A1'
    """

def test_named_adapter_with_default():
    """Query a named simple adapter

    >>> registry = AdapterRegistry()

    If we ask for a named adapter, we won't get a result unless there
    is a named adapter, even if the object implements the interface:

    >>> registry.lookup([IF1], IF0, 'bob')

    >>> registry.register([None], IB1, 'bob', 'A1')
    >>> registry.lookup([IF1], IB0, 'bob')
    'A1'

    >>> registry.lookup([IF1], IB0, 'bruce')

    >>> registry.register([None], IB0, 'bob', 'A2')
    >>> registry.lookup([IF1], IB0, 'bob')
    'A2'
    """

def test_multi_adapter_gets_closest_provided():
    """
    >>> registry = AdapterRegistry()
    >>> registry.register([IF1, IR0], IB0, 'bob', 'A1')
    >>> registry.register((IF1, IR0), IB1, 'bob', 'A2')
    >>> registry.lookup((IF1, IR1), IB0, 'bob')
    'A1'

    >>> registry = AdapterRegistry()
    >>> registry.register([IF1, IR0], IB1, 'bob', 'A2')
    >>> registry.register([IF1, IR0], IB0, 'bob', 'A1')
    >>> registry.lookup([IF1, IR0], IB0, 'bob')
    'A1'

    >>> registry = AdapterRegistry()
    >>> registry.register([IF1, IR0], IB0, 'bob', 'A1')
    >>> registry.register([IF1, IR1], IB1, 'bob', 'A2')
    >>> registry.lookup([IF1, IR1], IB0, 'bob')
    'A2'

    >>> registry = AdapterRegistry()
    >>> registry.register([IF1, IR1], IB1, 'bob', 2)
    >>> registry.register([IF1, IR0], IB0, 'bob', 1)
    >>> registry.lookup([IF1, IR1], IB0, 'bob')
    2
    """

def test_multi_adapter_check_non_default_dont_hide_default():
    """
    >>> registry = AdapterRegistry()

    >>> class IX(zope.interface.Interface):
    ...     pass

    
    >>> registry.register([None, IR0], IB0, 'bob', 1)
    >>> registry.register([IF1,   IX], IB0, 'bob', 2)
    >>> registry.lookup([IF1, IR1], IB0, 'bob')
    1
    """


def test_getRegisteredMatching_with_with():
    """
    >>> registry = AdapterRegistry()
    >>> registry.register([None], IB0, '', '_0')
    >>> registry.register([IF0], IB0, '', '00')
    >>> registry.register([IF1], IB0, '', '10')
    >>> registry.register([IF1], IB1, '', '11')
    >>> registry.register((IF0, IR0), IB0, '', '000')
    >>> registry.register((IF1, IR0), IB0, '', '100')
    >>> registry.register((IF1, IR0), IB1, '', '110')
    >>> registry.register((IF0, IR1), IB0, '', '001')
    >>> registry.register((IF1, IR1), IB0, '', '101')
    >>> registry.register((IF1, IR1), IB1, '', '111')

    >>> from pprint import PrettyPrinter
    >>> pprint = PrettyPrinter(width=60).pprint
    >>> def sorted(x):
    ...    x = [(getattr(r, '__name__', None), p.__name__,
    ...          [w.__name__ for w in rwith], n, f)
    ...         for (r, p, rwith, n, f) in x]
    ...    x.sort()
    ...    pprint(x)

    >>> sorted(registry.getRegisteredMatching())
    [(None, 'IB0', [], u'', '_0'),
     ('IF0', 'IB0', [], u'', '00'),
     ('IF0', 'IB0', ['IR0'], u'', '000'),
     ('IF0', 'IB0', ['IR1'], u'', '001'),
     ('IF1', 'IB0', [], u'', '10'),
     ('IF1', 'IB0', ['IR0'], u'', '100'),
     ('IF1', 'IB0', ['IR1'], u'', '101'),
     ('IF1', 'IB1', [], u'', '11'),
     ('IF1', 'IB1', ['IR0'], u'', '110'),
     ('IF1', 'IB1', ['IR1'], u'', '111')]
    >>> sorted(registry.getRegisteredMatching(required=[IF0]))
    [(None, 'IB0', [], u'', '_0'),
     ('IF0', 'IB0', [], u'', '00'),
     ('IF0', 'IB0', ['IR0'], u'', '000'),
     ('IF0', 'IB0', ['IR1'], u'', '001')]
    >>> sorted(registry.getRegisteredMatching(required=[IF1],
    ...                                       provided=[IB0]))
    [(None, 'IB0', [], u'', '_0'),
     ('IF0', 'IB0', [], u'', '00'),
     ('IF0', 'IB0', ['IR0'], u'', '000'),
     ('IF0', 'IB0', ['IR1'], u'', '001'),
     ('IF1', 'IB0', [], u'', '10'),
     ('IF1', 'IB0', ['IR0'], u'', '100'),
     ('IF1', 'IB0', ['IR1'], u'', '101'),
     ('IF1', 'IB1', [], u'', '11'),
     ('IF1', 'IB1', ['IR0'], u'', '110'),
     ('IF1', 'IB1', ['IR1'], u'', '111')]
    >>> sorted(registry.getRegisteredMatching(required=[IF1],
    ...                                       provided=[IB0],
    ...                                       with=[IR0]))
    [('IF0', 'IB0', ['IR0'], u'', '000'),
     ('IF1', 'IB0', ['IR0'], u'', '100'),
     ('IF1', 'IB1', ['IR0'], u'', '110')]
    >>> sorted(registry.getRegisteredMatching(required=[IF1],
    ...                                       provided=[IB0],
    ...                                       with=[IR1]))
    [('IF0', 'IB0', ['IR0'], u'', '000'),
     ('IF0', 'IB0', ['IR1'], u'', '001'),
     ('IF1', 'IB0', ['IR0'], u'', '100'),
     ('IF1', 'IB0', ['IR1'], u'', '101'),
     ('IF1', 'IB1', ['IR0'], u'', '110'),
     ('IF1', 'IB1', ['IR1'], u'', '111')]
    """




def test_suite():
    from docfilesuite import DocFileSuite
    return unittest.TestSuite((
        DocFileSuite('../adapter.txt', 'foodforthought.txt'),
        doctest.DocTestSuite('zope.interface.adapter'),
        doctest.DocTestSuite(),
        ))

if __name__ == '__main__': unittest.main()
