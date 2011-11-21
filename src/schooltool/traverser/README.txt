====================
Pluggable Traversers
====================

Traversers are Zope's mechanism to convert URI paths to an object of the
application. They provide an extremly flexible mechanism to make decisions
based on the policies of the application. Unfortunately the default traverser
implementation is not flexible enough to deal with arbitrary extensions (via
adapters) of objects that also wish to participate in the traversal decision
process.

Let's say that we have some objects that we wish to traverse to.

    >>> from schooltool.testing import mock
    >>> mock.fake_module('schooltool.traverser.test_pluggable')
    >>> from schooltool.traverser import test_pluggable

    >>> from zope.interface import Interface, implements

    >>> @mock.module(test_pluggable)
    ... class ISimpleContent(Interface):
    ...     pass

    >>> @mock.module(test_pluggable)
    ... class SimpleContent(object):
    ...     implements(ISimpleContent)
    ...     name = 'simple content'

    >>> @mock.module(test_pluggable)
    ... class IContent(Interface):
    ...     pass

    >>> @mock.module(test_pluggable)
    ... class Content(object):
    ...     implements(IContent)
    ...     var = 'Some value'
    ...     other = 'Other value'

Traversal in its essence works like this:

    >>> from zope.component import getMultiAdapter
    >>> from zope.publisher.interfaces import IPublishTraverse

    >>> def traverse(ob, request, name):
    ...     adapter = getMultiAdapter((ob, request), IPublishTraverse)
    ...     return adapter.publishTraverse(request, name)


The simplest case is a stand-alone traverser:

    >>> zcml.setUp(namespaces={'': 'http://namespaces.zope.org/zope'})

    >>> from schooltool.traverser.traverser import Traverser

    >>> @mock.module(test_pluggable)
    ... class HelloTraverser(Traverser):
    ...
    ...     def traverse(self, name):
    ...         return '%s, %s' % (name, self.context.name)

    >>> zcml.string('''
    ...   <traverser
    ...       for="schooltool.traverser.test_pluggable.ISimpleContent"
    ...       factory="schooltool.traverser.test_pluggable.HelloTraverser"
    ...       type="zope.publisher.interfaces.http.IHTTPRequest"
    ...       />
    ... ''')

    >>> from zope.publisher.browser import TestRequest
    >>> request = TestRequest()

    >>> simple_content = SimpleContent()

    >>> print traverse(simple_content, request, 'Hello')
    Hello, simple content

    >>> print traverse(simple_content, request, 'Bye')
    Bye, simple content


The pluggable traverser allows developers, especially third-party developers,
to add new traversers to an object without altering the original traversal
implementation.

Let's make traversal from our content object pluggable.


    >>> zcml.string('''
    ...   <pluggableTraverser
    ...       for="schooltool.traverser.test_pluggable.IContent"
    ...       type="zope.publisher.interfaces.http.IHTTPRequest"
    ...       />
    ... ''')

We can now try to lookup the variable::

    >>> request = TestRequest()

    >>> content = Content()

    >>> traverse(content, request, 'var')
    Traceback (most recent call last):
    ...
    NotFound: Object: <Content object at ...>, name: 'var'

But it fails, because we have not registered a plugin traverser yet that
knows how to lookup attributes. This package provides such a traverser
already, so we just have to register it::

    >>> zcml.string('''
    ...   <traverserPlugin
    ...       for="schooltool.traverser.test_pluggable.IContent"
    ...       plugin="schooltool.traverser.traverser.AttributeTraverserPlugin"
    ...       />
    ... ''')

    >>> traverse(content, request, 'var')
    'Some value'

    >>> traverse(content, request, 'other')
    'Other value'

However, an incorrect variable name will still return a 'NotFound' error:

    >>> traverse(content, request, 'bad')
    Traceback (most recent call last):
    ...
    NotFound: Object: <Content object at ...>, name: 'bad'

