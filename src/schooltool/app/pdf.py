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
Schooltool PDF support.
"""
from reportlab.pdfbase import pdfmetrics

enabled = False

def isEnabled():
    return enabled


# ------------------
# Font configuration
# ------------------

def registerTTFont(fontname, filename):
    """Register a TrueType font with ReportLab.

    Clears up the incorrect straight-through mappings that ReportLab 1.19
    unhelpfully gives us.
    """
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab.lib.fonts

    pdfmetrics.registerFont(TTFont(fontname, filename))
    # For some reason pdfmetrics.registerFont for TrueType fonts explicitly
    # calls addMapping with incorrect straight-through mappings, at least in
    # reportlab version 1.19.  We thus need to stick our dirty fingers in
    # reportlab's internal data structures and undo those changes so that we
    # can call addMapping with correct values.
    key = fontname.lower()
    del reportlab.lib.fonts._tt2ps_map[key, 0, 0]
    del reportlab.lib.fonts._tt2ps_map[key, 0, 1]
    del reportlab.lib.fonts._tt2ps_map[key, 1, 0]
    del reportlab.lib.fonts._tt2ps_map[key, 1, 1]
    del reportlab.lib.fonts._ps2tt_map[key]


# 'Arial' is predefined in ReportLab, so we use 'Arial_Normal'

font_map = {
    'Arial_Normal': 'LiberationSans-Regular.ttf',
    'Arial_Bold': 'LiberationSans-Bold.ttf',
    'Arial_Italic': 'LiberationSans-Italic.ttf',
    'Arial_Bold_Italic': 'LiberationSans-BoldItalic.ttf',
    'Times_New_Roman': 'LiberationSerif-Regular.ttf',
    'Times_New_Roman_Bold': 'LiberationSerif-Bold.ttf',
    'Times_New_Roman_Italic': 'LiberationSerif-Italic.ttf',
    'Times_New_Roman_Bold_Italic': 'LiberationSerif-BoldItalic.ttf',
    'Ubuntu_Regular': 'Ubuntu-R.ttf',
    'Ubuntu_Bold': 'Ubuntu-B.ttf',
    'Ubuntu_Italic': 'Ubuntu-RI.ttf',
    'Ubuntu_Bold_Italic': 'Ubuntu-BI.ttf',
    }

font_directories = ()


def setUpFonts(directories=()):
    """Set up ReportGen to use Liberation and Ubuntu Fonts."""
    import reportlab.rl_config
    from reportlab.lib.fonts import addMapping

    global font_directories
    if not directories:
        directories = font_directories
    else:
        font_directories = directories

    ttfpath = reportlab.rl_config.TTFSearchPath
    for fontdir in directories:
        if fontdir not in ttfpath:
            ttfpath.append(fontdir)

    reportlab.rl_config.warnOnMissingFontGlyphs = 0

    for font_name, font_file in font_map.items():
        registerTTFont(font_name, font_file)

    addMapping('Arial_Normal', 0, 0, 'Arial_Normal')
    addMapping('Arial_Normal', 0, 1, 'Arial_Italic')
    addMapping('Arial_Normal', 1, 0, 'Arial_Bold')
    addMapping('Arial_Normal', 1, 1, 'Arial_Bold_Italic')

    addMapping('Times_New_Roman', 0, 0, 'Times_New_Roman')
    addMapping('Times_New_Roman', 0, 1, 'Times_New_Roman_Italic')
    addMapping('Times_New_Roman', 1, 0, 'Times_New_Roman_Bold')
    addMapping('Times_New_Roman', 1, 1, 'Times_New_Roman_Bold_Italic')

    # XXX: Rename to Ubuntu
    addMapping('Ubuntu_Regular', 0, 0, 'Ubuntu_Regular')
    addMapping('Ubuntu_Regular', 0, 1, 'Ubuntu_Italic')
    addMapping('Ubuntu_Regular', 1, 0, 'Ubuntu_Bold')
    addMapping('Ubuntu_Regular', 1, 1, 'Ubuntu_Bold_Italic')

    global enabled
    enabled = True


# z3c.rml >= 1.1.0 calls _reset when processing each document
# We need to register our fonts again
from reportlab.rl_config import register_reset
register_reset(setUpFonts)
del register_reset
