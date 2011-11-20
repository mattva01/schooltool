==========================
SchoolTool Testing Support
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

Now you execute the setup using the ``setup()`` method::

    >>> result = []
    >>> registry.setup('SampleFill')
    >>> result
    [1]

Now we can register more complex functions::

    >>> def addTwo(number):
    ...     result.append(number)
    >>> registry.register('SampleFill', addTwo, 2)

    >>> def addThree(number=None):
    ...     result.append(number)
    >>> registry.register('SampleFill', addThree, number=3)

    >>> def addFour(number1, number2=None):
    ...     result.append(number1+number2)
    >>> registry.register('SampleFill', addFour, 3, number2=1)

And here is the result::

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
following containerish object::

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
the setup::

    >>> def addOneToContainer(container):
    ...     container.add(1)
    >>> registry.register('ContainerValues', addOneToContainer)

    >>> def addTwoToContainer(container, number=None):
    ...     container.add(number)
    >>> registry.register('ContainerValues', addTwoToContainer, number=2)

But how do we pass in the container? The ``setup()`` method allows you to
specify additional positional and keyword arguments. The positional arguments
passed via the ``setup()`` are *appended* to the original ones. The additional
keyword arguments are merged (updated) into the original keyword arguments. ::

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
the form ``setup<registry name>``::

    >>> container = Container()
    >>> registry.setupContainerValues(container)
    >>> container.data
    [1, 2]


HTML Analyzation Tools
----------------------

There is a set of helpful analyzation tools available.

    >>> from schooltool.testing import analyze

They are designed to ease the inspection of HTML and other testing output.


Pick an Element using an XPath expression
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Often you are only interested in a particular element or text. The
``queryHTML`` method allows you to specify an XPath query to pick out a
particular note. A list of all found nodes will be returned. The nodes will be
returned as serialized strings::

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

    >>> print analyze.queryHTML('/html/body/h1', html)[0]
    <h1>This is my page!</h1>

It works also with XHTML compliant documents::

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

    >>> print analyze.queryHTML('/html/body/h1', html)[0]
    <h1>This is my page!</h1>

``printQuery`` makes this even easier, by printing all nodes::

    >>> analyze.printQuery('/html/body/h1', html)
    <h1>This is my page!</h1>

    >>> html = '''
    ... <html>
    ...   <body>
    ...     <ul>
    ...       <li>One</li>
    ...       <li>Two</li>
    ...     </ul>
    ...   </body>
    ... </html>
    ... '''

    >>> analyze.printQuery('//li', html)
    <li>One</li>
    <li>Two</li>

``printQuery`` skips empty matches::

    >>> html = '''
    ... <ul>
    ...   <li>One</li>
    ...   <li>Two</li>
    ...   <li>
    ...     <b>Three</b>
    ...   </li>
    ...   <li>Four</li>
    ... </ul>
    ... '''

    >>> analyze.printQuery('//li/text()', html)
    One
    Two
    Four


Reportlab PDF story testing
---------------------------

Schooltool PDF reports utilize Reportlab platypus module.  A report is
built from a list of platypus flowables known as as 'story'.

Let's build a short pdf story::

    >>> from reportlab.lib.styles import ParagraphStyle
    >>> from reportlab.platypus.paragraph import Paragraph
    >>> from reportlab.platypus.flowables import PageBreak

    >>> style = ParagraphStyle(name='Test', fontName='Times-Roman')

    >>> story = [
    ...     Paragraph('Hello world', style),
    ...     PageBreak(),
    ...     Paragraph('A new page', style)]

There are several helpers for testing the stories.

    >>> from schooltool.testing.pdf import StoryXML

The tool aims to build a human readable XML representation of the
story.  There is a helper which prints the formatted XML::

    >>> StoryXML(story).printXML()
    <story>
    <Paragraph>Hello world</Paragraph>
    <PageBreak/>
    <Paragraph>A new page</Paragraph>
    </story>

As with HTML analyzation tools, there are helpers for XPath queries::

    >>> parser = StoryXML(story)

    >>> parser.printXML('//Paragraph')
    <Paragraph>Hello world</Paragraph>
    <Paragraph>A new page</Paragraph>

    >>> parser.query('//Paragraph')
    ['<Paragraph>Hello world</Paragraph>',
     '<Paragraph>A new page</Paragraph>']

