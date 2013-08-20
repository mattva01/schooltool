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
import datetime

import celery.task

from schooltool.common import SchoolToolMessage as _


IN_PROGRESS = 'IN_PROGRESS'
COMMITTING = 'COMMITTING_ZODB'


def normalized_progress(*args):
    pmin = 0.0
    pmax = 1.0
    while args:
        val, max = args.pop()
        pmin = pmin + pmax * val
        pmax = pmax * max
    return min(float(pmin) / float(pmax), 1.0)


class TaskReadState(object):

    task_id = None
    _meta = None
    _progress_states = (celery.states.STARTED, IN_PROGRESS)

    def __init__(self, task_id):
        self.task_id = task_id
        self._meta = None, None, None
        self.reload()

    def reload(self):
        result = celery.task.Task.AsyncResult(self.task_id)
        self._meta = result.state, result.result, result.traceback

    @property
    def state(self):
        return self._meta[0]

    @property
    def in_progress(self):
        return (self.state in self._progress_states or self.committing)

    @property
    def committing(self):
        return self.state == COMMITTING

    @property
    def pending(self):
        return self.state in celery.states.UNREADY_STATES

    @property
    def finished(self):
        return self.state in celery.states.READY_STATES

    @property
    def failed(self):
        return self.state in celery.states.PROPAGATE_STATES

    @property
    def succeeded(self):
        return self.state == celery.states.SUCCESS

    @property
    def progress(self):
        if self.in_progress:
            return self._meta[1]

    @property
    def result(self):
        if self.succeeded:
            return self._meta[1]

    @property
    def failure(self):
        if self.failed:
            return self._meta[1]

    @property
    def info(self):
        return self._meta[1]

    @property
    def traceback(self):
        return self._meta[2]


class NotInProgress(Exception):
    pass


class TaskWriteState(TaskReadState):

    def set_progress(self, progress=None):
        result = celery.task.Task.AsyncResult(self.task_id)
        # XXX: only check this if task.track_started
        if result.state not in self._progress_states:
            raise NotInProgress(result.state, self._progress_states)
        result.backend.store_result(result.task_id, progress, IN_PROGRESS)
        self.reload()

    def set_committing(self):
        result = celery.task.Task.AsyncResult(self.task_id)
        # XXX: only check this if task.track_started
        if result.state not in self._progress_states:
            raise NotInProgress(result.state, self._progress_states)
        result.backend.store_result(result.task_id, self.info, COMMITTING)
        self.reload()


class Timer(object):

    update_interval = datetime.timedelta(seconds=1)
    last_updated = None

    def __init__(self):
        self.reset()

    def reset(self):
        self.last_updated = None

    @property
    def now(self):
        return datetime.datetime.utcnow()

    @property
    def delta(self):
        last_updated = self.last_updated
        if last_updated is None:
            return None
        return self.now - last_updated

    def tick(self, *args, **kw):
        raise NotImplemented()

    def tock(self, *args, **kw):
        raise NotImplemented()

    def force(self, *args, **kw):
        self.tick(*args, **kw)
        self.tock(*args, **kw)
        self.last_updated = self.now

    def __call__(self, *args, **kw):
        self.tick(*args, **kw)
        if (self.last_updated is None or
            self.delta >= self.update_interval):
            self.tock(*args, **kw)
            self.last_updated = self.now


class Progress(Timer):

    title = u''
    value = 0.0
    max_value = 1.0

    def __init__(self, default_title=u'', max=None):
        self.default_title = default_title
        self.max_value = max or 1.0

    def reset(self):
        self.title = self.default_title
        self.value = 0.0

    def tick(self, title=None, progress=None):
        if title is not None:
            self.title = title
        if progress is not None:
            self.progress = progress

    def tock(self, *args, **kw):
        pass


class TaskProgress(Timer):

    parts = None
    order = None
    value = None
    task_status = None

    def __init__(self, task_id):
        self.parts = {}
        self.order = []
        self.task_status = TaskWriteState(task_id)
        Timer.__init__(self)

    def reset(self):
        Timer.reset(self)
        self.value = {}
        for n, importer in enumerate(self.parts):
            self.value[n] = {
                'title': importer.title,
                'errors': [],
                'progress': 0.0,
                }
        #self.value['overall'] = {
        #        'title': _('Overall'),
        #        'errors': [],
        #        'progress': 0.0,
        #        }
        self.tock()

    def finish(self):
        for status in self.value.values():
            status['progress'] = 1.0
        self.task_status.set_progress(self.value)
        self.last_updated = self.now

    def tick(self, part_name, title=None, progress=None):
        if part_name not in self.parts:
            self.parts[part_name] = Progress(default_title=title)
        
            
        self.value[importer_n]['progress'] = value
        self.value['overall']['progress'] = normalized_progress(
            importer_n, len(self.importers), value, 1.0)

    def tock(self, *args, **kw):
        self.task_status.set_progress(self.value)


