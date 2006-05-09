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
        self.nameinfo = NameInfo()
        locate(self.nameinfo, self, 'nameinfo')
        
class NameInfo(Persistent):
    implements(interfaces.INameInfo, ILocation)

    def __init__(self):
        initializeSchemaAttributes(interfaces.INameInfo, self)

def initializeSchemaAttributes(iface, obj):
    for field in schema.getFields(iface).values():
        field.set(obj, field.default)
