##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
from time import time
from persistence.interfaces import IPersistent
from zope.interface import implements


def _p_get_changed(self):
    return self._p_state

def _p_set_changed(self, val):
    if self._p_jar is None or self._p_oid is None:
        return

    state = self._p_state
    if state is val: return

    if state:
        # changed
        if val==0:
            self._p_state = 0
    elif state==0:
        # unchanged, but not a ghost
        if val:
            self._p_state = 1
            self._p_jar.register(self)
        elif val is None:
            self._p_deactivate()
            self._p_state = None
    else:
        # Ghost. Note val can't be None, cuz then val would equal state.
        self._p_jar.setstate(self)
        self._p_state = 0

def _p_del_changed(self):
    if self._p_jar is None or self._p_oid is None:
        return

    state = self._p_state
    if state is not None:
        self._p_state = 0
        self._p_deactivate()
        self._p_state = None



class Persistent(object):
    """Mix-in class providing IPersistent support
    """

    implements(IPersistent)

    _p_changed = property(_p_get_changed, _p_set_changed, _p_del_changed,
                          "set _p_changed to 1 to indicate a change")

    _p_state = 0

    _p_oid = _p_jar = _p_serial = None

    def __getstate__(self):
        r={}
        for k, v in self.__dict__.items():
            if k[:3] not in ('_p_', '_v_'):
                r[k]=v
        return r

    def __setstate__(self, state):
        d=self.__dict__
        for k, v in d.items():
            if k[:3] != '_p_':
                del d[k]
        d.update(state)

    def _p_deactivate(self):
        if self._p_state:
            return
        if self._p_jar is None or self._p_oid is None:
            return

        d=self.__dict__
        for k, v in d.items():
            if k[:3] != '_p_':
                del d[k]
        self._p_state = None

    def _p_activate(self):
        state = self._p_state
        if state is None:
            dm = self._p_jar
            if dm is not None:
                setstate(self, dm, 0)

    def __getattribute__(self, name):
        if name[:3] != '_p_' and name != '__dict__':
            self._p_activate()
            self._p_atime = int(time() % 86400)

        return object.__getattribute__(self, name)

    def __setattr__(self, name, v):
        if name[:3] not in ('_p_', '_v_') and name != '__dict__':
            if self._p_state is None:
                dm=self._p_jar
                if dm is None or self._p_oid is None:
                    raise TypeError('Attempt to modify a unreviveable ghost')
                # revivable ghost
                setstate(self, dm, 1)
                dm.register(self)
            elif not self._p_state:
                dm=self._p_jar
                if dm is not None:
                    self._p_state = 1
                    dm.register(self)

            self._p_atime = int(time() % 86400)

        return object.__setattr__(self, name, v)


def setstate(ob, dm, state):
    # Put in modified state so we don't mark ourselves as modified
    # when our state is updated.
    ob._p_state = 1

    try:
        # Get out data manager to updates us.
        dm.setstate(ob)

        # Now set the final state.
        ob._p_state = state

    except: # We are going to reraise!
        # Something went wrong. We need to end up in the ghost state:
        del ob._p_changed
        raise
