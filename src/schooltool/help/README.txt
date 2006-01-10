=============================
Context-Sensitive Help System
=============================

This package provides a context-sensitive help system for SchoolTool. It is
heavily based on the Zope 3 help system, but makes some different policy
decisions.

The first object the user will interact with is the help link. The help link
is a content provider that inserts a link with the text "Help" in the tools
bar of the standard SchoolTool O-wrap.

  >>> import zope.interface
  >>> class IPerson(zope.interface.Interface):
  ...    pass

  >>> class Person(object):
  ...     zope.interface.implements(IPerson)
  >>> person = Person()

  >>> from zope.publisher.browser import TestRequest
  >>> request = TestRequest()

  >>> from zope.app.publisher.browser import BrowserView
  >>> class View(BrowserView):
  ...     __name__ = u'index.html'
  >>> view = View(person, request)

  >>> from zope.app.testing import setup
  >>> setup.setUpTraversal()

The helplink is instantiated with the typical content provider API:

  >>> from schooltool.help import browser
  >>> helplink = browser.HelpLink(person, request, view)

We can now render the link:

  >>> helplink.update()
  >>> helplink.render()
  u''

We get an empty string. This is because there is no help topic registered for
this view yet. The help link is only shown, if a contextual help is really
available. Let's now register a helptopic for the view:

  >>> import os, tempfile
  >>> helpfile = tempfile.mktemp('.txt')
  >>> open(helpfile, 'w').write('''
  ... The person's index view shows the default info about the person.
  ... ''')

  >>> from zope.app.onlinehelp import globalhelp
  >>> globalhelp.registerHelpTopic(
  ...     '', u'person', u'Person Overview', helpfile, IPerson, u'index.html')

Now the helplink should produce some output:

  >>> helplink.update()
  >>> print helplink.render()
  |
  <a id="tools-help"
     href="javascript:popUp('http://127.0.0.1/++help++/@@contexthelp.html')"
     title="Context Help">Help</a>
  <BLANKLINE>

Once the link is provided, it needs to end somewhere. This package also
reimplements the ``contexthelp.html`` view. As you can see, it is a view on
the ``++help++`` namespace. This namespace is always available, and it can
either be added after the view name or the context object directly. In the
latter case, the the context help should look up the default view and use it
to find the help topic.

The first step is to setup the help topic views ...

  >>> class SimpleOnlineHelpTopicView(BrowserView):
  ...     def __call__(self):
  ...         return self.context.source

  >>> import zope.component
  >>> from zope.app.onlinehelp.interfaces import IOnlineHelpTopic
  >>> zope.component.provideAdapter(
  ...     SimpleOnlineHelpTopicView, (IOnlineHelpTopic, TestRequest),
  ...     zope.interface.Interface, name=u'index.html')

and to register our view:

  >>> zope.component.provideAdapter(
  ...     View, (IPerson, TestRequest), zope.interface.Interface,
  ...     name=u'index.html')

Then we create the onlinehelp namespace and create the context help from our
view:

  >>> from zope.app.onlinehelp import helpNamespace
  >>> helpSystem = helpNamespace(view).traverse('', None)

  >>> contextHelp = browser.ContextHelpView(helpSystem, request)
  >>> contextHelp.getContextualTopicView()
  u"\nThe person's index view shows the default info about the person.\n"

Also, if the help namespace is looked up on the person, we should get the same
result, since the 'index.html' view is the default view:

  >>> from zope.component.interfaces import IDefaultViewName
  >>> zope.component.provideAdapter(
  ...     'index.html', (IPerson, TestRequest), IDefaultViewName)

  >>> helpSystem = helpNamespace(person).traverse('', None)

  >>> contextHelp = browser.ContextHelpView(helpSystem, request)
  >>> contextHelp.getContextualTopicView()
  u"\nThe person's index view shows the default info about the person.\n"
