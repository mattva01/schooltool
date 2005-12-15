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
Person sample data generation

$Id$
"""

from zope.interface import implements

from schooltool.sampledata.interfaces import ISampleDataPlugin
from schooltool.resource.resource import Resource


class SampleResources(object):

    implements(ISampleDataPlugin)

    name = 'resources'
    dependencies = ()

    def generate(self, app, seed=None):
        for i in range(64):
            app['resources']['room%02d' % i] = Resource(title='Room %02d' % i,
                                                        isLocation=True)
        for i in range(24):
            resource = Resource(title='Projector %02d' % i)
            app['resources']['projector%02d' % i] = resource


