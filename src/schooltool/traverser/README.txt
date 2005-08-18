====================
Pluggable Traversers
====================

Traversers are Zope's mechanism to convert URI paths to an object of the
application. They provide an extremly flexible mechanism to make decisions
based on the policies of the application. Unfortunately the default traverser
implementation is not flexible enough to deal with arbitrary extensions (via
adapters) of objects that also wish to participate in the traversal decision
process.

The pluggable traverser allows developers, especially third-party developers,
to add new traversers to an object without altering the original traversal
implementation.

  >>> from schoolbell.app.traverser.traverser import PluggableTraverser

Let's say that we have an object

  >>> from zope.interface import Interface, implements
  >>> class IContent(Interface):
  ...     pass

  >>> class Content(object):
  ...     implements(IContent)
  ...     var = True

  >>> content = Content()

that we wish to traverse to. Since traversers are presentation-type specific,
they are implemented as views and must thus be initiated using a request:

  >>> from zope.publisher.base import TestRequest
  >>> request = TestRequest('')
  >>> traverser = PluggableTraverser(content, request)

We can now try to lookup the variable:

  >>> traverser.publishTraverse(request, 'var')
  Traceback (most recent call last):
  ...
  NotFound: Object: <Content object at ...>, name: 'var'


But it failed. Why? Because we have not registered a plugin traverser yet that
knows how to lookup attributes. This package provides such a traverser
already, so we just have to register it:

  >>> from zope.component import provideSubscriptionAdapter
  >>> from zope.publisher.interfaces import IPublisherRequest
  >>> from schoolbell.app.traverser.traverser import AttributeTraverserPlugin

  >>> provideSubscriptionAdapter(AttributeTraverserPlugin,
  ...                            (IContent, IPublisherRequest))

If we now try to lookup the attribute, we the value:

  >>> traverser.publishTraverse(request, 'var')
  True

However, an incorrect variable name will still return a ``NotFound`` error:

  >>> traverser.publishTraverse(request, 'bad')
  Traceback (most recent call last):
  ...
  NotFound: Object: <Content object at ...>, name: 'bad'

Every traverser should also make sure that the passed in name is not a
view. (This allows us to not specify the ``@@`` in front of a view.) So let's
register one:

  >>> class View(object):
  ...     def __init__(self, context, request):
  ...         pass

  >>> from zope.component import provideAdapter
  >>> from zope.publisher.interfaces import IPublisherRequest
  >>> provideAdapter(View, 
  ...                adapts=(IContent, IPublisherRequest),
  ...                provides=Interface,
  ...                name='view.html')

Now we can lookup the view as well:

  >>> traverser.publishTraverse(request, 'view.html')
  <View object at ...>


Advanced Uses
-------------

A more interesting case to consider is a traverser for a container. If you
really dislike the Zope 3 traversal namespace notation ``++namespace`` and you
can control the names in the container, then the pluggable traverser will also
provide a viable solution. Let's say we have a container

  >>> from zope.app.container.interfaces import IContainer
  >>> class IMyContainer(IContainer):
  ...     pass

  >>> from zope.app.container.btree import BTreeContainer
  >>> class MyContainer(BTreeContainer):
  ...     implements(IMyContainer)
  ...     foo = True
  ...     bar = False

  >>> myContainer = MyContainer()
  >>> myContainer['blah'] = 123

and we would like to be able to traverse

  * all items of the container, as well as

    >>> from schoolbell.app.traverser.traverser import ContainerTraverserPlugin
    >>> from schoolbell.app.traverser.interfaces import ITraverserPlugin

    >>> provideSubscriptionAdapter(ContainerTraverserPlugin,
    ...                            (IMyContainer, IPublisherRequest),
    ...                            ITraverserPlugin)

  * the ``foo`` attribute. Luckily we also have a predeveloped traverser for
    this:

    >>> from schoolbell.app.traverser.traverser import \
    ...     SingleAttributeTraverserPlugin
    >>> provideSubscriptionAdapter(SingleAttributeTraverserPlugin('foo'),
    ...                            (IMyContainer, IPublisherRequest))

We can now use the pluggable traverser

  >>> traverser = PluggableTraverser(myContainer, request)

to look up items

  >>> traverser.publishTraverse(request, 'blah')
  123

and the ``foo`` attribute:

  >>> traverser.publishTraverse(request, 'foo')
  True

However, we cannot lookup the ``bar`` attribute or any other non-existent
item:

  >>> traverser.publishTraverse(request, 'bar')
  Traceback (most recent call last):
  ...
  NotFound: Object: <MyContainer object at ...>, name: 'bar'

  >>> traverser.publishTraverse(request, 'bad')
  Traceback (most recent call last):
  ...
  NotFound: Object: <MyContainer object at ...>, name: 'bad'

You can also add traversers that return an adapted object. For example, let's
take the following adapter:

  >>> class ISomeAdapter(Interface):
  ...     pass

  >>> from zope.component import adapts
  >>> class SomeAdapter(object):
  ...     implements(ISomeAdapter)
  ...     adapts(IMyContainer)
  ...
  ...     def __init__(self, context):
  ...         pass

  >>> from zope.component import adapts, provideAdapter
  >>> provideAdapter(SomeAdapter)

Now we register this adapter under the traversal name ``some``:

  >>> from schoolbell.app.traverser.traverser import AdapterTraverserPlugin
  >>> provideSubscriptionAdapter(
  ...     AdapterTraverserPlugin('some', ISomeAdapter),
  ...     (IMyContainer, IPublisherRequest))

So here the result:

  >>> traverser.publishTraverse(request, 'some')
  <SomeAdapter object at ...>