#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2005 Shuttleworth Foundation
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
Context-Help related views.

$Id$
"""

__docformat__ = 'reStructuredText'

import zope.interface
from zope import contentprovider
from zope.app import onlinehelp
from zope.app.publisher import browser
from zope.app.pagetemplate import ViewPageTemplateFile
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IBrowserView
from zope.app.onlinehelp.browser.tree import OnlineHelpTopicTreeView
from zope.component import getMultiAdapter
from zope.traversing.api import getName, getParent
from zope.traversing.api import joinPath
from zope.i18n import translate


def sortById(x,y):
    return cmp(x.id, y.id)

class SchoolToolOnlineHelpTopicTreeView(OnlineHelpTopicTreeView):
    """Online help topic tree view."""

    def renderItemList(self, topic, intend):
        """Render a 'ul' elements as childs of the 'ul' tree."""
        res = []
        intend = intend + "  "
        res.append('%s<ul>' % intend)

        for item in sorted(topic.getSubTopics(), sortById):

            # expand if context is in tree
            if self.isExpanded(topic):
                res.append('  %s<li class="expand">' % intend)
            else:
                res.append('  %s<li>' % intend)

            res.append(self.renderLink(item))
            if len(item.getSubTopics()) > 0:
                res.append('    %s%s' % (
                    self.renderItemList(item, intend), intend))
            res.append('  %s</li>' % intend)
        res.append('%s</ul>' % intend)

        return '\n'.join(res)

    def renderTree(self, root):
        """Render an ordered list 'ul' tree with a class name 'tree'."""
        res = []
        intend = "  "
        res.append('<ul class="tree" id="tree">')
        for topic in sorted(root.getSubTopics(), sortById):
            # we don't show the default zope help
            if topic.id in ['dev', 'ui', 'welcome', 'samples']:
                continue

            item = self.renderLink(topic)

            # expand if context is in tree
            if self.isExpanded(topic):
                res.append('  <li class="expand">%s' % item)
            else:
                res.append('  <li>%s' % item)

            if len(topic.getSubTopics()) > 0:
                res.append(self.renderItemList(topic, intend))
            res.append('  </li>')

        res.append('<ul>')

        return '\n'.join(res)

    # This is a workaround for a bug in zope.app.onlinehelp
    # See https://bugs.launchpad.net/schooltool/+bug/372606
    def renderLink(self, topic):
        """Render a href element."""
        title = translate(topic.title, context=self.request,
                default=topic.title)
        if topic.parentPath:
            url = joinPath(topic.parentPath, topic.id)
        else:
            url = topic.id
        return '<a href="%s/++help++/%s">%s</a>\n' % ( 
            self.request.getApplicationURL(), url, title)


class ContextHelpView(BrowserView):

    def __init__(self, context, request):
        super(ContextHelpView, self).__init__(context, request)
        self.topic = None

    def getContextualTopicView(self):
        """Retrieve and render the source of a context help topic """
        topic = self.contextHelpTopic
        view = getMultiAdapter((topic, self.request), name='index.html')
        return view()

    @property
    def contextHelpTopic(self):
        """Retrieve a help topic based on the context of the help namespace."""
        if self.topic is not None:
            return self.topic

        help_context = self.context.context
        self.topic = None
        if IBrowserView.providedBy(help_context):
            name = getName(help_context)
            help_context = getParent(help_context)
        else:
            name = browser.queryDefaultViewName(help_context, self.request)
            if name is None:
                return self.topic

        self.topic = onlinehelp.getTopicFor(help_context, name)

        return self.topic


class HelpLink(object):
    """Help Link Content Provider"""

    zope.interface.implements(contentprovider.interfaces.IContentProvider)

    template = ViewPageTemplateFile('helplink.pt')

    def __init__(self, context, request, view):
        self.__parent__ = view
        self.context, self.request = context, request
        self.show = False
        self.title = 'Context Help' # XXX mg: i18n?

    def update(self):
        help = onlinehelp.helpNamespace(
            self.__parent__, self.request).traverse('', None)
        helpView = ContextHelpView(help, self.request)
        if helpView.contextHelpTopic is not None:
            self.show = True

    def render(self):
        if self.show:
            return self.template()
        return u''
