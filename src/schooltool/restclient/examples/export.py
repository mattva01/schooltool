#!/usr/bin/env python
"""Script that exports a list of all users into one csv file and
connection between groups and users into another one.

Formats are like this:
persons.csv
username, title

groups.csv
group_id, title, description, member1, member2, member3

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


def get_id(ref):
    """Get object id out of it's ref."""
    url = ref.url
    return url.split("/")[-1]


def process_persons():
    for person_ref in stc.getPersons():
        person_id = get_id(person_ref)
        person_title = person_ref.title.encode("UTF-8")
        yield (person_id, person_title)


def export_persons(file_name):
    file = open(file_name, "w")
    writer = csv.writer(file)
    writer.writerows(process_persons())


def process_groups():
    for group_ref in stc.getGroups():
        group_id = get_id(group_ref)

        group_info = group_ref.getInfo()
        title = group_info.title.encode("UTF-8")
        description = group_info.description.encode("UTF-8")

        member_refs = group_ref.getMembers()
        member_ids = [get_id(ref) for ref in member_refs]

        yield tuple([group_id, title, description] + member_ids)


def export_groups(file_name):
    file = open(file_name, "w")
    writer = csv.writer(file)
    writer.writerows(process_groups())


export_persons("persons.csv")
export_groups("groups.csv")
