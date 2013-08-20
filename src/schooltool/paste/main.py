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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
SchoolTool application factory useable with paste.
"""
import os

from zope.app.wsgi import WSGIPublisherApplication
from zope.app.publication.httpfactory import HTTPPublicationRequestFactory

from schooltool.app.main import SchoolToolServer


class PasteSchoolToolPublisherApplication(SchoolToolServer,
                                          WSGIPublisherApplication):

    def __init__(self, config_file, factory=HTTPPublicationRequestFactory):
        options = self.load_options(['schooltool', '-c', config_file])
        db = self.setup(options)

        super(PasteSchoolToolPublisherApplication, self).__init__(db, factory)


_st_app = None
def schooltool_app_factory(global_conf, config_file):
    global _st_app
    if _st_app:
        return _st_app
    _st_app = PasteSchoolToolPublisherApplication(
        os.path.join(global_conf['here'], config_file))
    return _st_app


def task_result_app_factory(global_conf, config_file):
    from schooltool.task.result_server import ResultServerMachinery
    machinery = ResultServerMachinery()
    machinery.configure(os.path.join(global_conf['here'], config_file))

    return machinery.app
