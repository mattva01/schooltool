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
Testing registries.

$Id: app.py 4705 2005-08-15 14:49:07Z srichter $
"""
__docformat__ = 'restructuredtext'

_registries = {}

def register(reg_name, func, *args, **kw):
    reg = _registries.setdefault(reg_name, [])
    reg.append((func, args, kw))


def setup(reg_name, *args, **kw):
    for func, orig_args, orig_kw in _registries[reg_name]:
        all_kw = orig_kw.copy()
        all_kw.update(kw)
        func(*(orig_args+args), **all_kw)
