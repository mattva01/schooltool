##############################################################################
#
# Copyright (c) 2002, 2003 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Schema loader utility."""

import os.path
import sys
import urllib
import urllib2

import ZConfig
import ZConfig.cfgparser
import ZConfig.datatypes
import ZConfig.matcher
import ZConfig.schema
import ZConfig.url

try:
    True
except NameError:
    True = 1
    False = 0


def loadSchema(url):
    return SchemaLoader().loadURL(url)

def loadSchemaFile(file, url=None):
    return SchemaLoader().loadFile(file, url)

def loadConfig(schema, url, overrides=()):
    return _get_config_loader(schema, overrides).loadURL(url)

def loadConfigFile(schema, file, url=None, overrides=()):
    return _get_config_loader(schema, overrides).loadFile(file, url)


def _get_config_loader(schema, overrides):
    if overrides:
        from ZConfig import cmdline
        loader = cmdline.ExtendedConfigLoader(schema)
        for opt in overrides:
            loader.addOption(opt)
    else:
        loader = ConfigLoader(schema)
    return loader


class BaseLoader:
    def __init__(self):
        pass

    def createResource(self, file, url):
        return Resource(file, url)

    def loadURL(self, url):
        url = self.normalizeURL(url)
        r = self.openResource(url)
        try:
            return self.loadResource(r)
        finally:
            r.close()

    def loadFile(self, file, url=None):
        if not url:
            url = _url_from_file(file)
        r = self.createResource(file, url)
        try:
            return self.loadResource(r)
        finally:
            r.close()

    # utilities

    def loadResource(self, resource):
        raise NotImpementedError(
            "BaseLoader.loadResource() must be overridden by a subclass")

    def openResource(self, url):
        # XXX This should be replaced to use a local cache for remote
        # resources.  The policy needs to support both re-retrieve on
        # change and provide the cached resource when the remote
        # resource is not accessible.
        url = str(url)
        try:
            file = urllib2.urlopen(url)
        except (IOError, OSError), e:
            # Python 2.1 raises a different error from Python 2.2+,
            # so we catch both to make sure we detect the situation.
            error = ZConfig.ConfigurationError("error opening resource %s: %s"
                                               % (url, str(e)))
            error.url = url
            raise error
        return self.createResource(file, url)

    def normalizeURL(self, url):
        if os.path.exists(url) or ":" not in url:
            url = "file://" + urllib.pathname2url(os.path.abspath(url))
        url, fragment = ZConfig.url.urldefrag(url)
        if fragment:
            raise ZConfig.ConfigurationError(
                "fragment identifiers are not supported")
        return url


def _url_from_file(file):
    name = getattr(file, "name", None)
    if name and name[0] != "<" and name[-1] != ">":
        return "file://" + urllib.pathname2url(os.path.abspath(name))
    else:
        return None


class SchemaLoader(BaseLoader):
    def __init__(self, registry=None):
        if registry is None:
            registry = ZConfig.datatypes.Registry()
        BaseLoader.__init__(self)
        self.registry = registry
        self._cache = {}

    def loadResource(self, resource):
        if resource.url and self._cache.has_key(resource.url):
            schema = self._cache[resource.url]
        else:
            schema = ZConfig.schema.parseResource(resource,
                                                  self.registry, self)
            self._cache[resource.url] = schema
        return schema

    # schema parser support API

    def schemaComponentSource(self, package, file):
        parts = package.split(".")
        if not parts:
            raise ZConfig.SchemaError(
                "illegal schema component name: " + `package`)
        if len(filter(None, parts)) != len(parts):
            # '' somewhere in the package spec; still illegal
            raise ZConfig.SchemaError(
                "illegal schema component name: " + `package`)
        file = file or "component.xml"
        for dir in sys.path:
            dirname = os.path.join(os.path.abspath(dir), *parts)
            fn = os.path.join(dirname, file)
            if os.path.exists(fn):
                break
        else:
            raise ZConfig.SchemaError(
                "schema component not found: " + `package`)
        return "file://" + urllib.pathname2url(fn)


class ConfigLoader(BaseLoader):
    def __init__(self, schema):
        if schema.isabstract():
            raise ZConfig.SchemaError(
                "cannot check a configuration an abstract type")
        BaseLoader.__init__(self)
        self.schema = schema

    def loadResource(self, resource):
        sm = self.createSchemaMatcher()
        self._parse_resource(sm, resource)
        result = sm.finish(), CompositeHandler(sm.handlers, self.schema)
        return result

    def createSchemaMatcher(self):
        return ZConfig.matcher.SchemaMatcher(self.schema)

    # config parser support API

    def startSection(self, parent, type, name, delegatename):
        if delegatename:
            raise NotImpementedError(
                "section delegation is not yet supported")
        t = self.schema.gettype(type)
        if t.isabstract():
            raise ZConfig.ConfigurationError(
                "concrete sections cannot match abstract section types;"
                " found abstract type " + `type`)
        return parent.createChildMatcher(t, name)

    def endSection(self, parent, type, name, delegatename, matcher):
        assert not delegatename
        sectvalue = matcher.finish()
        parent.addSection(type, name, sectvalue)

    def includeConfiguration(self, section, url, defines):
        url = self.normalizeURL(url)
        r = self.openResource(url)
        try:
            self._parse_resource(section, r, defines)
        finally:
            r.close()

    # internal helper

    def _parse_resource(self, matcher, resource, defines=None):
        parser = ZConfig.cfgparser.ZConfigParser(resource, self, defines)
        parser.parse(matcher)


class CompositeHandler:
    __metatype__ = type
    __slots__ = '_handlers', '_convert'

    def __init__(self, handlers, schema):
        self._handlers = handlers
        self._convert = schema.registry.get("basic-key")

    def __call__(self, handlermap):
        d = {}
        for name, callback in handlermap.items():
            n = self._convert(name)
            if d.has_key(n):
                raise ZConfig.ConfigurationError(
                    "handler name not unique when converted to a basic-key: "
                    + `name`)
            d[n] = callback
        L = []
        for handler, value in self._handlers:
            if not d.has_key(handler):
                L.append(handler)
        if L:
            raise ZConfig.ConfigurationError(
                "undefined handlers: " + ", ".join(L))
        for handler, value in self._handlers:
            f = d[handler]
            if f is not None:
                f(value)

    def __len__(self):
        return len(self._handlers)


class Resource:
    def __init__(self, file, url):
        self.file = file
        self.url = url

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None
            self.closed = True

    def __getattr__(self, name):
        return getattr(self.file, name)
