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
import datetime

from zope.interface import implements

from schooltool.task.interfaces import IProgressMessage
from schooltool.task.state import TaskWriteState
from schooltool.task.tasks import Message


def normalized_progress(*args):
    pmin = 0.0
    pmax = 1.0
    args = list(args)
    while args:
        max = args.pop()
        val = args.pop()
        pmin = pmin + pmax * val
        pmax = pmax * max
    return min(float(pmin) / float(pmax), 1.0)


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
        self.last_updated = self.now

    def force(self, *args, **kw):
        self.tick(*args, **kw)
        self.tock(*args, **kw)
        self.last_updated = self.now

    def __call__(self, *args, **kw):
        self.tick(*args, **kw)
        if (self.last_updated is None or
            self.delta >= self.update_interval):
            self.tock(*args, **kw)


unchanged = object()


class ProgressLine(dict):

    def __init__(self, **kw):
        dict.__init__(self)
        defaults = self.defaults()
        defaults.update(kw)
        self.update(defaults)

    def defaults(self):
        defaults = {
            'title': u'',
            'errors': [],
            'progress': None,
            'active': True,
            }
        return defaults

    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __repr__(self):
        return '<%s (%s)>' % (self.__class__.__name__, dict.__repr__(self))

    def finish(self):
        if self.get('progress') is not None:
            self['progress'] = 1.0
            self['active'] = False


class TaskProgress(Timer):

    lines = None
    order = None

    title = u''

    def __init__(self, task_id):
        if task_id is None:
            self.task_state = None
        else:
            self.task_state = TaskWriteState(task_id)
        Timer.__init__(self)

    def reset(self):
        self.lines = {}
        self.order = {}
        Timer.reset(self)

    def get(self, line_id, **kw):
        return self.lines.get(line_id, **kw)

    def __getitem__(self, line_id):
        return self.lines[line_id]

    def add(self, line_id, **kw):
        if line_id not in self.lines:
            self.lines[line_id] = ProgressLine(**kw)
            self.order[line_id] = max(self.order.values())+1 if self.order else 1
        return self.get(line_id)

    def remove(self, line_id):
        del self.lines[line_id]
        del self.order[line_id]

    def finish(self, line_id, force=True):
        self.lines[line_id].finish()
        if force:
            self.force()

    def error(self, line_id, error):
        self.lines[line_id].errors.append(error)

    def tick(self, *args, **kw):
        if args or kw:
            self.add(*args, **kw)
            assert len(args) == 1
            line_id = args[0]
            self.lines[line_id].update(kw)

    def tock(self, *args, **kw):
        lines = dict([(n, self.lines[lid]) for lid, n in self.order.items()])
        progress = {
            'lines': lines,
            'title': self.title
            }
        if self.task_state is not None:
            self.task_state.set_progress(progress)
        Timer.tock(self)


class ProgressMessage(Message):
    implements(IProgressMessage)
