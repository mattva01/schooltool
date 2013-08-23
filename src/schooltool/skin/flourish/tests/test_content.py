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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Tests for schooltool content provider machinery.
"""
import unittest
import doctest

from zope.component import provideAdapter, provideHandler
from zope.component import queryMultiAdapter
from zope.interface import implements, Interface
from zope.interface.verify import verifyObject

from schooltool.skin.flourish.interfaces import IContentProvider
from schooltool.skin.flourish.interfaces import IContentProviders
from schooltool.skin.flourish.content import ContentProviders
from schooltool.skin.flourish.content import ContentProvider
from schooltool.skin.flourish.content import ContentProviderProxy
from schooltool.app.browser.testing import setUp, tearDown


def doctest_ContentProvider():
    """Tests for ContentProvider base class.

        >>> from zope.contentprovider.interfaces import IBeforeUpdateEvent

        >>> provider = ContentProvider('context', 'request', 'view')
        >>> verifyObject(IContentProvider, provider)
        True

        >>> events = []
        >>> def log_event(event):
        ...     events.append('%s for %s' %
        ...         (event.__class__.__name__,
        ...          event.object.__class__.__name__))
        >>> provideHandler(log_event, [IBeforeUpdateEvent])

        >>> provider()
        Traceback (most recent call last):
        ...
        NotImplementedError: ``render`` method must be implemented by subclass

        >>> events
        ['BeforeUpdateEvent for ContentProvider']

        >>> events[:] = []

        >>> class ProviderForTest(ContentProvider):
        ...     def update(self):
        ...         events.append('%s.update' % self.__class__.__name__)
        ...     def render(self, *args, **kw):
        ...         events.append('%s.render' % self.__class__.__name__)
        ...         return 'rendered with %s %s' % (args, kw)

        >>> provider = ProviderForTest('context', 'request', 'view')

        >>> result = provider('param1', keyword='hello')

        >>> events
        ['BeforeUpdateEvent for ProviderForTest',
         'ProviderForTest.update',
         'ProviderForTest.render']

        >>> print result
        rendered with ('param1',) {'keyword': 'hello'}

        >>> provider.context, provider.request, provider.view
        ('context', 'request', 'view')

    ContentProvider.view is an alternative to ContentProvider.__parent__.

        >>> provider.__parent__ = 'the view'

        >>> provider.view
        'the view'

        >>> provider.view = 'again with the view'

        >>> provider.__parent__
        'again with the view'

    """


def doctest_ContentProviderProxy():
    """Tests for ContentProviderProxy.

        >>> from zope.contentprovider.interfaces import (
        ...     IContentProvider as IZopeContentProvider)
        >>> from zope.contentprovider.interfaces import IBeforeUpdateEvent
        >>> from zope.contentprovider.provider import ContentProviderBase

        >>> class OldProvider(ContentProviderBase):
        ...     def update(self):
        ...         print 'updating', self
        ...     def render(self, *args, **kw):
        ...         print 'rendering', self
        ...         return 'Rendered with arguments: %s; %s' % (args, kw)

    Zope's content providers are not callable:

        >>> old_provider = OldProvider('context', 'request', 'view')

        >>> old_provider()
        Traceback (most recent call last):
        ...
        TypeError: 'OldProvider' object is not callable

    This proxy just wraps zope's content providers, making them callable.
    The proxied provider behaviour of TALESProviderExpression from
    zope.contentprovider.

        >>> provideAdapter(ContentProviderProxy)
        >>> provider = IContentProvider(old_provider)

        >>> def print_event(event):
        ...     print event.__class__.__name__, 'for', event.object
        >>> provideHandler(print_event, [IBeforeUpdateEvent])

        >>> result = provider('arg1', 'arg2', options='some options')
        BeforeUpdateEvent for <...OldProvider object at ...>
        updating <...OldProvider object at ...>
        rendering <...OldProvider object at ...>

        >>> print result
        Rendered with arguments: ('arg1', 'arg2'); {'options': 'some options'}

    The proxied provider is otherwise transparent.

        >>> verifyObject(IZopeContentProvider, provider)
        True

        >>> verifyObject(IContentProvider, provider)
        True

        >>> provider.context, provider.request, provider.__parent__
        ('context', 'request', 'view')

    """


def doctest_ContentProviders_traversal():
    """Tests for ContentProviders.

    ContentProviders are designed as multi adapter to IContentProviders.

        >>> class SomeContext(object):
        ...     pass

        >>> provideAdapter(ContentProviders,
        ...                (SomeContext, None, None),
        ...                IContentProviders)

        >>> def adapt(*args):
        ...     return queryMultiAdapter(args, IContentProviders)

        >>> providers = adapt(SomeContext(), 'request', 'view')

        >>> verifyObject(IContentProviders, providers)
        True

        >>> providers.context, providers.request, providers.view
        (<...SomeContext ...>, 'request', 'view')

   The adapter is traversable - it looks up content providers by
   adapting to IContentProvider.

   Let's register a content provider.

        >>> class ContentProvider(ContentProvider):
        ...     def render(self, *args, **kw):
        ...         return 'Rendered %r for %r' % (self, self.context)

        >>> provideAdapter(ContentProvider,
        ...                (SomeContext, None, None),
        ...                provides=IContentProvider,
        ...                name='dummy')

        >>> dummy = providers.traverse('dummy', ())

        >>> dummy()
        'Rendered <...ContentProvider ...> for <...SomeContext ...>'

    Traversal does not modify further path:

        >>> path = ['more', 'to', 'follow']
        >>> name = 'dummy'
        >>> dummy = providers.traverse(name, path)
        >>> path
        ['more', 'to', 'follow']

    Traversing to non-existent providers throws an exception.

        >>> providers.traverse('info', ())
        Traceback (most recent call last):
        ...
        ContentProviderLookupError: (<...SomeContext ...>, 'info')

    It is possible to traverse to zope's content providers.

        >>> from zope.contentprovider.provider import ContentProviderBase
        >>> class ContentProviderStub(ContentProviderBase):
        ...     def render(self, *args, **kw):
        ...         return 'Rendered %r for %r' % (self, self.context)

        >>> from zope.contentprovider.interfaces import (
        ...     IContentProvider as IZopeContentProvider)
        >>> provideAdapter(ContentProviderStub,
        ...                (SomeContext, None, None),
        ...                provides=IZopeContentProvider,
        ...                name='info')

        >>> providers.traverse('info', ())
        Traceback (most recent call last):
        ...
        ContentProviderLookupError: (<...SomeContext ...>, 'info')

    But they need to be adaptable to IContentProvider.
    Also, content providers cache the looked up providers, so we need to reset
    the cache.

        >>> provideAdapter(ContentProviderProxy)

        >>> info = providers.traverse('info', ())
        Traceback (most recent call last):
        ...
        ContentProviderLookupError: (<...SomeContext ...>, 'info')

        >>> providers = adapt(SomeContext(), 'request', 'view')

        >>> info = providers.traverse('info', ())

        >>> info()
        'Rendered <...ContentProviderStub ...> for <...SomeContext ...>'

    Let's try with another context.

        >>> class OtherContext(object):
        ...     pass

        >>> print adapt(OtherContext(), 'request', 'view')
        None

        >>> provideAdapter(ContentProviders,
        ...                (OtherContext, None, None),
        ...                IContentProviders)

    Content providers are context/request/view sensitive, and we can see
    that there is no 'dummy' ContentProvider for this context.

        >>> providers = adapt(OtherContext(), 'request', 'view')
        >>> providers.traverse('dummy', ())
        Traceback (most recent call last):
        ...
        ContentProviderLookupError: (<...OtherContext ...>, 'dummy')

    """


def doctest_ContentProviders_getitem():
    """Tests demonstrating dict-like ContentProviders behaviour.

    ContentProviders are designed as multi adapter to IContentProviders.

        >>> class SomeContext(object):
        ...     pass

        >>> provideAdapter(ContentProviders,
        ...                (SomeContext, None, None),
        ...                IContentProviders)

        >>> def adapt(*args):
        ...     return queryMultiAdapter(args, IContentProviders)

        >>> providers = adapt(SomeContext(), 'request', 'view')

        >>> class TestProvider(ContentProvider):
        ...     def __repr__(self):
        ...         return '<%s %r>' % (self.__class__.__name__, self.__name__)

        >>> provideAdapter(TestProvider,
        ...                (SomeContext, None, None),
        ...                provides=IContentProvider,
        ...                name='frog')

        >>> provideAdapter(TestProvider,
        ...                (SomeContext, None, None),
        ...                provides=IContentProvider,
        ...                name='pond')

        >>> providers['frog']
        <TestProvider 'frog'>

        >>> providers.get('pond')
        <TestProvider 'pond'>

        >>> providers['spoon']
        Traceback (most recent call last):
        ...
        KeyError: 'spoon'

        >>> providers.get('spoon', default='There is no spoon')
        'There is no spoon'

    """


def doctest_TALESAwareContentProviders():
    """Tests for TALESAwareContentProviders.

    When TALESAwareContentProviders traverse to a content provider,
    they add the requested TAL attributes to the provider.  Tal attributes are
    taken from the tal engine.

        >>> from schooltool.skin.flourish.content import (
        ...     TALESAwareContentProviders)

        >>> providers = TALESAwareContentProviders(
        ...     'context', 'request', 'view')

        >>> class ContentProviderStub(ContentProvider):
        ...     def render(self, *args, **kw):
        ...         return 'Rendered %r for %r' % (self, self.context)

        >>> provideAdapter(ContentProviderStub,
        ...                (None, None, None),
        ...                provides=IContentProvider,
        ...                name='dummy')

        >>> class TALContext(object):
        ...     def __init__(self, vars=()):
        ...         self.vars = dict(vars)

        >>> providers.setEngine(TALContext({
        ...     'hello': 'Hello world!',
        ...     'bar': 'BAR'
        ...     }))

    Simply traversing to a provider will not set the attributes from tal.

        >>> provider = providers.traverse('dummy', ())
        >>> provider.hello
        Traceback (most recent call last):
        ...
        AttributeError: 'ContentProviderStub' object has no attribute 'hello'

    To do this, we need a schema that defines the attributes we want.

        >>> from zope.schema import TextLine

        >>> class IHelloData(Interface):
        ...     hello = TextLine(title=u'The greeting.')

    We also need to set the type of the schema to ITALNamespaceData

        >>> from zope.interface import alsoProvides
        >>> from zope.contentprovider.interfaces import ITALNamespaceData

        >>> alsoProvides(IHelloData, ITALNamespaceData)

   Finally, make our content provider implement IHelloData.

        >>> class GreetingContentProvider(ContentProviderStub):
        ...     implements(IHelloData)

        >>> provideAdapter(GreetingContentProvider,
        ...                (None, None, None),
        ...                provides=IContentProvider,
        ...                name='greeting')

   We can now see that relevant data is passed from tal.

        >>> provider = providers.traverse('greeting', ())

        >>> provider.hello
        'Hello world!'

        >>> provider.bar
        Traceback (most recent call last):
        ...
        AttributeError: 'GreetingContentProvider' object has no attribute 'bar'

    """


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(setUp=setUp, tearDown=tearDown,
                                       optionflags=optionflags))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
