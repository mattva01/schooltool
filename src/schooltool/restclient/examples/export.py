#!/usr/bin/env python
"""A script that exports a list of SchoolTool users into one CSV file
and connections between groups and users into another one.

Fields in persons.csv:
  username, title

Fields in groups.csv:
  group_id, title, description, member1, member2, member3, ...

"""

# Configuration

server_address = 'localhost'
server_port = 7001
username = 'manager'
password = 'schooltool'

# End of configuration

import sys
import os


if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)


import csv    # This is one of the reasons why we need 2.3


# SchoolTool should be in the Python path.  Let us make it run
# directly in the source checkout
basedir = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                        os.path.pardir,
                                        os.path.pardir,
                                        os.path.pardir,
                                        os.path.pardir))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))


from schooltool.restclient.restclient import SchoolToolClient



def get_id(ref):
    """Get object ID from its URL."""
    url = ref.url
    return url.split("/")[-1]


def process_persons(stc):
    """Extract a sequence of person IDs and titles from the server.

    Returned strings are in UTF-8.
    """
    for person_ref in stc.getPersons():
        person_id = get_id(person_ref).encode("UTF-8")
        person_title = person_ref.title.encode("UTF-8")
        yield (person_id, person_title)


def export_persons(file_name, persons):
    """Write a list of person ID and title tuples to a CSV file."""
    f = open(file_name, "w")
    writer = csv.writer(f)
    writer.writerows(persons)


def process_groups(stc):
    """Extract a sequence of groups and their members from the server.

    Returned strings are in UTF-8.
    """
    for group_ref in stc.getGroups():
        group_id = get_id(group_ref).encode("UTF-8")

        group_info = group_ref.getInfo()
        title = group_info.title.encode("UTF-8")
        description = group_info.description.encode("UTF-8")

        member_refs = group_ref.getMembers()
        member_ids = [get_id(ref).encode("UTF-8") for ref in member_refs]

        yield [group_id, title, description] + member_ids


def export_groups(file_name, groups_and_members):
    """Write a list of groups and their members to a CSV file."""
    f = open(file_name, "w")
    writer = csv.writer(f)
    writer.writerows(groups_and_members)


def main():
    """Export groups and persons from a SchoolTool server."""
    stc = SchoolToolClient(server_address, server_port)
    stc.setUser(username, password)
    export_persons("persons.csv", process_persons(stc))
    export_groups("groups.csv", process_groups(stc))


if __name__ == '__main__':
    main()
