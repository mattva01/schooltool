from persistent import Persistent

from zope.app.container.contained import Contained

from schooltool.person.person import Person
from schooltool.person.interfaces import IPersonFactory
from schooltool.utility import UtilitySetUp

class PersonFactory(Persistent, Contained):
    def __call__(self, *args, **kw):
        return Person(*args, **kw)

personFactorySetUpSubscriber = UtilitySetUp(PersonFactory,
                                            IPersonFactory)
