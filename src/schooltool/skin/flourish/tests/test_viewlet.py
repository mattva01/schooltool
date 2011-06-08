#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Unit tests for schooltool.app.
"""
import unittest
import doctest

from zope.interface import implements
from zope.interface.verify import verifyObject
from zope.app.testing import setup
from zope.component import getMultiAdapter, provideAdapter
from zope.component import provideHandler
from zope.publisher.browser import TestRequest
from zope.security.interfaces import ISecurityPolicy
from zope.security.checker import defineChecker, CheckerPublic, NamesChecker
from zope.security.management import setSecurityPolicy
from zope.security.management import newInteraction, endInteraction
from zope.security.management import restoreInteraction

from schooltool.skin.flourish import interfaces
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManager
from schooltool.skin.flourish.viewlet import ManagerViewlet


class TestViewlet(Viewlet):
    status = 'A fresh'

    def update(self):
        print 'Updating', self
        self.status = 'An updated'

    def render(self, *args, **kw):
        passed = (
            [repr(a) for a in args] +
            ['%s=%r' % a for a in sorted(kw.items())])
        return '%s ViewletTest. Called render(%s)' % (
            self.status, ', '.join(passed))

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.__name__)


def viewletClass(permission=CheckerPublic, **classdict):
    cls = type('TestViewlet', (TestViewlet, ), classdict)
    defineChecker(cls, NamesChecker(list(interfaces.IViewlet), permission))
    return cls


class TestManager(ViewletManager):

    def render(self, *args, **kw):
        rendered = ['TestManager.render:']
        rendered += [str(v.render(*args, **kw))
                     for v in self.viewlets]
        return '\n'.join(rendered)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.__name__)


class TestManagerViewlet(ManagerViewlet):
    status = 'A fresh'

    def update(self):
        print 'Updating', self
        self.status = 'An updated'
        ManagerViewlet.update(self)

    def render(self, *args, **kw):
        passed = (
            [repr(a) for a in args] +
            ['%s=%r' % a for a in sorted(kw.items())])
        call_str = '%s %s.render(%s)' % (
            self.status, self.__class__.__name__,
            ', '.join(passed))
        rendered = [call_str]
        rendered += [str(v.render(*args, **kw))
                     for v in self.viewlets]
        return '\n'.join(rendered)

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.__name__)


def provideViewlet(factory, manager, name):
    provideAdapter(
        factory,
        (manager.context.__class__, manager.request.__class__,
         manager.view.__class__, manager.__class__),
        interfaces.IViewlet,
        name)


def doctest_Viewlet():
    """Tests for Viewlet.

        >>> viewlet = Viewlet('context', 'request', 'view', 'manager')

        >>> verifyObject(interfaces.IViewlet, viewlet)
        True

        >>> viewlet.context, viewlet.request, viewlet.view, viewlet.manager
        ('context', 'request', 'view', 'manager')

        >>> viewlet.__parent__
        'manager'

        >>> print viewlet.__name__
        None

        >>> viewlet.before, viewlet.after, viewlet.requires
        ((), (), ())

        >>> print viewlet.update()
        None

        >>> print viewlet.render()
        Traceback (most recent call last):
        ...
        NotImplementedError: `render` method must be implemented by subclass.


    """


def doctest_Viewlet_call():
    """Tests for Viewlet.__call__

        >>> viewlet = TestViewlet(None, 'request', None, None)

        >>> print viewlet.render()
        A fresh ViewletTest. Called render()

        >>> result =  viewlet('arg', option='something')
        Updating <TestViewlet None>

        >>> print result
        An updated ViewletTest. Called render('arg', option='something')

    """


def doctest_ViewletManager():
    """Tests for ViewletManager.

        >>> context = 'context'
        >>> request = TestRequest()
        >>> view = 'view'

        >>> manager = ViewletManager(context, request, view)

        >>> verifyObject(interfaces.IViewletManager, manager)
        True

    Let's provide some viewlets for the manager.

        >>> provideViewlet(viewletClass(), manager, 'v1')
        >>> provideViewlet(viewletClass(), manager, 'v2')

        >>> getMultiAdapter(
        ...     (manager.context, manager.request,
        ...      manager.view, manager),
        ...     interfaces.IViewlet, 'v1')
        <TestViewlet None>

    Note that name of adapter gets assigned to viewlet.__name__.

        >>> sorted(manager.viewlet_dict.items())
        [(u'v1', <TestViewlet u'v1'>),
         (u'v2', <TestViewlet u'v2'>)]

        >>> manager.order
        [u'v1', u'v2']

        >>> manager.viewlets
        [<TestViewlet u'v1'>, <TestViewlet u'v2'>]

        >>> 'v1' in manager
        True

        >>> manager.get('v1')
        <TestViewlet u'v1'>

        >>> manager.get('v3', 'nosuchthing')
        'nosuchthing'

        >>> manager['v2']
        <TestViewlet u'v2'>

        >>> manager['v3']
        Traceback (most recent call last):
        ...
        KeyError: 'v3'

    """


def doctest_ViewletManager_call():
    """Tests for ViewletManager.

        >>> from zope.contentprovider.interfaces import IBeforeUpdateEvent

        >>> context = 'context'
        >>> request = TestRequest()
        >>> view = 'view'

        >>> manager = TestManager(context, request, view)

        >>> verifyObject(interfaces.IViewletManager, manager)
        True

    Let's provide some viewlets for the manager.

        >>> provideViewlet(viewletClass(), manager, 'v1')
        >>> provideViewlet(viewletClass(), manager, 'v2')

        >>> def beforeUpdate(e):
        ...     print 'About to update', e.object
        >>> provideHandler(beforeUpdate, [IBeforeUpdateEvent])

        >>> result = manager('foo', bar='bar')
        About to update <TestManager None>
        About to update <TestViewlet u'v1'>
        Updating <TestViewlet u'v1'>
        About to update <TestViewlet u'v2'>
        Updating <TestViewlet u'v2'>

        >>> print result
        TestManager.render:
        An updated ViewletTest. Called render('foo', bar='bar')
        An updated ViewletTest. Called render('foo', bar='bar')

    """


def doctest_ViewletManager_order():
    """Tests for ViewletManager.order.

        >>> context = 'context'
        >>> request = TestRequest()
        >>> view = 'view'
        >>> manager = TestManager(context, request, view)

        >>> provideViewlet(
        ...     viewletClass(before=('v3')),
        ...     manager, 'v1')

        >>> provideViewlet(viewletClass(), manager, 'v2')

        >>> provideViewlet(
        ...     viewletClass(after=('v4')),
        ...     manager, 'v3')

        >>> provideViewlet(viewletClass(), manager, 'v4')

        >>> manager.order
        [u'v2', u'v4', u'v1', u'v3']

        >>> manager = TestManager(context, request, view)

    """


def doctest_ViewletManager_filter():
    """Tests for ViewletManager.filter

        >>> context = 'context'
        >>> request = TestRequest()
        >>> view = 'view'

        >>> class TestManager(ViewletManager):
        ...     def filter(self, viewlets):
        ...         print 'Filter viewlets:'
        ...         print sorted(viewlets)
        ...         return ViewletManager.filter(self, viewlets)

        >>> manager = TestManager(context, request, view)

        >>> provideViewlet(viewletClass(), manager, 'v1')

        >>> provideViewlet(
        ...     viewletClass(permission='deny'),
        ...     manager, 'v2')

        >>> provideViewlet(
        ...     viewletClass(requires=('v1',)),
        ...     manager, 'v3')

        >>> provideViewlet(
        ...     viewletClass(requires=('v2',)),
        ...     manager, 'v4')

        >>> provideViewlet(
        ...     viewletClass(requires=('v1', 'v3')),
        ...     manager, 'v5')

        >>> provideViewlet(
        ...     viewletClass(requires=('v1', 'v2')),
        ...     manager, 'v6')

        >>> filtered = manager.viewlets
        Filter viewlets:
        [(u'v1', <TestViewlet u'v1'>),
         (u'v2', <TestViewlet u'v2'>),
         (u'v3', <TestViewlet u'v3'>),
         (u'v4', <TestViewlet u'v4'>),
         (u'v5', <TestViewlet u'v5'>),
         (u'v6', <TestViewlet u'v6'>)]

        >>> print filtered
        [<TestViewlet u'v1'>, <TestViewlet u'v3'>, <TestViewlet u'v5'>]

    """


def doctest_ManagerViewlet():
    """Tests for ManagerViewlet.

        >>> names = sorted(interfaces.IManagerViewlet)

        >>> context = 'context'
        >>> request = TestRequest()
        >>> view = 'view'
        >>> manager = 'manager'

        >>> viewlet = ManagerViewlet(context, request, view, manager)
        >>> verifyObject(interfaces.IManagerViewlet, viewlet)
        True

        >>> viewlet.context, viewlet.request, viewlet.view, viewlet.manager
        ('context', <...TestRequest ...>, 'view', 'manager')

        >>> viewlet.__parent__
        'manager'

        >>> print viewlet.update()
        None

        >>> print viewlet.render()
        Traceback (most recent call last):
        ...
        NotImplementedError: `render` method must be implemented by subclass.

    The render method is inherited from the Viewlet.

        >>> viewlet.__class__.render == Viewlet.render
        True

    """


def doctest_ManagerViewlet_call():
    """Tests for ViewletManager.__call__

        >>> v = TestManagerViewlet(None, 'request', None, None)

        >>> print v.render()
        A fresh TestManagerViewlet.render()

        >>> result =  v('arg', option='something')
        Updating <TestManagerViewlet None>

        >>> print result
        An updated TestManagerViewlet.render('arg', option='something')

    """


def doctest_ManagerViewlet_viewlets():
    """Tests for ViewletManager.

        >>> from zope.contentprovider.interfaces import IBeforeUpdateEvent

        >>> context = 'context'
        >>> request = TestRequest()
        >>> view = 'view'
        >>> manager = 'manager'

        >>> viewlet = TestManagerViewlet(context, request, view, manager)

    Let's provide some viewlets for the manager.

        >>> provideViewlet(viewletClass(), viewlet, 'v1')
        >>> provideViewlet(viewletClass(), viewlet, 'v2')

        >>> def beforeUpdate(e):
        ...     print 'About to update', e.object
        >>> provideHandler(beforeUpdate, [IBeforeUpdateEvent])

        >>> print viewlet.viewlets
        [<TestViewlet u'v1'>, <TestViewlet u'v2'>]

        >>> result = viewlet('foo', bar='bar')
        About to update <TestManagerViewlet None>
        Updating <TestManagerViewlet None>
        About to update <TestViewlet u'v1'>
        Updating <TestViewlet u'v1'>
        About to update <TestViewlet u'v2'>
        Updating <TestViewlet u'v2'>

        >>> print result
        An updated TestManagerViewlet.render('foo', bar='bar')
        An updated ViewletTest. Called render('foo', bar='bar')
        An updated ViewletTest. Called render('foo', bar='bar')

    """


class SecurityPolicy(object):
    implements(ISecurityPolicy)

    def checkPermission(self, permission, object):
        return permission == 'allow'


def setUp(test=None):
    setup.placelessSetUp()
    test.globs['__policy'] = setSecurityPolicy(SecurityPolicy)
    endInteraction()
    newInteraction()


def tearDown(test=None):
    setSecurityPolicy(test.globs['__policy'])
    restoreInteraction()
    setup.placelessTearDown()


def test_suite():
    optionflags = (doctest.ELLIPSIS |
                   doctest.NORMALIZE_WHITESPACE |
                   doctest.REPORT_NDIFF)

    return unittest.TestSuite([
                doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                     optionflags=optionflags),
           ])


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
