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
"""Tests of the configuration data structures and loader."""

import os
import StringIO
import tempfile
import unittest

import ZConfig

from ZConfig.Context import Context
from ZConfig.url import urljoin

from ZConfig.tests.support import CONFIG_BASE


class TestBase(unittest.TestCase):

    def load(self, relurl, context=None):
        url = urljoin(CONFIG_BASE, relurl)
        if context is None:
            context = Context()
        conf = context.loadURL(url)
        self.assertEqual(conf.url, url)
        self.assert_(conf.name is None)
        self.assert_(conf.type is None)
        self.assert_(conf.delegate is None)
        return conf

    def loadtext(self, text):
        sio = StringIO.StringIO(text)
        return Context().loadFile(sio)

    def check_simple_gets(self, conf):
        self.assertEqual(conf.get('empty'), '')
        self.assertEqual(conf.getint('int-var'), 12)
        self.assertEqual(conf.getint('neg-int'), -2)
        self.assertEqual(conf.getfloat('float-var'), 12.02)
        self.assertEqual(conf.get('var1'), 'abc')
        self.assert_(conf.getbool('true-var-1'))
        self.assert_(conf.getbool('true-var-2'))
        self.assert_(conf.getbool('true-var-3'))
        self.assert_(not conf.getbool('false-var-1'))
        self.assert_(not conf.getbool('false-var-2'))
        self.assert_(not conf.getbool('false-var-3'))
        self.assertEqual(conf.getlist('list-1'), [])
        self.assertEqual(conf.getlist('list-2'), ['abc'])
        self.assertEqual(conf.getlist('list-3'), ['abc', 'def', 'ghi'])
        self.assertEqual(conf.getlist('list-4'), ['[', 'what', 'now?', ']'])
        self.assert_(conf.getlist('list-0') is None)
        missing = Thing()
        self.assert_(conf.getlist('list-0', missing) is missing)
        self.assertEqual(conf.getlist('list-1', missing), [])
        self.assertEqual(conf.getlist('list-2', missing), ['abc'])
        self.assertEqual(conf.getlist('list-3', missing),
                         ['abc', 'def', 'ghi'])
        self.assertEqual(conf.getlist('list-4', missing),
                         ['[', 'what', 'now?', ']'])


class Thing:
    pass

