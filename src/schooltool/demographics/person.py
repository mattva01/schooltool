import datetime
from persistent import Persistent
from zope.interface import implements
from zope import schema
from zope.location import locate, ILocation
from schooltool.person.person import Person as PersonBase
import interfaces

class Person(PersonBase):
    """Special person that adds demographics information.
    """

    def __init__(self, username=None, title=None):
        super(Person, self).__init__(username, title)
        self.modified = datetime.datetime.utcnow()
        self.nameinfo = NameInfo()
        locate(self.nameinfo, self, 'nameinfo')
        self.demographics = Demographics()
        locate(self.demographics, self, 'demographics')
        self.schooldata = SchoolData()
        locate(self.schooldata, self, 'schooldata')
        self.parent1 = ContactInfo()
        locate(self.parent1, self, 'parent1')
        self.parent2 = ContactInfo()
        locate(self.parent2, self, 'parent2')
        self.emergency1 = ContactInfo()
        locate(self.emergency1, self, 'emergency1')
        self.emergency2 = ContactInfo()
        locate(self.emergency2, self, 'emergency2')
        self.emergency3 = ContactInfo()
        locate(self.emergency3, self, 'emergency3')

class NameInfo(Persistent):
    implements(interfaces.INameInfo, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.INameInfo, self)

class Demographics(Persistent):
    implements(interfaces.IDemographics, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.IDemographics, self)

class SchoolData(Persistent):
    implements(interfaces.ISchoolData, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.ISchoolData, self)

class ContactInfo(Persistent):
    implements(interfaces.IContactInfo, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.IContactInfo, self)
        
def initializeSchemaAttributes(iface, obj):
    for field in schema.getFields(iface).values():
        field.set(obj, field.default)

def personModifiedSubscriber(person, event):
    person.modified = datetime.datetime.utcnow()

