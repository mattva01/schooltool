##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Interface that describes the 'macros' attribute of a PageTemplate.

$Id$
"""
from zope.interface import Interface, Attribute


class IPageTemplate(Interface):
    """Objects that can render page templates
    """

    def __call__(*args, **kw):
        """Render a page template

        The argument handling is specific to particular
        implementations.  Normally, however, positional arguments are
        bound to the top-level `args` variable and keyword arguments
        are bound to the top-level `options` variable.
        """

    def pt_edit(source, content_type):
        """Set the source and content type
        """

    def pt_errors(namespace):
        """Return a sequence of strings that describe errors in the template.

        The errors may occur when the template is compiled or
        rendered.

        `namespace` is the set of names passed to the TALES expression
        evaluator, similar to what's returned by pt_getContext().

        This can be used to let a template author know what went wrong
        when an attempt was made to render the template.
        """

    def pt_warnings():
        """Return a sequence of warnings from the parser.

        This can be useful to present to the template author to
        indication forward compatibility problems with the template.
        """

    def read():
        """Get the template source
        """

    macros = Attribute("An object that implements the __getitem__ "
                       "protocol, containing page template macros.")

class IPageTemplateSubclassing(IPageTemplate):
    """Behavior that may be overridden or used by subclasses
    """

    
    def pt_getContext(**kw):
        """Compute a dictionary of top-level template names
        
        Responsible for returning the set of
        top-level names supported in path expressions
        
        """

    def pt_getEngine():
        """Returns the TALES expression evaluator.
        """

    def pt_getEngineContext(namespace):
        """Return an execution context from the expression engine."""

    def __call__(*args, **kw):
        """Render a page template

        This is sometimes overridden to provide additional argument
        binding.
        """
        
    def pt_source_file():
        """return some text describing where a bit of ZPT code came from.

        This could be a file path, a object path, etc.
        """

    def _cook():
        """Compile the source

        Results are saved in the variables: _v_errors, _v_warnings,
        _v_program, and _v_macros, and the flag _v_cooked is set.
        """
    def _cook_check():
        """Compiles the source if necessary

        Subclasses might override this to influence the decision about
        whether compilation is necessary.
        """
        
    content_type = Attribute("The content-type of the generated output")

    expand = Attribute(
        "Flag indicating whether the read method should expand macros")
