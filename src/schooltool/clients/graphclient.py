#!/usr/bin/env python2.3
#
# SchoolTool - common information systems platform for school administration
# Copyright (c) 2003 Shuttleworth Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
Backend for database graphing tool.
Requires the Graphviz application
http://www.research.att.com/sw/tools/graphviz/download.html
with the "dot" application in your command path.
"""

import os
from schooltool.uris import strURI
from schooltool.clients.guiclient import SchoolToolClient


class GraphGenerator(SchoolToolClient):
    """Creates a DOT file from data on a SchoolTool server"""

    def makeHeader(self):
        self.DOT = ["""digraph SchoolTool {
  nodesep=0.1;
  ranksep=1.5;
  color="black";
  bgcolor="white";
  node [fontsize=10];
  edge [fontsize=10];
  rankdir=LR;
"""]

    def complete(self, filename='graph.png'):
        self.DOT.append('}')
        cr = '\n'
        DOTstring = cr.join(self.DOT)
        results = os.popen('dot -Tpng -o %s' % filename, 'w')
        results.write(DOTstring)
        draw = results.close()
        if draw:
            raise DOT_Error

    def drawGroupTree(self):
        groups = self.getGroupTree()
        parents = ["/groups/root", "", "", "", "", "", "", "", "", "", ""]#hack
        level = 1
        for group in groups:
            if group[0] > 0:
                line = '"%s" -> "%s" [color=gray];' % (parents[group[0]-1],
                                                       group[2])
                level = group[0]
                parents[level] = group[2]
                self.DOT.append(line)

    def drawGroupInfo(self):
        groups = self.getListOfGroups()
        for group in groups:
            members = self.getGroupInfo(group[1]).members
            for member in members:
                line = '"%s" -> "%s" [color=slateblue];'\
                 % (group[1], member.person_path)
                self.DOT.append(line)

    def drawPersonInfo(self):
        persons = self.getListOfPersons()
        for person in persons:
            self.DOT.append('"%s" [color=red,shape=circle];' % person[1])
            info = self.getPersonInfo(person[1])
            if info.first_name or info.last_name:
                self.DOT.append('"%s %s"[shape=box, color=salmon];' \
                                % (info.first_name, info.last_name))
                self.DOT.append('"%s" -> "%s %s" [color=salmon];'
                                % (person[1], info.first_name, info.last_name))
            if info.date_of_birth:
                self.DOT.append('"%s"[shape=box, color=salmon];' % info.date_of_birth)
                self.DOT.append('"%s" -> "%s" [color=salmon];' % (person[1],
                                                              info.date_of_birth))
            if info.comment:
                self.DOT.append('"%s"[shape=box, color=salmon];' % info.comment)
                self.DOT.append('"%s" -> "%s" [color=salmon];' % (person[1],
                                                              info.comment))

    def drawResources(self):
        resources = self.getListOfResources()
        for resource in resources:
            self.DOT.append('"%s" [color=brown, shape=house];' % resource[1])

    def drawRelationships(self, node):
        self.DOT.append('"%s";' % node)
        relationshipPath = node + '/relationships'
        self.DOT.append('"%s" -> "%s";' % (node, relationshipPath))
        relationships = self.getObjectRelationships(node)
        for relationship in relationships:
            self.DOT.append('"%s" [shape=box,color=orange]' %
            relationship.target_title)
            self.DOT.append('"%s" -> "%s"' % (relationshipPath,
                                              relationship.link_path))
            self.DOT.append('"%s" -> "%s" [label="%s"]' %
                            (relationship.link_path,
                             relationship.target_title,
                             'xlink:title'))
            self.DOT.append('"%s" -> "%s" [label="%s"]' %
                            (relationship.link_path,
                             relationship.target_path,
                             'xlink:href'))
            self.DOT.append('"%s" -> "%s" [label="%s"]' %
                            (relationship.link_path,
                             strURI(relationship.arcrole),
                             'xlink:arcrole'))
            self.DOT.append('"%s" -> "%s" [label="%s"]' %
                            (relationship.link_path,
                             strURI(relationship.role),
                             'xlink:role'))


class DOT_Error(Exception):
    """Error in generating graph from DOT file."""
