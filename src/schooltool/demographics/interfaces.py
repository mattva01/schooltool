from zope.interface import Interface, implements
from zope import schema
from zope.schema.interfaces import IIterableSource

from schooltool import SchoolToolMessage as _

class INameInfo(Interface):

    prefix = schema.TextLine(
        title=_(u"Prefix"),
        description=_(u"Prefix such as Mr., Mrs."),
        required=False,
        )
    
    first_name = schema.TextLine(
        title=_(u"First name"),
        required=False,
        )
        
    middle_name = schema.TextLine(
        title=_(u"Middle name"),
        required=False,
        )

    last_name = schema.TextLine(
        title=_(u"Last name"),
        required=False,
        )

    suffix = schema.TextLine(
        title=_(u"Suffix"),
        required=False,
        )

    preferred_name = schema.TextLine(
        title=_(u"Preferred name"),
        description=_(u"Name by which the student prefers to be called"),
        required=False,
        )
    
    full_name = schema.TextLine(
        title=_(u"Full name"),
        required=True,
        )

class SourceList(list):
    implements(IIterableSource)
    
class IDemographics(Interface):
    # XXX how to translate male and female? in widget?
    gender = schema.Choice(
        title=_(u"Gender"),
        source=SourceList(['male', 'female']),
        required=False,
        )

    birth_date = schema.Date(
        title=_(u"Birth date"),
        required=False,
        )

    ethnicity = schema.Choice(
        title=_(u"Ethnicity"),
        source=SourceList(['foo', 'bar']),
        required=False,
        )

    primary_language = schema.Choice(
        title=_(u"Primary language"),
        source=SourceList(['qux', 'hoi']),
        required=False,
        )

    special_education = schema.Bool(
        title=_(u"Special education"),
        required=False
        )
    
    previous_school = schema.Text(
        title=_(u"Previous school"),
        required=False
        )
