Page Templates

  Introduction

     Page Templates provide an elegant templating mechanism that
     achieves a clean separation of presentation and application
     logic while allowing for designers to work with templates
     in their visual editing tools (FrontPage, Dreamweaver, GoLive,
     etc.).

     This document focuses on usage of Page Templates outside of
     a Zope context, it does *not* explain how to write page templates
     as there are several resources on the web which do so.

  Dependencies

    Zope3 Package Dependencies

      - zope.tal (Template Attribute Language)

      - zope.talInterface

      - ZTUtils (batching utilities for zpt)

      - The standard logging package ("logging") from Python 2.3.

  Simple Usage

    Using PageTemplates outside of Zope3 is very easy and straight
    forward. a quick example::

      >>> from zope.pagetemplate.pagetemplatefile import PageTemplateFile
      >>> my_pt = PageTemplateFile('hello_world.pt')
      >>> my_pt()
      u'<html><body>Hello World</body></html>'

  Setting Up Contexts

    Rendering a page template without binding data to is not very
    interesting. By default keyword arguments you pass in page
    templates appear in the options namespace.

    pt_getContext(**keywords)
        Should ignore keyword arguments that it doesn't care about,
        and construct the namespace passed to the TALES expression
        engine.  This method is free to use the keyword arguments it
        receives.

    pt_render(namespace, source=0)
        Responsible the TAL interpreter to perform the rendering.  The
        namespace argument is a mapping which defines the top-level
        namespaces passed to the TALES expression engine.

  Narrative (Subclassing PageTemplates)

    Lets say we want to alter page templates such that keyword
    arguments appear as top level items in the namespace. we can
    subclass page template and alter the default behavior of
    pt_getContext to add them in::

      from zope.pagetemplate.pagetemplate import PageTemplate

      class mypt(PageTemplate):
          def pt_getContext(self, args=(), options={}, **kw):
             rval = PageTemplate.pt_getContext(self, args=args)
             options.update(rval)
             return options

      class foo:
          def getContents(self): return 'hi'

    So now we can bind objects in a more arbitrary fashion, like
    the following::

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

  Author

    Kapil Thangavelu <hazmat at objectrealms.net>
