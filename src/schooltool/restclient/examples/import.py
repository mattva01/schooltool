#!/usr/bin/env python
"""Script for importing persons and groups into a running SchoolTool.
"""

import sys
import os
import csv

if sys.version_info < (2, 3):
    print >> sys.stderr, '%s: need Python 2.3 or later.' % sys.argv[0]
    print >> sys.stderr, 'Your python is %s' % sys.version
    sys.exit(1)

basedir = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                        os.path.pardir,
                                        os.path.pardir,
                                        os.path.pardir,
                                        os.path.pardir))
sys.path.insert(0, os.path.join(basedir, 'src'))
sys.path.insert(0, os.path.join(basedir, 'Zope3', 'src'))

from schooltool.restclient.restclient import SchoolToolClient

stc = SchoolToolClient()
stc.setUser('manager', 'schooltool')

persons = {}

def import_persons(file):
    data = open(file)
    reader = csv.reader(data)
    for row in reader:
        row = [cell.decode('UTF-8') for cell in row]
        username, title = row
        person = stc.createPerson(title, username)
        persons[username] = person


def add_members_to_groups(file):
    data = open(file)
    reader = csv.reader(data)
    for row in reader:
        row = [cell.decode('UTF-8') for cell in row]
        group_id, title, description = row[:3]
        group = stc.createGroup(title, description=description,
                                name=group_id)
        for member_id in row[3:]:
            person = persons.get(member_id, None)
            if person:
                group.addMember(person)
            else:
                print "Person with id '%s' not found!" % member_id

import_persons("persons.csv")
add_members_to_groups("groups.csv")