class ConfigurationTestCase(TestBase):

    def test_simple_gets(self):
        conf = self.load("simple.conf")
        self.check_simple_gets(conf)

    def test_type_errors(self):
        conf = self.load("simple.conf")
        getbool = conf.getbool
        getint = conf.getint
        self.assertRaises(ValueError, getbool, 'int-var')
        self.assertRaises(ValueError, getbool, 'float-var')
        self.assertRaises(ValueError, getbool, 'neg-int')
        self.assertRaises(ValueError, getint, 'true-var-1')
        self.assertRaises(ValueError, getint, 'true-var-2')
        self.assertRaises(ValueError, getint, 'true-var-3')
        self.assertRaises(ValueError, getint, 'false-var-1')
        self.assertRaises(ValueError, getint, 'false-var-2')
        self.assertRaises(ValueError, getint, 'false-var-3')
        self.assertRaises(ValueError, getint, 'float-var')

    def test_range_errors(self):
        conf = self.load("simple.conf")
        getfloat = conf.getfloat
        getint = conf.getint
        self.assertRaises(ValueError, getint, 'int-var', min=20)
        self.assertRaises(ValueError, getint, 'int-var', max=10)
        self.assertRaises(ValueError, getint, 'neg-int', min=-1)
        self.assertRaises(ValueError, getint, 'neg-int', max=-3)
        self.assertRaises(ValueError, getfloat, 'float-var', min=12.03)
        self.assertRaises(ValueError, getfloat, 'float-var', max=12.01)

    def test_items(self):
        conf = self.load("simplesections.conf")
        self.assertEqual(sorted_items(conf),
                         [("var", "foo"), ("var-0", "foo-0"),
                          ("var-1", "foo-1"), ("var-2", "foo-2"),
                          ("var-3", "foo-3"), ("var-4", "foo-4"),
                          ("var-5", "foo-5"), ("var-6", "foo-6")])
        self.assertEqual(sorted_items(conf.getSection("section", "name")),
                         [("var", "bar"), ("var-one", "splat"),
                          ("var-two", "stuff")])

    def test_has_key(self):
        conf = self.load("simplesections.conf")
        sect = conf.getSection("section", "name")
        for key in ("var", "var-one", "var-two"):
            self.assert_(sect.has_key(key))
            self.assert_(sect.has_key(key.upper()))
        self.assert_(not sect.has_key("var-three"))

    def test_missing_named_section(self):
        conf = self.load("simplesections.conf")
        self.assertRaises(ZConfig.ConfigurationMissingSectionError,
                          conf.getSection, "section", "does-not-exist")

    def test_keys(self):
        conf = self.load("simplesections.conf")
        self.assertEqual(sorted_keys(conf),
                         ["var", "var-0", "var-1", "var-2", "var-3",
                          "var-4", "var-5", "var-6"])
        sect = conf.getSection("section", "Name")
        self.assertEqual(sorted_keys(sect),
                         ["var", "var-one", "var-two"])
        sect = conf.getSection("Section", "delegate")
        self.assertEqual(sorted_keys(sect), ["var", "var-two"])
        sect = conf.getSection("SECTION", "ANOTHER")
        self.assertEqual(sorted_keys(sect), ["var", "var-three"])
        L = [sect for sect in conf.getChildSections() if not sect.name]
        self.assertEqual(len(L), 3)
        section, trivial, minimal = L
        self.assert_(section.name is None)
        self.assertEqual(section.type, "section")
        self.assertEqual(sorted_keys(section), ["var", "var-two"])
        self.assert_(trivial.name is None)
        self.assertEqual(trivial.type, "trivial")
        self.assertEqual(sorted_keys(trivial), ["var"])
        self.assert_(minimal.name is None)
        self.assertEqual(minimal.type, "minimal")
        self.assertEqual(minimal.keys(), [])

    def test_simple_sections(self):
        conf = self.load("simplesections.conf")
        self.assertEqual(conf.get("var"), "foo")
        # check each interleaved position between sections
        for c in "0123456":
            self.assertEqual(conf.get("var-" + c), "foo-" + c)
        self.assert_(conf.get("var-7") is None)
        sect = conf.getSection("section", "name")
        for k, v in [("var", "bar"), ("var-one", "splat"),
                     ("var-two", "stuff")]:
            self.assertEqual(sect.get(k), v)
            self.assertEqual(sect.get(k.upper()), v)
        self.assert_(sect.get("not-there") is None)
        sect = conf.getSection("section", "delegate")
        for k, v in [("var", "spam"), ("var-two", "stuff")]:
            self.assertEqual(sect.get(k), v)
            self.assertEqual(sect.get(k.upper()), v)
        self.assert_(sect.get("Var-One") is None)
        L = []
        for sect in conf.getChildSections():
            if sect.type == "trivial":
                L.append(sect)
                self.assertEqual(sect.get("var"), "triv")
                break
        L2 = conf.getChildSections("TRIVIAL")
        self.assertEqual(L, L2)

    def test_no_delegation(self):
        url = urljoin(CONFIG_BASE, "simplesections.conf")
        context = NoDelegationContext()
        self.assertRaises(ZConfig.ConfigurationTypeError,
                          context.loadURL, url)

    def test_include(self):
        conf = self.load("include.conf")
        self.assertEqual(conf.get("var1"), "abc")
        self.assertEqual(conf.get("VAR1"), "abc")
        self.assertEqual(conf.get("var2"), "value2")
        self.assertEqual(conf.get("VAR2"), "value2")
        self.assertEqual(conf.get("var3"), "value3")
        self.assertEqual(conf.get("VAR3"), "value3")
        self.assertEqual(conf.get("var4"), "value")

    def test_includes_with_defines(self):
        conf = self.load("outer.conf")
        self.assertEqual(conf.get("refinner"), "inner")
        self.assertEqual(conf.get("refouter"), "outer")

    def test_define(self):
        conf = self.load("simple.conf")
        self.assertEqual(conf.get("getname"), "value")
        self.assertEqual(conf.get("getnametwice"), "valuevalue")
        self.assertEqual(conf.get("getdollars"), "$$")
        self.assertEqual(conf.get("getempty"), "xy")
        self.assertEqual(conf.get("getwords"), "abc two words def")

    def test_define_errors(self):
        self.assertRaises(ZConfig.ConfigurationSyntaxError,
                          self.loadtext, "%define\n")
        self.assertRaises(ZConfig.ConfigurationSyntaxError,
                          self.loadtext, "%define abc-def\n")
        self.assertRaises(ZConfig.ConfigurationSyntaxError,
                          self.loadtext, "%define a value\n%define a value\n")

    def test_fragment_ident_disallowed(self):
        self.assertRaises(ZConfig.ConfigurationError,
                          self.load, "simplesections.conf#another")

    def test_load_from_abspath(self):
        fn = self.write_tempfile()
        try:
            self.check_load_from_path(fn)
        finally:
            os.unlink(fn)

    def test_load_from_relpath(self):
        fn = self.write_tempfile()
        dir, name = os.path.split(fn)
        pwd = os.getcwd()
        try:
            os.chdir(dir)
            self.check_load_from_path(name)
        finally:
            os.chdir(pwd)
            os.unlink(fn)

    def test_load_from_fileobj(self):
        sio = StringIO.StringIO("name value\n"
                                "<section>\n"
                                "  name value2\n"
                                "</section>\n")
        cf = Context().loadFile(sio)
        self.assertEqual(cf.get("Name"), "value")
        self.assertEqual(cf.getSection("Section").get("Name"), "value2")

    def write_tempfile(self):
        fn = tempfile.mktemp()
        fp = open(fn, "w")
        fp.write("key value\n")
        fp.close()
        return fn

    def check_load_from_path(self, path):
        context = Context()
        context.loadURL(path)


class NoDelegationContext(Context):
    def getDelegateType(self, type):
        return None


def sorted_items(conf):
    L = conf.items()
    L.sort()
    return L

def sorted_keys(conf):
    L = conf.keys()
    L.sort()
    return L


def test_suite():
    return unittest.makeSuite(ConfigurationTestCase)

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
