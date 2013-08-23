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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Security description views for SchoolTool security policy.
"""

from zope.publisher.browser import BrowserView
from zope.component import queryMultiAdapter
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.traversing.browser import absoluteURL

from schooltool.securitypolicy.metaconfigure import getCrowdsUtility
from schooltool.securitypolicy.metaconfigure import getDescriptionUtility
from schooltool.securitypolicy.crowds import getCrowdDescription
from schooltool.securitypolicy.crowds import collectCrowdDescriptions
from schooltool.common.inlinept import InlinePageTemplate

from schooltool.common import SchoolToolMessage as _


class CrowdDescriptionSnippetBase(BrowserView):

    template = None

    def __init__(self, description, view, request, crowd, action, group):
        self.context = description
        self.view = view
        self.request = request
        self.crowd = crowd
        self.action = action
        self.group = group

    def empty(self):
        return False

    def snippets(self):
        if self.empty():
            return []
        content = self.template(
            view=self, context=self.context, request=self.request)
        return [content.strip()]


class CrowdDescriptionSnippets(CrowdDescriptionSnippetBase):

    template = InlinePageTemplate('''
    <p tal:content="view/context/description" />
    ''')

    def empty(self):
        return not self.context.description.strip()


class AggregatedSnippets(CrowdDescriptionSnippetBase):

    def snippets(self):
        descriptions = self.context.getDescriptions()
        result = []
        snippets = [
            queryMultiAdapter(
                (d, self.view, self.request, d.crowd, d.action, d.group),
                default=None)
            for d in descriptions]
        for collection in snippets:
            if collection:
                result.extend(collection.snippets())
        return result


class AccessSettingSnippets(CrowdDescriptionSnippetBase):

    template = ViewPageTemplateFile('templates/access_setting_snippet.pt')

    @property
    def setting(self):
        return self.crowd.settings.getSetting(self.crowd.setting_key)

    @property
    def status(self):
        status = bool(self.setting.getValue())
        return status and _("Enabled") or _("Disabled")


class AdministrationSnippets(CrowdDescriptionSnippetBase):
    """A way to display short crowd description with a link to a legend.

    Not a good way to do that.
    """

    description = _(u'School administration')
    template = InlinePageTemplate('''
    <p>
      <tal:block content="view/description" />
      <a href="#legend_administration">[1]</a>
    </p>
    ''')


class SecurityDescriptions(BrowserView):

    def done_link(self):
        return '%s/settings' % absoluteURL(self.context, self.request)

    def legends(self):
        # XXX: hacky legend builder (for eye-candy)
        factories = getCrowdsUtility().factories
        crowd = factories['administration'](None)
        description = getCrowdDescription(crowd, None, None)
        if description is None:
            return
        collection = queryMultiAdapter(
            (description, None, self.request,
             description.crowd, description.action, description.group),
            default=None)
        if collection is None:
            return
        yield {
            'idx': '1',
            'description': AdministrationSnippets.description,
            'href': 'legend_administration',
            'snippets': collection.snippets(),
            }

    def getDescriptionSnippets(self, description):
        if description is None:
            return []
        collection = queryMultiAdapter(
            (description, self, self.request,
             description.crowd, description.action, description.group),
            default=None)
        if collection is not None:
            return collection.snippets()
        return []

    def getCrowdSnippets(self, action):
        descriptions = collectCrowdDescriptions(action)
        snippets = []
        for description in descriptions:
            snippets.append(self.getDescriptionSnippets(description))
        return snippets

    def getActions(self, group):
        descriptions = getDescriptionUtility()
        action_dict = descriptions.actions_by_group.get(group.__name__, {})
        actions = sorted(action_dict.values(),
                         key=lambda a: '%d %s' % (a.order, a.__name__))
        for action in actions:
            snippets = self.getCrowdSnippets(action)

            yield {
                'action': action,
                'crowds': snippets,
                }

    def getGroups(self):
        util = getDescriptionUtility()
        groups = sorted(util.groups.values(),
                        key=lambda g: g.__name__)
        for group in groups:
            actions = self.getActions(group)
            yield {'group': group, 'actions': list(actions)}

    def update(self):
        self.groups = list(self.getGroups())


