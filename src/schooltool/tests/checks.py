#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
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
Checks for the unit tests.
"""

import sys

__metaclass__ = type


def warn(msg):
    print >> sys.stderr, msg


class ComponentChecks:

    def startTest(self, test):
        from schooltool import component
        self.facet_factory_registry = dict(component.facet_factory_registry)
        self.uri_registry = dict(component._uri_registry)
        self.relationship_registry = dict(component.relationship_registry._reg)
        self.view_registry = dict(component.view_registry._reg)
        self.class_view_registry = dict(component.class_view_registry)

    def stopTest(self, test):
        from schooltool import component
        if self.facet_factory_registry != component.facet_factory_registry:
            warn("%s changed facet factory registry" % test)
        if self.uri_registry != component._uri_registry:
            warn("%s changed URI registry" % test)
        if self.relationship_registry != component.relationship_registry._reg:
            warn("%s changed relationship registry" % test)
        if self.view_registry != component.view_registry._reg:
            warn("%s changed view registry" % test)
        if self.class_view_registry != component.class_view_registry:
            warn("%s changed class view registry" % test)


class TransactionChecks:

    def startTest(self, test):
        import zodb.ztransaction # calls transaction.set_factory
        from transaction import get_transaction
        txn = get_transaction()
        self.had_resources = bool(txn._resources)

    def stopTest(self, test):
        if self.had_resources:
            return
        from transaction import get_transaction
        txn = get_transaction()
        if txn._resources:
            warn("%s left an unclean transaction" % test)


class StdoutWrapper:

    def __init__(self, stm):
        self._stm = stm
        self.written = False

    def __getattr__(self, attr):
        return getattr(self._stm, attr)

    def write(self, *args):
        self.written = True
        self._stm.write(*args)


class StdoutChecks:

    def __init__(self):
        self.stdout_wrapper = StdoutWrapper(sys.stdout)
        self.stderr_wrapper = StdoutWrapper(sys.stderr)

    def startTest(self, test):
        import sys
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        sys.stdout = self.stdout_wrapper
        sys.stderr = self.stderr_wrapper
        self.stdout_wrapper.written = False
        self.stderr_wrapper.written = False

    def stopTest(self, test):
        import sys
        warn_stdout_replaced = sys.stdout is not self.stdout_wrapper
        warn_stderr_replaced = sys.stderr is not self.stderr_wrapper
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        if warn_stdout_replaced:
            warn("%s replaced sys.stdout" % test)
        if warn_stderr_replaced:
            warn("%s replaced sys.stderr" % test)
        if self.stdout_wrapper.written:
            warn("%s wrote to sys.stdout" % test)
        if self.stderr_wrapper.written:
            warn("%s wrote to sys.stderr" % test)


def test_hooks():
    return [StdoutChecks(),     # should be the first one
            ComponentChecks(),
            TransactionChecks()]
