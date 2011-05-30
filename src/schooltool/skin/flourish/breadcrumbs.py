#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
Flourish breadcrumbs.
"""

import zope.schema
from zope.component import queryMultiAdapter
from zope.interface import implements, Interface, Attribute
from zope.traversing.interfaces import IContainmentRoot
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.app.browser.content import ISchoolToolContentProvider
from schooltool.app.browser.content import ContentProvider
from schooltool.common.inlinept import InlinePageTemplate

from schooltool.common import SchoolToolMessage as _


class IBreadcrumbInfo(Interface):

    title = zope.schema.TextLine(
        title=u"Title",
        description=u"""
        The name of the breadcrumb.
        If there is not title, the breadcrumb should not be displayed.
        """,
        required=False)

    link = zope.schema.URI(
        title=u"URL",
        description=u"URL of the breadcrumb.",
        required=False)


class IBreadcrumb(IBreadcrumbInfo, ISchoolToolContentProvider):

    crumb_parent = Attribute(
        u"Suggested parent context for breadcrumb lookup.")

    follow_crumb = Attribute(
        u"The next crumb to follow.")

    breadcrumbs = Attribute(
        u"List of breadcrumbs in parent-to-this order.")


class BreadCrumbInfo(object):

    def __init__(self, name, url):
        self.name = name
        self.url = url


class Breadcrumbs(ContentProvider):
    implements(IBreadcrumb)

    template = InlinePageTemplate('''
      <ul class="breadcrumbs">
        <tal:block repeat="crumb view/breadcrumbs"
                   condition="crumb/title">
          <li tal:attributes="
                class python:repeat['crumb'].end() and 'last' or None">
            <a tal:condition="crumb/link"
               tal:attributes="href crumb/link"
               tal:content="crumb/name">
               [crumb with link]
            </a>
            <span tal:condition="not:crumb/link"
                  tal:content="crumb/name">
               [crumb without link]
            </span>
          </li>
        </tal:block>
    ''')

    @property
    def title(self):
        name = getattr(self.context, 'title', None)
        if name is None:
            name = getattr(self.context, '__name__', None)
        if name is None and IContainmentRoot.providedBy(self.context):
            name = _('SchoolTool')
        return name

    @property
    def link(self):
        return absoluteURL(self.context, self.request)

    @property
    def crumb_parent(self):
        if self.context.__parent__ is None:
            return None
        if IContainmentRoot.providedBy(self.context):
            return None
        return self.context.__parent__

    def follow_crumb(self):
        parent = self.crumb_parent
        if parent is None:
            return None
        breadcrumb = queryMultiAdapter(
            (parent, self.request, self.view),
            IBreadcrumb)
        return breadcrumb

    @property
    def breadcrumbs(self):
        """List of breadcrumbs.
        root > child > child > this.
        """
        breadcrumbs = [BreadCrumbInfo(self.title, self.link)]
        follow = self.follow_crumb
        if follow is not None:
            breadcrumbs = follow.breadcrumbs + breadcrumbs
        return breadcrumbs

    def render(self, *args, **kw):
        return self.template(*args, **kw)


class PageBreadcrumbs(Breadcrumbs):
    implements(IBreadcrumb)

    @property
    def breadcrumbs(self):
        crumb = BreadCrumbInfo(self.title, self.link)
        breadcrumbs = [crumb]
        if self.request.URL != self.link:
            breadcrumbs.append(BreadCrumbInfo(self.view.title, None))
        follow = self.follow_crumb
        if follow is not None:
            breadcrumbs = follow.breadcrumbs + breadcrumbs
        return breadcrumbs
