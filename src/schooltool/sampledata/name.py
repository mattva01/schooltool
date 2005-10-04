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
SchoolTool person name generator

$Id$
"""
import os.path
import random


class NameGenerator(object):
    """Person name generator

    Generates random full names and makes sure they don't repeat.
    """

    def __init__(self, seed):
        self.random = random.Random()
        self.random.seed(seed)
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
        return "%s %s" % (self.random.choice(self.first_names),
                          self.random.choice(self.last_names))
