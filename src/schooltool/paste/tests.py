#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2011 Shuttleworth Foundation
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#

from __future__ import with_statement

import shutil
import tempfile
import unittest
from os.path import join
from textwrap import dedent
from os.path import exists

from schooltool.paste.run import update_instance


class TestRun(unittest.TestCase):
    def test_update_instance(self):
        # create an old instance
        d = tempfile.mkdtemp()
        
        with open(join(d, 'schooltool.ini'), 'w') as f:
            f.write('[app:main]\n')
            f.write('config_file=schooltool.conf\n')
        with open(join(d, 'school.zcml'), 'w') as f:
            f.write('<include package="schooltool.stapp2007" />\n')
        with open(join(d, 'schooltool.conf'), 'w') as f:
            f.write(dedent("""
                site-definition %(instance)s/school.zcml
                pid-file var/schooltool.pid
                attendance-log-file log/attendance.log
                #   Specifies the path to TrueType fonts (Arial and Times New Roman)
                #   for ReportLab.
                # Examples:
                #    reportlab_fontdir /usr/share/fonts/truetype/msttcorefonts
                #reportlab_fontdir /usr/share/fonts/truetype/msttcorefonts
                """) % dict(instance = d))

        # update
        update_instance(d)

        # check
        assert exists(join(d, 'paste.ini'))
        assert exists(join(d, 'site.zcml'))
        assert exists(join(d, 'schooltool.conf'))

        with open(join(d, 'schooltool.conf'), 'r') as f:
            schooltool_conf = f.read()

            assert 'school.zcml' not in schooltool_conf
            assert join(d, 'site.zcml') in schooltool_conf
            assert 'msttcorefonts' not in schooltool_conf
            assert '\nreportlab_fontdir /usr/share/fonts/truetype/ttf-liberation' in schooltool_conf
            assert '\nattendance-log-file' not in schooltool_conf
            assert '\n#attendance-log-file log/attendance.log\n' in schooltool_conf
            assert '\npid-file %(instance)s/var/schooltool.pid\n' % dict(
                instance = d) in schooltool_conf

        # cleanup
        shutil.rmtree(d)

