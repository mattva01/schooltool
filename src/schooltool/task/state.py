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

import celery.states
import celery.task


IN_PROGRESS = 'IN_PROGRESS'
COMMITTING = 'COMMITTING_ZODB'


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
