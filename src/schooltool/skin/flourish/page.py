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

from zope.cachedescriptors.property import Lazy
from zope.component import getMultiAdapter
from zope.interface import implements
from zope.publisher.browser import BrowserPage
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from schooltool.app.browser.content import IContentProviders
from schooltool.common.inlinept import InlinePageTemplate
from schooltool.skin.flourish.viewlet import Viewlet
from schooltool.skin.flourish import interfaces


class Page(BrowserPage):
    implements(interfaces.IPage)

    title = None
    subtitle = None

    template = ViewPageTemplateFile('templates/main.pt')
    page_template = ViewPageTemplateFile('templates/page.pt')
    content_template = None

    @Lazy
    def providers(self):
        providers = getMultiAdapter(
            (self.context, self.request, self),
            IContentProviders)
        return providers


class Refine(Viewlet):

    template = InlinePageTemplate('''
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
    title = None


class Content(Viewlet):

    template = InlinePageTemplate('''
      <div class="header"
           tal:define="actions context/schootlool:content/actions"
           tal:condition="actions"
           tal:content="structure actions">
        [action] [buttons]
      </div>
      <div class="body" tal:content="structure view/body_template">
        [ The content itself ]
      </div>
    ''')
    body_template = None


class Related(Viewlet):

    template = InlinePageTemplate('''
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
    title = None
