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
Tests for SchoolTool PDF support.
"""

import os
import sys
import unittest
import doctest

from schooltool.app.pdf import setUpFonts


def doctest_setUpFonts():
    r"""TrueType font setup tests.

        >>> from schooltool.app import pdf

    The actual setup has been done at import-time by the test_suite function.
    We only test the results here.

    Let's check that the TrueType fonts have been configured:

        >>> from reportlab.pdfbase import pdfmetrics

        >>> pdfmetrics.getFont('Times_New_Roman')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Times_New_Roman_Bold')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Times_New_Roman_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Times_New_Roman_Bold_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>

        >>> pdfmetrics.getFont('Arial_Normal')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Arial_Bold')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Arial_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>
        >>> pdfmetrics.getFont('Arial_Bold_Italic')
        <reportlab.pdfbase.ttfonts.TTFont instance at ...>

    For our Serif font (normal paragraphs), the bold/italic mappings
    are registered:

        >>> from reportlab.lib.fonts import tt2ps, ps2tt

        >>> tt2ps('Times_New_Roman', 0, 0)
        'Times_New_Roman'
        >>> tt2ps('Times_New_Roman', 1, 0)
        'Times_New_Roman_Bold'
        >>> tt2ps('Times_New_Roman', 0, 1)
        'Times_New_Roman_Italic'
        >>> tt2ps('Times_New_Roman', 1, 1)
        'Times_New_Roman_Bold_Italic'

        >>> ps2tt('Times_New_Roman')
        ('times_new_roman', 0, 0)
        >>> ps2tt('Times_New_Roman_Bold')
        ('times_new_roman', 1, 0)
        >>> ps2tt('Times_New_Roman_Italic')
        ('times_new_roman', 0, 1)
        >>> ps2tt('Times_New_Roman_Bold_Italic')
        ('times_new_roman', 1, 1)

        >>> tt2ps('Arial_Normal', 0, 0)
        'Arial_Normal'
        >>> tt2ps('Arial_Normal', 1, 0)
        'Arial_Bold'
        >>> tt2ps('Arial_Normal', 0, 1)
        'Arial_Italic'
        >>> tt2ps('Arial_Normal', 1, 1)
        'Arial_Bold_Italic'

        >>> ps2tt('Arial_Normal')
        ('arial_normal', 0, 0)
        >>> ps2tt('Arial_Bold')
        ('arial_normal', 1, 0)
        >>> ps2tt('Arial_Italic')
        ('arial_normal', 0, 1)
        >>> ps2tt('Arial_Bold_Italic')
        ('arial_normal', 1, 1)

# XXX This part fails on Windows, I don't yet know why.
#    If the fonts can not be found, setUpFonts() will
#    raise an exception:
#
#        >>> import reportlab.rl_config
#        >>> real_path = reportlab.rl_config.TTFSearchPath[-1]
#        >>> del reportlab.rl_config.TTFSearchPath[-1]
#
#        >>> pdf.setUpFonts('/definitely/nonexistent')
#        Traceback (most recent call last):
#          ...
#        TTFError: Can't open file "....ttf"
#
#    Clean up:
#
#        >>> reportlab.rl_config.TTFSearchPath.append(real_path)

    """


def tryToSetUpReportLab():
    """Try to set up reportlab.

    Returns True without doing anything if pdf.isEnabled() is True.

    Tries to guess the location of fonts.  Returns True on success,
    False if reportlab is not available or fonts could not be found.

    If something breaks during setUpFonts, the exception
    will be propagated up.
    """
    try:
        import reportlab
    except ImportError:
        return False # We don't have reportlab, so we can't get anywhere.

    from schooltool.app import pdf
    if pdf.isEnabled():
        return True # Assume that reportlab has been configured already.

    # Heuristic to try and find the TrueType fonts.
    font_dirs = ['/usr/share/fonts/truetype/ttf-liberation', # Debian
                 '/usr/share/fonts/truetype/liberation', # Fedora
                 '/usr/share/fonts/truetype/ubuntu-font-family', # Ubuntu font family
                 r'C:\WINDOWS\Fonts']
    try:
        setUpFonts(font_dirs)
        return True
    except reportlab.pdfbase.ttfonts.TTFError:
        return False


def test_suite():
    optionflags = (doctest.ELLIPSIS | doctest.REPORT_NDIFF
                   | doctest.REPORT_ONLY_FIRST_FAILURE
                   | doctest.NORMALIZE_WHITESPACE)
    suite = unittest.TestSuite()

    success = tryToSetUpReportLab()
    if success:
        suite.addTest(doctest.DocTestSuite(optionflags=optionflags))
    else:
        print >> sys.stderr, ("reportlab or TrueType fonts not found;"
                              " PDF generator tests skipped")

    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
