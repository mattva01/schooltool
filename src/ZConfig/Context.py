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
"""Top-level configuration handle."""

import ZConfig

from ZConfig import loader
from ZConfig.Config import Configuration


class Context(loader.BaseLoader):

    def __init__(self):
        loader.BaseLoader.__init__(self)
        self._named_sections = {}  # name -> Configuration
        self._needed_names = {}    # name -> [needy Configuration, ...]
        self._all_sections = []

    # subclass-support API

    def createNestedSection(self, section, type, name, delegatename):
        return Configuration(section, type, name, section.url)

    def createToplevelSection(self, url):
        return Configuration(None, None, None, url)

    def getDelegateType(self, type):
        # Applications must provide delegation typing information by
        # overriding the Context.getDelegateType() method.
        return type.lower()

    def parse(self, resource, section, defines=None):
        from ZConfig.cfgparser import ZConfigParser
        ZConfigParser(resource, self, defines).parse(section)

    def loadResource(self, resource):
        top = self.createToplevelSection(resource.url)
        self._all_sections.append(top)
        self.parse(resource, top)
        self._finish()
        return top

    # interface for parser

    def includeConfiguration(self, section, url, defines):
        r = self.openResource(url)
        try:
            self.parse(r, section, defines)
        finally:
            r.close()

    def startSection(self, section, type, name, delegatename):
        if name and self._named_sections.has_key(name):
            # Make sure sections of the same name are not defined
            # twice in the same resource, and that once a name has
            # been defined, its type is not changed by a section from
            # another resource.
            oldsect = self._named_sections[name]
            if oldsect.url == section.url:
                raise ZConfig.ConfigurationError(
                    "named section cannot be defined twice in same resource")
            if oldsect.type != type:
                raise ZConfig.ConfigurationError(
                    "named section cannot change type")
        newsect = self.createNestedSection(section, type, name, delegatename)
        self._all_sections.append(newsect)
        if delegatename:
            # The knitting together of the delegation graph needs this.
            try:
                L = self._needed_names[delegatename]
            except KeyError:
                L = []
                self._needed_names[delegatename] = L
            L.append(newsect)
        section.addChildSection(newsect)
        if name:
            self._named_sections[name] = newsect
        return newsect

    def endSection(self, parent, type, name, delegatename, section):
        section.finish()

    # internal helpers

    def _finish(self):
        # Resolve section delegations
        for name, L in self._needed_names.items():
            section = self._named_sections[name]
            for referrer in L:
                type = self.getDelegateType(referrer.type)
                if type is None:
                    raise ZConfig.ConfigurationTypeError(
                        "%s sections are not allowed to specify delegation\n"
                        "(in %s)"
                        % (repr(referrer.type), referrer.url),
                        referrer.type, None)
                type = type.lower()
                if type != section.type:
                    raise ZConfig.ConfigurationTypeError(
                        "%s sections can only inherit from %s sections\n"
                        "(in %s)"
                        % (repr(referrer.type), repr(type), referrer.url),
                        referrer.type, type)
                referrer.setDelegate(section)
        self._needed_names = None
        # Now "finish" the sections, making sure we close inner
        # sections before outer sections.  We really should order
        # these better, but for now, "finish" all sections that have
        # no delegates first, then those that have them.  This is not
        # enough to guarantee that delegates are finished before their
        # users.
        self._all_sections.reverse()
        for sect in self._all_sections:
            if sect.delegate is None:
                sect.finish()
        for sect in self._all_sections:
            if sect.delegate is not None:
                sect.finish()
        self._all_sections = None
