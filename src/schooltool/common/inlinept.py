#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2009 Shuttleworth Foundation
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
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""
Inline page templates
"""

from zope.pagetemplate.engine import TrustedAppPT
from zope.pagetemplate.pagetemplate import PageTemplate
from zope.browserpage.viewpagetemplatefile import BoundPageTemplate


class InlineTemplateBase(TrustedAppPT, PageTemplate):

    def __init__(self, source, content_type=None):
        self.source = source
        if content_type is not None:
            self.content_type = content_type
        self.pt_edit(source, self.content_type)


class InlinePageTemplate(InlineTemplateBase):
    """Inline page template.

    Use it like this:

        >>> pt = InlinePageTemplate('''
        ... <ul>
        ...   <li tal:repeat="item items" tal:content="item">(item)</li>
        ... </ul>
        ... ''')
        >>> print pt(items=['a', 'b', 'c']).strip()
        <ul>
          <li>a</li>
          <li>b</li>
          <li>c</li>
        </ul>

    """

    def pt_getContext(self, args, options):
        namespace = {'template': self, 'args': args, 'nothing': None}
        namespace.update(self.pt_getEngine().getBaseNames())
        namespace.update(options)
        return namespace


class InlineViewPageTemplate(InlineTemplateBase):
    """Inline page template for views.

    Use it like this:

        >>> class View(object):
        ...     template = InlineViewPageTemplate('''
        ...         <p tal:content="context"></p>
        ...         <p>Page <tal:c content="request/page"></tal:c></p>
        ...         <p tal:content="view"></p>
        ...         <ul>
        ...           <li tal:repeat="item options/items"
        ...               tal:content="item">
        ...           </li>
        ...         </ul>
        ...         ''')
        ...     def __init__(self, context, request):
        ...         self.context = context
        ...         self.request = request
        ...     __repr__ = lambda self: '%s object' % self.__class__.__name__

        >>> from zope.publisher.browser import TestRequest
        >>> view = View('the context', TestRequest(form={'page': 5}))
        >>> print view.template(items=['a', 'b']).strip()
        <p>the context</p>
        <p>Page 5</p>
        <p>View object</p>
        <ul>
          <li>a</li>
          <li>b</li>
        </ul>

    """

    def pt_getContext(self, instance, **kw):
        namespace = InlineTemplateBase.pt_getContext(self, **kw)
        namespace.update({
                'context': instance.context,
                'request': instance.request,
                'view': instance,
                })
        return namespace

    def __call__(self, instance, *args, **keywords):
        namespace = self.pt_getContext(
            instance, args=args, options=keywords)
        s = self.pt_render(
            namespace,
            showtal=getattr(instance.request.debug, 'showTAL', False),
            )
        response = instance.request.response
        if not response.getHeader("Content-Type"):
            response.setHeader("Content-Type", self.content_type)
        return s

    def __get__(self, instance, type):
        return BoundPageTemplate(self, instance)
