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
Devmode view support.
"""
from zope.app.exception.browser.unauthorized import Unauthorized
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.viewlet import viewlet

from schooltool.skin import flourish
from schooltool.securitypolicy.policy import CachingSecurityPolicy


DevmodeCSSViewlet = viewlet.CSSViewlet('devmode.css')

IntrospectorCSSViewlet = viewlet.CSSViewlet('introspector.css')


class DebugUnauthorized(Unauthorized):
    template = ViewPageTemplateFile('unauthorized.pt')
    next_url = ''

    @property
    def security_checks(self):
        cache = DebugSecurityPolicy.getCache(self.request)
        if cache is None:
            return
        for key, info in cache['debug_order']:
            obj, level = info
            permission = key[0]
            value = cache['perm'].get(key)
            try:
                text = repr(obj)
            except:
                text = '<object>'

            # XXX: quite hacky indeed, but will do for now.
            path = str(getattr(obj, '__name__', ''))
            parent = getattr(obj, '__parent__', None)
            seen = set([id(obj)])
            while parent is not None and id(parent) not in seen:
                seen.add(id(parent))
                path = str(getattr(parent, '__name__', '')) + '/' + path
                parent = getattr(parent, '__parent__', None)

            yield {
                'obj': obj,
                'permission': permission,
                'repr': text,
                'value': value,
                'level': level,
                'name': path,
                }

    def __call__(self):
        cache = DebugSecurityPolicy.getCache(self.request)
        sp_cache_enabled = None
        if cache is not None:
            sp_cache_enabled = cache['enabled']
            cache['enabled'] = False
        result = Unauthorized.__call__(self)
        if self.request.response.getStatus() in (302, 303):
            self.next_url = self.request.response.getHeader('location')
            self.request.response.setHeader('location', '')
            self.request.response.setStatus(200)
            result = self.template()
        if cache is not None:
            cache['enabled'] = sp_cache_enabled
        return result


class FlourishDebugUnauthorized(flourish.page.NoSidebarPage,
                                DebugUnauthorized):
    container_class = 'container extra-wide-container'

    def render(self, *args, **kw):
        return DebugUnauthorized.__call__(self)


class DebugSecurityPolicy(CachingSecurityPolicy):

    @classmethod
    def getCache(cls, participation):
        cache = CachingSecurityPolicy.getCache(participation)
        if (cache is not None and
            'debug_order' not in cache):
            cache['debug_order'] = []
            cache['debug_level'] = 0
        return cache

    def checkPermission(self, permission, obj):
        caches = filter(None, [self.getCache(p) for p in self.participations])
        levels = [cache['debug_level'] for cache in caches]
        perm = CachingSecurityPolicy.checkPermission(
            self, permission, obj)
        for cache, level in zip(caches, levels):
            cache['debug_level'] = level
        return perm

    def cache(self, participation, permission, obj, value):
        cache = self.getCache(participation)
        if cache is None or not cache['enabled']:
            return
        cache['debug_level'] += 1
        CachingSecurityPolicy.cache(
            self, participation, permission, obj, value)
        key = self.cachingKey(permission, obj)
        if (key is not None and
            key in cache['perm'] and
            key not in cache['debug_order']):
            extra_info = (obj, cache['debug_level'])
            cache['debug_order'].append((key, extra_info))
