==========================
SchoolBell Testing Support
==========================

This package basically splits into two parts, an abstract test-setup registry
and some specific setup functions that are useful for many test setups.

The Test-Setup Registry
-----------------------

The test-setup registry was designed to de-centralize the creation of a
testing environment, allowing several independent packages to contribute to a
particular setup. The codebase is located in:

  >>> from schooltool.testing import registry

In the module you will find a ``register()`` method that allows you to
register a function for a particular setup. The simplest case is to register a
function that has no arguments:

  >>> def addOne():
  ...     result.append(1)

You register the function as follows in the `SampleFill` setup registry:

  >>> registry.register('SampleFill', addOne)

Now you execute the setup using the ``setup()`` method:

  >>> result = []
  >>> registry.setup('SampleFill')
  >>> result
  [1]

Now we can register more complex functions as well, of course:

  >>> def addTwo(number):
  ...     result.append(number)
  >>> registry.register('SampleFill', addTwo, 2)

  >>> def addThree(number=None):
  ...     result.append(number)
  >>> registry.register('SampleFill', addThree, number=3)

  >>> def addFour(number1, number2=None):
  ...     result.append(number1+number2)
  >>> registry.register('SampleFill', addFour, 3, number2=1)

And here is the result:

  >>> result = []
  >>> registry.setup('SampleFill')
  >>> result
  [1, 2, 3, 4]

Note that the order of registration is preserved, so if you can control the
order of registration, one setup step could depnd on a previous one. However,
this is hard to accomplish for generic development platforms and it is thus
not recommended to rely on the order of the setup steps.

While this functionality in itself is alsready pretty powerful, it does not
cover all of our required use cases. Oftentimes we want to be able to
"decorate" an object using several setup steps. Let's say, we have the
following containerish object:

  >>> class Container(object):
  ...
  ...     def __init__(self):
  ...         self.data = []
  ...
  ...     def add(self, entry):
  ...         self.data.append(entry)

We now want our setup functions to fill this container with some initial
values. Clearly, the above method does not work here anymore, since we do not
have the container instance available when creating and registering the setup
step function. Here are a couple of functions that we would like to help with
the setup:

  >>> def addOneToContainer(container):
  ...     container.add(1)
  >>> registry.register('ContainerValues', addOneToContainer)

  >>> def addTwoToContainer(container, number=None):
  ...     container.add(number)
  >>> registry.register('ContainerValues', addTwoToContainer, number=2)

But how do we pass in the container? The ``setup()`` method allows you to
specify additional positional and keyword arguments. The positional arguments
passed via the ``setup()`` are *appended* to the original ones. The additional
keyword arguments are merged (updated) into the original keyword arguments.

  >>> container = Container()
  >>> registry.setup('ContainerValues', container)
  >>> container.data
  [1, 2]

  >>> container = Container()
  >>> registry.setup('ContainerValues', container=container)
  >>> container.data
  [1, 2]

Note: As you might have already noticed, every test-setup registry has its own
semantics and functions of a particular registry often have the same or
similar signatures.

As syntactic sugar, a setup function will be registered for all registries of
the form ``setup<registry name``:

  >>> container = Container()
  >>> registry.setupContainerValues(container)
  >>> container.data
  [1, 2]


HTML Analyzation Tools
----------------------

There is a set (currently one ;-) of helpful analyzation tools available.

  >>> from schooltool.testing import analyze

They are designed to ease the inspection of HTML and other testing output.


Pick an Element using an XPath expression
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Often you are only interested in a particular element or text. The
``queryHTML()`` method allows you to specify an XPath query to pick out a
particular note. A list of all found nodes will be returned. The nodes will be
returned as a serialized string.

  >>> html = '''
  ... <html>
  ...   <head>
  ...     <title>My Page</title>
  ...   </head>
  ...   <body>
  ...     <h1>This is my page!</h1>
  ...   </body>
  ... </html>
  ... '''

  >>> print analyze.queryHTML('html/body/h1', html)[0]
  <h1>This is my page!</h1>

It works also with XHTML compliant documents.

  >>> html = '''
  ... <html xmlns="http://www.w3.org/1999/xhtml">
  ...   <head>
  ...     <title>My Page</title>
  ...   </head>
  ...   <body>
  ...     <h1>This is my page!</h1>
  ...   </body>
  ... </html>
  ... '''

  >>> print analyze.queryHTML('html/body/h1', html)[0]
  <h1>This is my page!</h1>