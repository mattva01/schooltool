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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Flourish breadcrumbs.
"""

import zope.schema
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryMultiAdapter
from zope.interface import implements, Interface, Attribute
from zope.security import checkPermission
from zope.traversing.interfaces import IContainmentRoot
from zope.traversing.browser.absoluteurl import absoluteURL

from schooltool.skin.flourish.content import ContentProvider
from schooltool.skin.flourish import interfaces


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


class IBreadcrumb(IBreadcrumbInfo, interfaces.IContentProvider):

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

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.name)


class Breadcrumbs(ContentProvider):
    implements(IBreadcrumb)

    template = ViewPageTemplateFile('templates/breadcrumbs.pt')

    permission = "schooltool.view"

    @property
    def title(self):
        title_content = queryMultiAdapter(
            (self.context, self.request, self.view),
            interfaces.IContentProvider, 'title')
        if title_content is None:
            return None
        title = getattr(title_content, 'title', None)
        return title

    link = None

    def checkPermission(self):
        permission = self.permission
        if permission:
            if not checkPermission(permission, self.context):
                return False
        return True

    @property
    def url(self):
        if not self.checkPermission():
            return None
        context = self.context
        url = absoluteURL(context, self.request)
        link = self.link
        if link:
            url = '%s/%s' % (url, link)
        return url

    @property
    def crumb_parent(self):
        if getattr(self.context, '__parent__', None) is None:
            return None
        if IContainmentRoot.providedBy(self.context):
            return None
        return self.context.__parent__

    @property
    def follow_crumb(self):
        parent = self.crumb_parent
        if parent is None:
            return None
        breadcrumb = queryMultiAdapter(
            (parent, self.request, self.view),
            IBreadcrumb,
            name="",
            default=None)
        return breadcrumb

    @property
    def breadcrumbs(self):
        """List of breadcrumbs.
        root > child > child > this.
        """
        breadcrumbs = [BreadCrumbInfo(self.title, self.url)]
        follow = self.follow_crumb
        if follow is not None:
            breadcrumbs = follow.breadcrumbs + breadcrumbs
        return [b for b in breadcrumbs if b.name]

    def render(self, *args, **kw):
        return self.template(*args, **kw)


class PageBreadcrumbs(Breadcrumbs):
    implements(IBreadcrumb)

    @property
    def title(self):
        title = getattr(self.view, 'subtitle', None)
        title = title or getattr(self.view, 'title', None)
        return title

    url = None

    @property
    def crumb_parent(self):
        return self.context


class TitleBreadcrumb(Breadcrumbs):

    @property
    def title(self):
        return self.context.title
