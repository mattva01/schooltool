#!/usr/bin/env python
"""A script for importing persons and groups into a running SchoolTool.

It expects to find two CSV files in the current directory: persons.csv
and groups.csv.

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



def import_persons(filename, stc):
    """Read a CSV file and create all persons mentioned therein on the server.

    Expects the CSV file to be in UTF-8.

    Returns a mapping from usernames to PersonRefs.
    """
    persons = {}
    data = open(filename)
    reader = csv.reader(data)
    for row in reader:
        row = [cell.decode('UTF-8') for cell in row]
        username, title = row
        person = stc.createPerson(title, username)
        persons[username] = person
    return persons


def add_members_to_groups(filename, stc, persons):
    """Read a CSV file and create groups with members.

    Expects the CSV file to be in UTF-8.
    """
    data = open(filename)
    reader = csv.reader(data)
    for row in reader:
        row = [cell.decode('UTF-8') for cell in row]
        group_id, title, description = row[:3]
        group = stc.createGroup(title, description=description,
                                name=group_id)
        for member_id in row[3:]:
            try:
                person = persons[member_id]
                group.addMember(person)
            except KeyError:
                print "Person with id '%s' was not mentioned in persons.csv" % member_id


def main():
    """Import groups and persons to a SchoolTool server."""
    stc = SchoolToolClient(server_address, server_port)
    stc.setUser(username, password)
    persons = import_persons("persons.csv", stc)
    add_members_to_groups("groups.csv", stc, persons)


if __name__ == '__main__':
    main()
