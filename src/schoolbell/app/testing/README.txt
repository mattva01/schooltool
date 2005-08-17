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

  >>> from schoolbell.app.testing import registry

In the module you will find a ``register()`` method that allows you to
register a function for a particular setup. The simplest case is to register a
function that has no arguments:

  >>> def addOne():
  ...     result.append(1)

You register the function as follows in the `SampleSetup` setup registry:

  >>> registry.register('SampleSetup', addOne)

Now you execute the setup using the ``setup()`` method:

  >>> result = []
  >>> registry.setup('SampleSetup')
  >>> result
  [1]

Now we can register more complex functions as well, of course:

  >>> def addTwo(number):
  ...     result.append(number)
  >>> registry.register('SampleSetup', addTwo, 2)

  >>> def addThree(number=None):
  ...     result.append(number)
  >>> registry.register('SampleSetup', addThree, number=3)

  >>> def addFour(number1, number2=None):
  ...     result.append(number1+number2)
  >>> registry.register('SampleSetup', addFour, 3, number2=1)

And here is the result:

  >>> result = []
  >>> registry.setup('SampleSetup')
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
  >>> registry.register('ContainerSetup', addOneToContainer)

  >>> def addTwoToContainer(container, number=None):
  ...     container.add(number)
  >>> registry.register('ContainerSetup', addTwoToContainer, number=2)

But how do we pass in the container? The ``setup()`` method allows you to
specify additional positional and keyword arguments. The positional arguments
passed via the ``setup()`` are *appended* to the original ones. The additional
keyword arguments are merged (updated) into the original keyword arguments.

  >>> container = Container()
  >>> registry.setup('ContainerSetup', container)
  >>> container.data
  [1, 2]

  >>> container = Container()
  >>> registry.setup('ContainerSetup', container=container)
  >>> container.data
  [1, 2]
