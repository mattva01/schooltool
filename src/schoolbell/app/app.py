# Just for BBB:
from persistent import Persistent
from zope.interface import implements
from zope.deprecation import deprecated

from schooltool.person.person import PersonContainer, Person
from schoolbell.app.interfaces import IPersonDetails

class PersonDetails(Persistent):
    """BBB an old class that is not used anymore but might appear in old
    Data.fs files."""
    implements(IPersonDetails)

    __name__ = 'details'

    def __init__(self, nickname=None, primary_email=None,
                 secondary_email=None, primary_phone=None,
                 secondary_phone=None, mailing_address=None, home_page=None):
        self.nickname = nickname
        self.primary_email = primary_email
        self.secondary_email = secondary_email
        self.primary_phone = primary_phone
        self.secondary_phone = secondary_phone
        self.mailing_address = mailing_address
        self.home_page = home_page


deprecated(('PersonDetails'),
           'This class is not used anymore. '
           'The reference will be gone in 0.15')

deprecated(('PersonContainer', 'Person'),
           'This class has moved to schooltool.person.person. '
           'The reference will be gone in 0.15')

from schooltool.group.group import GroupContainer, Group
deprecated(('GroupContainer', 'Group'),
           'This class has moved to schooltool.group.group. '
           'The reference will be gone in 0.15')

from schooltool.resource.resource import ResourceContainer, Resource
deprecated(('ResourceContainer', 'Resource'),
           'This class has moved to schooltool.resource.resource. '
           'The reference will be gone in 0.15')

from schooltool.app.app import SchoolToolApplication as SchoolBellApplication
from schooltool.app.app import ApplicationPreferences
deprecated(('SchoolBellApplication', 'ApplicationPreferences'),
           'This class has moved to schooltool.app.app. '
           'The reference will be gone in 0.15')
