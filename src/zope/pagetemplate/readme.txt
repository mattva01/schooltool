==============
Page Templates
==============

:Author:  Kapil Thangavelu <hazmat at objectrealms.net>

Introduction
------------

Page Templates provide an elegant templating mechanism that achieves a
clean separation of presentation and application logic while allowing
for designers to work with templates in their visual editing tools
(FrontPage, Dreamweaver, GoLive, etc.).

This document focuses on usage of Page Templates outside of a Zope
context, it does *not* explain how to write page templates as there
are several resources on the web which do so.

Simple Usage
------------

Using Page Templates outside of Zope3 is very easy and straight
forward.  A quick example::

  >>> from zope.pagetemplate.pagetemplatefile import PageTemplateFile
  >>> my_pt = PageTemplateFile('hello_world.pt')
  >>> my_pt()
  u'<html><body>Hello World</body></html>'

Subclassing PageTemplates
-------------------------

Lets say we want to alter page templates such that keyword arguments
appear as top level items in the namespace.  We can subclass
`PageTemplate` and alter the default behavior of `pt_getContext()` to
add them in::

  from zope.pagetemplate.pagetemplate import PageTemplate

  class mypt(PageTemplate):
      def pt_getContext(self, args=(), options={}, **kw):
         rval = PageTemplate.pt_getContext(self, args=args)
         options.update(rval)
         return options

  class foo:
      def getContents(self): return 'hi'

So now we can bind objects in a more arbitrary fashion, like the
following::

  template = """
  <html>
  <body>
  <b tal:replace="das_object/getContents">Good Stuff Here</b>
  </body>
  </html>
  """

  pt = mypt()
  pt.write(template)
  pt(das_object=foo())

See interfaces.py.
