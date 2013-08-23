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
SchoolTool security policy testing helpers.
"""

import zope.schema

from schooltool.securitypolicy.metaconfigure import getDescriptionUtility


def discriminator_sort_key(disc):
    if disc[1] is None:
        return ('', 'None', disc[0])
    return (str(disc[1].__module__), str(disc[1].__name__), disc[0])


def collectActionsByDiscriminator():
    util = getDescriptionUtility()
    collected = {}
    for group in util.actions_by_group.values():
        for action in group.values():
            discriminator = (action.permission, action.interface)
            if discriminator not in collected:
                collected[discriminator] = []
            collected[discriminator].append(action)
    for actions in collected.values():
        actions[:] = sorted(actions,
                            key=lambda a: a.__name__ + a.__parent__.__name__)
    return collected


def printActionDescriptions(actions_by_discriminator):
    last_module = ''
    util = getDescriptionUtility()
    for disc in sorted(actions_by_discriminator, key=discriminator_sort_key):
        mod, ifc, perm = discriminator_sort_key(disc)
        if mod != last_module:
            last_module = mod
            print '=' * len(last_module)
            print last_module
            print '=' * len(last_module)
        perm_pair_desc = '%s, %s' % (ifc, perm)
        print '- %s\n- %s' % (perm_pair_desc, '-' * len(perm_pair_desc))
        listed = [
            str('%s / %s' % (util.groups[a.__parent__.__name__].title,
                             a.title))
            for a in actions_by_discriminator[disc]]
        for act in listed:
            print '-  %s' % act
        print '-'


def printDiscriminators(discriminators):
    last_module = ''
    for disc in sorted(discriminators, key=discriminator_sort_key):
        mod, ifc, perm = discriminator_sort_key(disc)
        if mod != last_module:
            last_module = mod
            print '-' * len(last_module)
            print last_module
            print '-' * len(last_module)
        print '%s, %s' % (ifc, perm)


def printDirectiveDescription(interface):
    for name, field in zope.schema.getFieldsInOrder(interface):
        title = '%s %s' % (name,
                           field.required and '(required)' or '(optional)')
        spacing = ' ' * (len(title) + 2)
        desc = ('\n' + spacing).join(
            [ln.strip() for ln in field.description.strip().splitlines()])
        print title + (desc and ': ' or '') + desc
