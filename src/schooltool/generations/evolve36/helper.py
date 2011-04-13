#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2010 Shuttleworth Foundation
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
Helpers for the evolution.
"""
from ZODB.broken import Broken


def assert_not_broken(*objects):
    for obj in objects:
        broken_list = []
        if isinstance(obj, Broken):
            broken_list.append(obj)
        try:
            attrs = sorted(set(list(obj.__dict__) +
                               list(obj.__class__.__dict__)))
        except:
            attrs = []
        finally:
            for name in attrs:
                a = getattr(obj, name)
                if isinstance(a, Broken):
                    broken_list.append((obj, name, a))
        assert not broken_list, broken_list


class BuildContext(object):
    _options = None
    def __init__(self, **kw):
        self._options = dict(kw)

    def __getattr__(self, name):
        if name in self._options:
            return self._options[name]
        return object.__getattr__(self, name)

    def expand(self, **options):
        new_options = dict(self._options)
        new_options.update(options)
        return BuildContext(**new_options)
