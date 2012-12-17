#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2012 Shuttleworth Foundation
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
from __future__ import absolute_import

import bottle
import celery.result
import sys
import types
try:
    import json
except ImportError:
    import simplejson as json


from schooltool.task.tasks import TaskReadStatus


result_app = bottle.Bottle()


class JSONEncoder(json.JSONEncoder):

    def default(self, ob):
        if type(ob) == types.GeneratorType:
            return list(ob)
        if type(ob) == Exception:
            return repr(ob)
        return json.JSONEncoder.default(self, ob)


def encode_json(obj):
    encoder = JSONEncoder(sort_keys=True, separators=(',', ':'))
    return encoder.encode(obj)


def status_dict(status):
    result = {}
    for attr in ('pending', 'in_progress', 'committing',
                 'finished', 'failed', 'succeeded'):
        result[attr] = getattr(status, attr)
    return result


def make_task_result(task_id):
    status = TaskReadStatus(task_id)
    result = {
        'internal_state': status.state,
        'status': status_dict(status),
        'info': status.info,
        'traceback': status.traceback,
        }
    return result


@result_app.route('/<task_id>')
def fetch_full(task_id=None):
    if task_id is None:
        raise bottle.HTTPError(404, "Not found: %r" % bottle.request.url)
    result = make_task_result(task_id)
    bottle.response.set_header('Content-Type', 'application/json')
    return encode_json(result)
