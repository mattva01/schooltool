# Just for BBB:
from zope.deprecation import deprecated
from zope.location.interfaces import ILocation
from zope.interface import Interface
from zope.schema import TextLine, Text

from schooltool.common import SchoolToolMessage as _

class IPersonDetails(Interface, ILocation):
    """Contacts details stored as an annotation on a Person."""

    nickname = TextLine(
        title=_("Nickname"),
        required=False,
        description=_("A short nickname for this person."))

    primary_email = TextLine(
        title=_("Primary Email"),
        required=False)

    secondary_email = TextLine(
        title=_("Secondary Email"),
        required=False)

    primary_phone = TextLine(
        title=_("Primary phone"),
        required=False,
        description=_("Recommended telephone number."))

    secondary_phone = TextLine(
        title=_("Secondary phone"),
        required=False,
        description=_("Secondary telephone number."))

    home_page = TextLine(
        title=_("Website"),
        required=False,
        description=_("Website or weblog."))

    mailing_address = Text(
        title=_("Mailing address"),
        required=False)

deprecated(('IPersonDetails'),
           'This interface is not used anymore.'
           'The reference will be gone in 0.15')
