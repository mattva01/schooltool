Relationship
============

schoolbell.relationship is a library for managing arbitrary many-to-many binary
relationships.

Relationship types and roles are identified by URIs (the idea was borrowed
from XLink and RDF).  Instead of dealing with strings directly,
schoolbell.relationship uses introspectable URI objects that also have an
optional short name and a description in addition to the URI itself.

    >>> from schoolbell.relationship import URIObject

For example, a generic group membership relationship can be defined with the
following URIs:

    >>> URIMembership = URIObject('http://schooltool.org/ns/membership',
    ...                           'Membership', 'The membership relationship.')
    >>> URIGroup = URIObject('http://schooltool.org/ns/membership/group')
    ...                      'Group', 'A role of a containing group.')
    >>> URIMember = URIObject('http://schooltool.org/ns/membership/member',
    ...                       'Member', 'A group member role.')

TODO