If these helpers are not sufficient, we can use XML document directly::

    >>> parser.document
    <...ElementTree object ...>

    >>> for child in parser.document.getroot().iterchildren():
    ...     if child.text:
    ...        print child.text
    Hello world
    A new page

``StoryXML`` helpers also work on single platypus flowables::

    >>> flowable = Paragraph('Some text', style)

    >>> StoryXML(flowable).printXML()
    <story>
    <Paragraph>Some text</Paragraph>
    </story>


ZCML execution wrapper
----------------------

`ZCMLWrapper` is a simple tool for convenient execution of ZCML in your tests.

    >>> from schooltool.testing.setup import ZCMLWrapper
    >>> zcml = ZCMLWrapper()

Let's include a ZCML file that defines a new directive::

    >>> zcml.include('schooltool.testing.tests',
    ...              file='echodirective.zcml')

The new directive is under a namespace, so we cannot access it directly::

    >>> zcml.string('<echo message="Boo" />')
    Traceback (most recent call last):
    ...
    ZopeXMLConfigurationError: File "<string>", line 2.0
        ConfigurationError: ('Unknown directive', None, u'echo')

Note that line number is a bit off in string execution, this happens
because the string is wrapped in ``<configure>...</configure>``.

So, lets set the default namespace and execute again::

    >>> zcml.setUp(namespaces={'': 'http://schooltool.org/testing/tests'})

    >>> zcml.string('<echo message="Boo" />')
    Executing echo: Boo

You can use prefixed namespaces like this::

    >>> zcml.setUp(namespaces={
    ...     '': 'http://schooltool.org/testing/tests',
    ...     'test': 'http://schooltool.org/testing/tests'})

    >>> zcml.string('<test:echo message="Boo"/>')
    Executing echo: Boo

And you can even postpone ZCML action execution, if it's convenient
for your tests::

    >>> zcml.auto_execute = False

    >>> zcml.string('<echo message="First" echo_on_add="True"/>')
    Adding ZCML action: ('echo', u'First')

    >>> zcml.string('<echo message="Second" echo_on_add="True"/>')
    Adding ZCML action: ('echo', u'Second')

    >>> zcml.execute()
    Executing echo: First
    Executing echo: Second

Finally, each instance of the wrapper has it's own ``ConfigurationMachine``::

    >>> zcml.context
    <zope.configuration.config.ConfigurationMachine ...>

    >>> other = ZCMLWrapper()
    >>> other.setUp(namespaces={'': 'http://schooltool.org/testing/tests'})
    >>> other.string('<echo message="Boo" />')
    Traceback (most recent call last):
    ...
    ZopeXMLConfigurationError: File "<string>", line 2.0
        ConfigurationError: ('Unknown directive', ..., u'echo')

Let's include the directive again, but this time also show that we can also
pass module instead of it's dotted name::

    >>> import schooltool.testing.tests as the_tests
    >>> other.include(the_tests, file='echodirective.zcml')

    >>> other.string('<echo message="Boo" />')
    Executing echo: Boo

    >>> other.context is not zcml.context
    True


Fake modules and their globals
------------------------------

Sometimes it is useful to define a class or method inside a test,
replacing actual counterpart in some module for the test only.

    >>> from schooltool.testing import mock

    >>> @mock.module('schooltool.imaginarium')
    ... def greet():
    ...     print 'Hello world!'

A fake module was created.

    >>> from schooltool import imaginarium
    >>> print imaginarium
    <module 'schooltool.imaginarium' (built-in)>

With the injected function.

    >>> for a in sorted(dir(imaginarium)):
    ...     print '%s: %s' % (a, getattr(imaginarium, a))
    __doc__: None
    __name__: schooltool.imaginarium
    __package__: None
    greet: <function greet at ...>

    >>> imaginarium.greet()
    Hello world!

We can mock classes the same way too.

    >>> @mock.module(imaginarium)
    ... class Pond(object):
    ...    frog = 'Kermit'

    >>> pond = imaginarium.Pond()
    >>> print pond.frog
    Kermit

Note that some attributes of mocked objects are not updated:

    >>> print imaginarium.greet.__module__
    None

    >>> print imaginarium.Pond.__module__
    __builtin__

Oh, and we can set global variables too.

    >>> mock.fake_global(imaginarium, 'the_answer', 42)

    >>> imaginarium.the_answer
    42

After the test is finished, fake modules will be removed.

    >>> mock.restoreModules()

    >>> from schooltool.imaginarium import foo
    Traceback (most recent call last):
    ...
    ImportError: No module named imaginarium

