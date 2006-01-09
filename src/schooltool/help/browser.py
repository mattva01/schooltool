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
from zope.app import zapi
from zope.app.publisher import browser, interfaces
from zope.app.pagetemplate import ViewPageTemplateFile


class ContextHelpView(browser.BrowserView):

    def __init__(self, context, request):
        super(ContextHelpView, self).__init__(context, request)
        self.topic = None

    def getContextualTopicView(self):
        """Retrieve and render the source of a context help topic """
        topic = self.contextHelpTopic
        view = zapi.getMultiAdapter((topic, self.request), name='index.html')
        return view()

    @property
    def contextHelpTopic(self):
        """Retrieve a help topic based on the context of the
        help namespace.
        """
        if self.topic is not None:
            return self.topic

        help_context = self.context.context
        self.topic = None
        if interfaces.browser.IBrowserView.providedBy(help_context):
            name = zapi.getName(help_context)
            help_context = zapi.getParent(help_context)
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
        self.title = 'Context Help'

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
