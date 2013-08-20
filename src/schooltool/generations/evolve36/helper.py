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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
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
    def __init__(self, *args, **kw):
        self._options = {}
        self.update(*args, **kw)

    def __getattr__(self, name):
        if name in self._options:
            return self._options[name]
        raise AttributeError(name)

    def update(self, *args, **options):
        if len(args) == 1 and isinstance(args[0], BuildContext):
            self._options.update(args[0]._options)
        self._options.update(options)

    def __call__(self, *args, **options):
        new_context = self.__class__(**self._options)
        new_context.update(*args, **options)
        return new_context

