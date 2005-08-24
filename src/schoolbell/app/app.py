# Just for BBB:
from zope.deprecation import deprecated

from schooltool.person.person import PersonContainer, Person
from schooltool.person.details import PersonDetails
deprecated(('PersonContainer', 'Person', 'PersonDetails'),
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
