import zope.interface
import zope.schema

from schooltool import SchoolToolMessage as _

class INameInfo(zope.interface.Interface):

    prefix = zope.schema.TextLine(
        title=_(u"Prefix"),
        description=_(u"Prefix such as Mr., Mrs."),
        required=False,
        )
    
    first_name = zope.schema.TextLine(
        title=_(u"First name"),
        required=False,
        )
        
    middle_name = zope.schema.TextLine(
        title=_(u"Middle name"),
        required=False,
        )

    last_name = zope.schema.TextLine(
        title=_(u"Last name"),
        required=False,
        )

    suffix = zope.schema.TextLine(
        title=_(u"Suffix"),
        required=False,
        )

    preferred_name = zope.schema.TextLine(
        title=_(u"Preferred name"),
        description=_(u"Name by which the student prefers to be called"),
        required=False,
        )
    
    full_name = zope.schema.TextLine(
        title=_(u"Full name"),
        required=True,
        )
