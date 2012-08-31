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
SchoolTool flourish pages.
"""
import re
import urllib

from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.cachedescriptors.property import Lazy
from zope.component import getMultiAdapter, queryMultiAdapter
from zope.interface import implements
from zope.publisher.browser import BrowserPage
from zope.publisher.interfaces import NotFound
from zope.browser.interfaces import IBrowserView
from zope.traversing.api import getParent
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.traversing.browser.absoluteurl import absoluteURL, AbsoluteURL

from schooltool.app.interfaces import ISchoolToolApplication
from schooltool.app.interfaces import IApplicationTabs
from schooltool.common.inlinept import InlineViewPageTemplate
from schooltool.common.inlinept import InheritTemplate
from schooltool.skin.flourish.viewlet import Viewlet, ViewletManager
from schooltool.skin.flourish.viewlet import ManagerViewlet
from schooltool.skin.flourish import interfaces
from schooltool.traverser.traverser import PluggableTraverser, TraverserPlugin


class Page(BrowserPage):
    implements(interfaces.IPage)

    title = None
    subtitle = None
    has_header = True
    page_class = 'page'
    container_class = 'container'

    template = ViewPageTemplateFile('templates/main.pt')
    page_template = ViewPageTemplateFile('templates/page.pt')
    content_template = None

    def publishTraverse(self, request, name):
        traverser = PluggableTraverser(self, request)
        return traverser.publishTraverse(request, name)

    @Lazy
    def providers(self):
        providers = getMultiAdapter(
            (self.context, self.request, self),
            interfaces.IContentProviders)
        return providers

    def update(self):
        pass

    def render(self, *args, **kw):
        return self.template(*args, **kw)

    def __call__(self, *args, **kw):
        self.update()
        if self.request.response.getStatus() in [300, 301, 302, 303,
                                                 304, 305, 307]:
            return u''
        result = self.render(*args, **kw)
        return result


class PageContentTraverser(TraverserPlugin):

    def __init__(self, view, request):
        self.view = view
        self.context = view.context
        self.request = request

    def traverse(self, name):
        parts = queryMultiAdapter(
            (self.context, self.request, self.view),
            interfaces.IContentProvider, name)
        if parts is None:
            raise NotFound(self.view, name, self.request)
        return parts


class PageAbsoluteURL(AbsoluteURL):

    def __str__(self):
        view = self.context
        request = self.request

        url = str(getMultiAdapter((view.context, request),
                                                 IAbsoluteURL))
        name = getattr(view, '__name__', None)
        if name:
            url += '/@@' + urllib.quote(name.encode('utf-8'), '@+')
        return url


class NoSidebarPage(Page):
    container_class = 'container extra-wide-container'

    page_template = ViewPageTemplateFile('templates/page_nosidebar.pt')


class WideContainerPage(Page):
    container_class = 'container widecontainer'


class ContentViewletManager(ViewletManager):
    template = InlineViewPageTemplate("""
        <tal:block repeat="viewlet view/viewlets">
          <div class="content"
               tal:define="rendered viewlet;
                           stripped rendered/strip|nothing"
               tal:condition="stripped"
               tal:content="structure stripped">
          </div>
        </tal:block>
    """)

    def render(self, *args, **kw):
        if not self.viewlets:
            return ''
        result = ViewletManager.render(self, *args, **kw)
        if result is not None:
            return result.strip()


class DisabledViewlet(Viewlet):

    def render(self, *args, **kw):
        return ''


class Refine(Viewlet):

    template = InlineViewPageTemplate('''
      <div class="header"
           tal:condition="view/title"
           tal:content="view/title">
        [ Filter title ]
      </div>
      <div class="body" tal:content="structure view/body_template">
        [ options ]
      </div>
    ''')
    body_template = None
    render = lambda self, *a, **kw: self.template(*a, **kw)
    title = None


class Content(Viewlet):
    template = ViewPageTemplateFile('templates/page_content.pt')
    body_template = None
    render = lambda self, *a, **kw: self.template(*a, **kw)


class Related(Viewlet):

    template = InlineViewPageTemplate('''
      <div class="header"
           tal:condition="view/title"
           tal:content="view/title">
        [ Title ]
      </div>
      <div class="body" tal:content="structure view/body_template">
        [ Related info ]
      </div>
    ''')

    body_template = None
    render = lambda self, *a, **kw: self.template(*a, **kw)
    title = None


def getViewletViewName(context, request, view, manager):
    return getattr(view, '__name__', None)


def getViewParentActiveViewletName(context, request, view, manager):
    parent = getattr(view, 'view', None)
    if parent is None:
        return None
    name = queryMultiAdapter(
        (context, request, parent, manager),
        interfaces.IActiveViewletName,
        name='',
        default=None)
    return name


def getParentActiveViewletName(context, request, view, manager):
    parent = getParent(context)
    if parent is None:
        return None
    name = queryMultiAdapter(
        (parent, request, view, manager),
        interfaces.IActiveViewletName,
        name='',
        default=None)
    return name


class ListNavigationBase(object):
    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class"
            tal:condition="view/items">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)
    list_class = None

    @Lazy
    def all_items(self):
        result = []
        active = self.active_viewlet
        for viewlet in self.viewlets:
            html_classes = []
            if viewlet.__name__ == active:
                html_classes.append('active')
            viewlet_class = getattr(viewlet, 'html_class', None)
            if viewlet_class:
                html_classes.append(viewlet_class)
            result.append({
                'class': ' '.join(html_classes) or None,
                'viewlet': viewlet,
                'content': viewlet(),
                })
        return result

    @Lazy
    def items(self):
        result = [item for item in self.all_items
                  if item['content'] and item['content'].strip()]
        return result

    @Lazy
    def active_viewlet(self):
        view = self.view
        name = queryMultiAdapter(
            (view.context, view.request, view, self),
            interfaces.IActiveViewletName,
            name='',
            default=None)
        return name

    @property
    def active(self):
        name = self.active_viewlet
        return(name and name in self.order)


class ListNavigationContent(ListNavigationBase, ViewletManager):
    pass


class ListNavigationViewlet(ListNavigationBase, ManagerViewlet):
    pass


class HeaderNavigationManager(ListNavigationContent):
    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)
    list_class = "navigation"

    @Lazy
    def viewlets(self):
        if self.cache is None:
            self.collect()
        app = ISchoolToolApplication(None)
        apptabs = IApplicationTabs(app)
        return [self[key] for key in self.order if apptabs.get(key, True)]


class SecondaryNavigationManager(ListNavigationContent):
    list_class = "second-nav"


class TertiaryNavigationManager(ListNavigationContent):
    template = InlineViewPageTemplate("""
        <ul tal:attributes="class view/list_class"
            tal:condition="view/items">
          <li tal:repeat="item view/items"
              tal:attributes="class item/class"
              tal:content="structure item/viewlet">
          </li>
        </ul>
    """)

    @property
    def list_class(self):
        related_manager = queryMultiAdapter(
            (self.context, self.request, self.view),
            interfaces.IContentProvider,
            'page_related')
        # XXX: this check of viewlets might not be safe
        if related_manager is not None and related_manager.viewlets:
            return 'third-nav third-nav-narrow'
        return 'third-nav'


class PageNavigationManager(ListNavigationContent):
    list_class = "navigation"

    def render(self, *args, **kw):
        if not self.active:
            return ''
        return ViewletManager.render(self, *args, **kw)


class RefineLinksViewlet(Refine, ListNavigationViewlet):
    list_class = "filter"
    body_template = InheritTemplate(ListNavigationBase.template)

    def render(self, *args, **kw):
        if not self.items:
            return ''
        return Refine.render(self, *args, **kw)


class IHTMLHeadManager(interfaces.IViewletManager):
    pass


class IHeaderNavigationManager(interfaces.IViewletManager):
    pass


class ISecondaryNavigationManager(interfaces.IViewletManager):
    pass


class ITertiaryNavigationManager(interfaces.IViewletManager):
    pass


class IPageNavigationManager(interfaces.IViewletManager):
    pass


class IPageRefineManager(interfaces.IViewletManager):
    pass


class IPageContentManager(interfaces.IViewletManager):
    pass


class IContentActionsManager(interfaces.IViewletManager):
    pass


class IPageRelatedManager(interfaces.IViewletManager):
    pass


class LinkViewlet(Viewlet):
    template = InlineViewPageTemplate('''
    <tal:block define="url view/url">
      <a tal:condition="url"
         tal:attributes="href view/url"
         tal:content="view/title"></a>
      <span tal:condition="not:url"
            tal:content="view/title"></span>
    </tal:block>
    ''')

    title = None

    @property
    def enabled(self):
        return bool(self.title)

    @property
    def link(self):
        if not self.__name__:
            return None
        return self.__name__

    @property
    def url(self):
        link = self.link
        if not link:
            return None
        return "%s/%s" % (absoluteURL(self.context, self.request),
                          self.link)

    def render(self, *args, **kw):
        if not self.enabled:
            return ''
        return self.template(*args, **kw)


_invalid_html_id_characters = re.compile('[^a-zA-Z0-9-._]')


def sanitize_id(html_id):
    if not html_id:
        return html_id
    html_id = html_id.encode('punycode')
    html_id = _invalid_html_id_characters.sub(
        lambda m: ':'+str(ord(m.group(0))), html_id)
    if not html_id[0].isalpha():
        html_id = 'i' + html_id
    return html_id

def generic_viewlet_html_id(viewlet, prefix=''):
    parent = viewlet.manager.__parent__
    parents = []
    while (parent is not None and
           IBrowserView.providedBy(parent)):
        name = getattr(parent, '__name__', None)
        parents.append(str(name))
        parent = parent.__parent__
    name_list = ([str(viewlet.__name__),
                  getattr(viewlet.manager, '__name__', 'manager')] +
                 parents[:-1] +
                 [prefix])
    return sanitize_id('-'.join(reversed(name_list)))


class LinkIdViewlet(LinkViewlet):
    template = InlineViewPageTemplate('''
    <tal:block define="url view/url">
      <a tal:condition="url"
         tal:attributes="href view/url;
                         id view/html_id"
         tal:content="view/title"></a>
      <span tal:condition="not:url"
            tal:attributes="id view/html_id"
            tal:content="view/title"></span>
    </tal:block>
    ''')

    @property
    def html_id(self):
        return generic_viewlet_html_id(self, 'LinkIdViewlet')


class SimpleModalLinkViewlet(LinkIdViewlet):
    template = InlineViewPageTemplate('''
    <tal:block define="url view/url">
      <a tal:condition="url"
         href="#"
         tal:attributes="id view/html_id;
                         onclick view/onclick"
         tal:content="view/title"></a>
      <span tal:condition="not:url"
            tal:attributes="id view/html_id"
            tal:content="view/title"></span>
    </tal:block>
    ''')

    @property
    def onclick(self):
        return "return ST.dialogs.open_modal_form('%s', '%s');" % (
            self.url, self.html_id+'-container')


class ModalFormLinkViewlet(LinkIdViewlet):
    template = ViewPageTemplateFile('templates/modal_form_link.pt')

    @property
    def form_container_id(self):
        return '%s-container' % self.html_id
