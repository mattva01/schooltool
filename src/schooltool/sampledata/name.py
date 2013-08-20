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
SchoolTool person name generator
"""
import os.path
from schooltool.sampledata import PortableRandom


class NameGenerator(object):
    """Person name generator

    Generates random full names.  Names can recur.
    """

    def __init__(self, seed):
        self.random = PortableRandom(seed)
        self.first_names = self._readLines('first_names.txt')
        self.last_names = self._readLines('last_names.txt')

    def _readLines(self, filename):
        """Read in lines from file

        Filename is relative to the module.
        Returned lines are stripped.
        """
        fullpath = os.path.join(os.path.dirname(__file__), filename)
        lines = file(fullpath).readlines()
        return [line.strip() for line in lines]

    def generate(self):
        """Generates name information, returns tuple of
        first name, last name, full name
        """
        first_name = self.random.choice(self.first_names)
        last_name = self.random.choice(self.last_names)
        full_name = "%s %s" % (first_name, last_name)
        return first_name, last_name, full_name

