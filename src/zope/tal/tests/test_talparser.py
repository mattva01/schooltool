##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Tests for zope.tal.talparser.

$Id$
"""
import unittest

from zope.tal import talparser


class TALParserTestCase(unittest.TestCase):

    def test_parser_returns_macros(self):
        parser = talparser.TALParser()
        parser.parseString(
            "<?xml version='1.0'?>\n"
            "<doc xmlns:metal='http://xml.zope.org/namespaces/metal'>\n"
            "  <m metal:define-macro='MACRO'>\n"
            "    <para>some text</para>\n"
            "  </m>\n"
            "</doc>")
        bytecode, macros = parser.getCode()
        self.assertEqual(macros.keys(), ["MACRO"])


def test_suite():
    return unittest.makeSuite(TALParserTestCase)
