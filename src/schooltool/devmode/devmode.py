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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Devmode view support.
"""
from zope.app.exception.browser.unauthorized import Unauthorized
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.viewlet import viewlet
from zope.security.proxy import removeSecurityProxy

from schooltool.skin import flourish
from schooltool.securitypolicy.policy import CachingSecurityPolicy
from schooltool.app.browser import SchoolToolAPI


DevmodeCSSViewlet = viewlet.CSSViewlet('devmode.css')


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
            unproxied = removeSecurityProxy(obj)
            permission = key[0]
            try:
                text = repr(obj)
            except:
                text = '<object>'
            if getattr(unproxied, '_p_jar', None) is None:
                value = None
                text += ' (freshly created object, not in DB yet)'
            else:
                value = cache['perm'].get(key)

            # XXX: quite hacky indeed, but will do for now.
            path = str(getattr(unproxied, '__name__', ''))
            parent = getattr(unproxied, '__parent__', None)
            seen = set([id(unproxied)])
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


class DevmodeSchoolToolAPI(SchoolToolAPI):

    devmode = True


class ZODBObjectLoadStats(object):

    _setstate = None
    stopper = None # ("part of class name", enter pdb on nth loaded object)

    def __init__(self):
        self.LOADED = {}
        self.UNIQUE = {}
        self.IDS = {}

    def patch_setstate(self):
        if self._setstate is not None:
            return
        from ZODB.Connection import Connection
        old_setstate = self._setstate = Connection._setstate
        stopper = self.stopper
        def setstate(*args, **kw):
            obj = args[1]
            classname = str(obj.__class__)
            ids = self.IDS.setdefault(obj._p_oid, [])
            if (stopper is not None and
                stopper[0] in classname and
                (self.LOADED.get(classname, 0) + 1) == stopper[1]):
                import ipdb; ipdb.set_trace()
            res = old_setstate(*args, **kw)
            self.LOADED[classname] = self.LOADED.get(classname, 0) + 1
            ids.append((id(obj), obj))
            all = self.UNIQUE.setdefault(classname, set())
            oid = args[1]._p_oid
            if oid not in all:
                all.add(oid)
            return res
        Connection._setstate = setstate

    def unpatch_setstate(self):
        if self._setstate is None:
            return
        from ZODB.Connection import Connection
        Connection._setstate = self._setstate
        self._setstate = None

    def start(self):
        self.LOADED.clear()
        self.UNIQUE.clear()
        self.IDS.clear()
        self.patch_setstate()

    def stop(self):
        self.unpatch_setstate()

    def print_stats(self):
        res = ['-'*40]
        for key in sorted(self.LOADED):
            total = self.LOADED.get(key, 0)
            unique = len(self.UNIQUE.get(key, ()))
            res.append('%s total %s unique %s' % (key, total, unique))
        res.append('%d objects in total' % len(self.IDS))
        est_size = 0
        for objs in self.IDS.values():
            for obj in objs:
                est_size += obj[1]._p_estimated_size

        res.append('Estimated %.3f megs' % (est_size/1000000.))
        res.append('-'*40)
        print '\n'.join(res)


def patch_publisher():
    import zope.app.wsgi
    old_publisher = zope.app.wsgi.publish
    def publish(*args, **kw):
        stats = ZODBObjectLoadStats()
        stats.start()
        result = old_publisher(*args, **kw)
        stats.stop()
        if stats.IDS:
            stats.print_stats()
        return result
    zope.app.wsgi.publish = publish
    return old_publisher


def launch_pdb_on_exception():
    import zope.publisher.publish
    import sys
    try:
        import ipdb as pdb
    except ImportError:
        import pdb
    olde_debug_call = zope.publisher.publish.debug_call
    def interceptor(*args, **kw):
        try:
            result = olde_debug_call(*args, **kw)
        except:
            type, value, tb = sys.exc_info()
            pdb.post_mortem(tb)
            raise
        return result
    zope.publisher.publish.debug_call = interceptor

#launch_pdb_on_exception()
#patch_publisher()
