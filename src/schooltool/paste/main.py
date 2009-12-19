#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2007 Shuttleworth Foundation
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
SchoolTool application factory useable with paste.

$Id$
"""
import os

from zope.app.wsgi import WSGIPublisherApplication
from zope.app.publication.httpfactory import HTTPPublicationRequestFactory

from schooltool.app.main import StandaloneServer


class PasteSchoolToolPublisherApplication(StandaloneServer,
                                          WSGIPublisherApplication):

    def __init__(self, config_file, factory=HTTPPublicationRequestFactory):
        options = self.load_options(['schooltool', '-c', config_file])
        db = self.setup(options)

        if options.config.rest:
            self.rest_enabled = True

        super(PasteSchoolToolPublisherApplication, self).__init__(db, factory)


_st_app = None
def schooltool_app_factory(global_conf, config_file):
    global _st_app
    if _st_app:
        return _st_app
    _st_app = PasteSchoolToolPublisherApplication(
        os.path.join(global_conf['here'], config_file))
    return _st_app
