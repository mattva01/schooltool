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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import absolute_import

import bottle
import types
try:
    import json
except ImportError:
    import simplejson as json

import zope.i18nmessageid.message
import zope.configuration.config
import zope.configuration.xmlconfig
from zope.i18n import translate
from zope.interface import directlyProvides
from zope.publisher.http import IHTTPRequest

from schooltool.app.main import SchoolToolMachinery, setLanguage
from schooltool.task.state import TaskReadState


not_translatable = object()


def iter_translate(o, markers=None):
    for item in o:
        text = inplace_translate(item, markers=markers)
        yield item if text is not_translatable else text


def inplace_translate(o, markers=None):
    oid = id(o)
    if markers is not None:
        if oid in markers:
            return markers[oid]
        else:
            markers[oid] = not_translatable
    else:
        markers = {oid: not_translatable}

    if isinstance(o, zope.i18nmessageid.message.Message):
        try:
            markers[oid] = translate(o, context=bottle.request)
        except TypeError:
            markers[oid] = o
    elif isinstance(o, (list, tuple)):
        if markers is None:
            markers = {}
        markers[oid] = o.__class__(iter_translate(o, markers=markers))
    elif isinstance(o, dict):
        for k in o:
            t = inplace_translate(o[k])
            if t is not_translatable:
                continue
            o[k] = t
        markers[oid] = o
    return markers[oid]


result_app = bottle.Bottle()


class JSONEncoder(json.JSONEncoder):

    def default(self, ob):
        if type(ob) == types.GeneratorType:
            return list(ob)
        if isinstance(ob, Exception):
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
    status = TaskReadState(task_id)
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
    directlyProvides(bottle.request, IHTTPRequest)
    translated_result = inplace_translate(result)
    encoded_result = encode_json(translated_result)
    bottle.response.set_header('Content-Type', 'application/json')
    return encoded_result


class ResultServerMachinery(SchoolToolMachinery):

    def configureComponents(self):
        context = zope.configuration.config.ConfigurationMachine()
        if self.config.devmode:
            context.provideFeature('devmode')
        zope.configuration.xmlconfig.registerCommonDirectives(context)
        context = zope.configuration.xmlconfig.file(
            self.config.result_server_definition, context=context)

    def configure(self, config_file):
        self.config, self.handler = self.readConfig(config_file)
        self.configureComponents()
        setLanguage(self.config.lang)

    @property
    def app(self):
        global result_app
        return result_app