Every traverser should also make sure that the passed in name is not a
view. (This allows us to not specify the '@@' in front of a view.) So let's
register one::

    >>> @mock.module(test_pluggable)
    ... class View(object):
    ...     def __init__(self, context, request):
    ...         pass

    >>> zcml.string('''
    ...   <adapter
    ...       for="schooltool.traverser.test_pluggable.IContent
    ...            zope.publisher.interfaces.IPublisherRequest"
    ...       provides="zope.interface.Interface"
    ...       factory="schooltool.traverser.test_pluggable.View"
    ...       name="view.html"
    ...       />
    ... ''')

Now we can lookup the view as well::

    >>> traverse(content, request, 'view.html')
    <View object at ...>


Combining plugins
-----------------

A more interesting case to consider is a traverser for a container. If you
really dislike the Zope 3 traversal namespace notation '++namespace++' and
you can control the names in the container, then the pluggable traverser will
also provide a viable solution. Let's say we have a container::

    >>> from zope.container.interfaces import IContainer

    >>> @mock.module(test_pluggable)
    ... class IMyContainer(IContainer):
    ...     pass

    >>> from zope.container.btree import BTreeContainer

    >>> @mock.module(test_pluggable)
    ... class MyContainer(BTreeContainer):
    ...     implements(IMyContainer)
    ...     foo = True
    ...     bar = False

    >>> myContainer = MyContainer()
    >>> myContainer['answer'] = 42
    >>> myContainer['question'] = '?'


Say we would like to be able to traverse all items of the container, as
well as the 'foo' attribute.

First, enable the pluggable traverser for our container.

    >>> zcml.string('''
    ...   <pluggableTraverser
    ...       for="schooltool.traverser.test_pluggable.IMyContainer"
    ...       type="zope.publisher.interfaces.http.IHTTPRequest"
    ...       />
    ... ''')

Then set ContainerTraverserPlugin as the default plugin.  To do so, we
ommit the name.

    >>> zcml.string('''
    ...   <traverserPlugin
    ...       for="schooltool.traverser.test_pluggable.IMyContainer"
    ...       plugin="schooltool.traverser.traverser.ContainerTraverserPlugin"
    ...       permission="zope.Public"
    ...       />
    ... ''')

Now we add a specific attribute traversal to 'foo'.

    >>> zcml.string('''
    ...   <attributeTraverserPlugin
    ...       for="schooltool.traverser.test_pluggable.IMyContainer"
    ...       name="foo"
    ...       />
    ... ''')

We can now use the pluggable traverser to look up items:

    >>> traverse(myContainer, request, 'answer')
    42

    >>> traverse(myContainer, request, 'question')
    '?'

And also the 'foo' attribute:

    >>> traverse(myContainer, request, 'foo')
    True

However, we cannot lookup the ``bar`` attribute or any other non-existent
item::

    >>> traverse(myContainer, request, 'bar')
    Traceback (most recent call last):
    ...
    NotFound: Object: <MyContainer object at ...>, name: 'bar'

    >>> traverse(myContainer, request, 'bad')
    Traceback (most recent call last):
    ...
    NotFound: Object: <MyContainer object at ...>, name: 'bad'


Adapter traverser plugin
------------------------

Often objects already have various useful adapters, and it is
convenient to reuse them for traversal. ::

Say, we have an ISomeSettings adapter for IMyContainer.

    >>> @mock.module(test_pluggable)
    ... class ISomeSettings(Interface):
    ...     pass

    >>> @mock.module(test_pluggable)
    ... class SomeSettings(object):
    ...     def __init__(self, context):
    ...         self.context = context
    ...     def __repr__(self):
    ...         return '<Settings for %s>' % self.context.__class__.__name__

    >>> zcml.string('''
    ...   <adapter
    ...       for="schooltool.traverser.test_pluggable.IMyContainer"
    ...       provides="schooltool.traverser.test_pluggable.ISomeSettings"
    ...       factory="schooltool.traverser.test_pluggable.SomeSettings" />
    ... ''')

Now we can register this adapter under the traversal name 'settings':

    >>> zcml.string('''
    ...   <adapterTraverserPlugin
    ...       for="schooltool.traverser.test_pluggable.IMyContainer"
    ...       adapter="schooltool.traverser.test_pluggable.ISomeSettings"
    ...       name="settings"
    ...       />
    ... ''')

Here is the result:

    >>> container = MyContainer()
    >>> traverse(container, request, 'settings')
    <Settings for MyContainer>
