from zope.interface import implements
from schooltool.tests.utils import LocatableEventTargetMixin
from schooltool.tests.test_relationship import Relatable
from schooltool.relationship import RelatableMixin
from schooltool.interfaces import IGroupMember, IFaceted


class BasicRelatable(Relatable, RelatableMixin):
    pass


class MemberStub(LocatableEventTargetMixin, BasicRelatable):
    implements(IGroupMember, IFaceted)

    def __init__(self, parent=None, name='does not matter'):
        LocatableEventTargetMixin.__init__(self, parent, name)
        self.__facets__ = {}
        self.added = None
        self.removed = None

    def notifyAdded(self, group, name):
        self.added = group
        if self not in group.values():
            raise AssertionError("notifyAdded called too early")

    def notifyRemoved(self, group):
        self.removed = group
        if self in group.values():
            raise AssertionError("notifyRemoved called too early")

MemberStub()
