#Boa:Frame:wxFrame1
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
wxWidgets interface for database graphing tool.
"""

import random

from wxPython.wx import *
from wxPython.html import *

from schooltool.clients.graphclient import GraphGenerator


def create(parent):
    return wxFrame1(parent)

[wxID_WXFRAME1, wxID_WXFRAME1BUTTON1, wxID_WXFRAME1GROUPINFO,
 wxID_WXFRAME1GROUPRELATIONSHIPS, wxID_WXFRAME1GROUPTREE,
 wxID_WXFRAME1HTMLWINDOW1, wxID_WXFRAME1PANEL1, wxID_WXFRAME1PERSONINFO,
 wxID_WXFRAME1PERSONRELATIONSHIPS, wxID_WXFRAME1PORT, wxID_WXFRAME1RESOURCES,
 wxID_WXFRAME1SERVER, wxID_WXFRAME1SPLITTERWINDOW1, wxID_WXFRAME1STATICBOX1,
 wxID_WXFRAME1STATICTEXT1, wxID_WXFRAME1STATICTEXT2,
] = map(lambda _init_ctrls: wxNewId(), range(16))


class wxFrame1(wxFrame):

    def _init_utils(self):
        # generated method, don't edit
        pass

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wxFrame.__init__(self, id=wxID_WXFRAME1, name='', parent=prnt,
              pos=wxPoint(166, 83), size=wxSize(840, 646),
              style=wxDEFAULT_FRAME_STYLE, title='SchoolTool Data Grapher')
        self._init_utils()
        self.SetClientSize(wxSize(832, 619))

        self.splitterWindow1 = wxSplitterWindow(id=wxID_WXFRAME1SPLITTERWINDOW1,
              name='splitterWindow1', parent=self, point=wxPoint(0, 0),
              size=wxSize(832, 619), style=wxSP_3D)

        self.htmlWindow1 = wxHtmlWindow(id=wxID_WXFRAME1HTMLWINDOW1,
              name='htmlWindow1', parent=self.splitterWindow1, pos=wxPoint(227,
              2), size=wxSize(603, 615))

        self.panel1 = wxPanel(id=wxID_WXFRAME1PANEL1, name='panel1',
              parent=self.splitterWindow1, pos=wxPoint(2, 2), size=wxSize(218,
              615), style=wxTAB_TRAVERSAL)
        self.splitterWindow1.SplitVertically(self.panel1, self.htmlWindow1, 220)

        self.groupTree = wxCheckBox(id=wxID_WXFRAME1GROUPTREE,
              label='Show Group Tree', name='groupTree', parent=self.panel1,
              pos=wxPoint(40, 120), size=wxSize(120, 13), style=0)
        self.groupTree.SetValue(False)

        self.staticText2 = wxStaticText(id=wxID_WXFRAME1STATICTEXT2,
              label='Port', name='staticText2', parent=self.panel1,
              pos=wxPoint(8, 52), size=wxSize(19, 13), style=0)

        self.staticText1 = wxStaticText(id=wxID_WXFRAME1STATICTEXT1,
              label='Server', name='staticText1', parent=self.panel1,
              pos=wxPoint(8, 24), size=wxSize(31, 13), style=0)

        self.button1 = wxButton(id=wxID_WXFRAME1BUTTON1, label='Create Graph',
              name='button1', parent=self.panel1, pos=wxPoint(120, 360),
              size=wxSize(75, 23), style=0)
        EVT_BUTTON(self.button1, wxID_WXFRAME1BUTTON1, self.OnCreateButton)

        self.staticBox1 = wxStaticBox(id=wxID_WXFRAME1STATICBOX1,
              label='Overviews', name='staticBox1', parent=self.panel1,
              pos=wxPoint(24, 88), size=wxSize(176, 248), style=0)

        self.server = wxTextCtrl(id=wxID_WXFRAME1SERVER, name='server',
              parent=self.panel1, pos=wxPoint(48, 20), size=wxSize(136, 21),
              style=0, value='schooltool.feinsteinhs.org')

        self.port = wxTextCtrl(id=wxID_WXFRAME1PORT, name='port',
              parent=self.panel1, pos=wxPoint(48, 48), size=wxSize(136, 21),
              style=0, value='80')

        self.groupInfo = wxCheckBox(id=wxID_WXFRAME1GROUPINFO,
              label='Show Group Info', name='groupInfo', parent=self.panel1,
              pos=wxPoint(40, 144), size=wxSize(120, 13), style=0)
        self.groupInfo.SetValue(False)

        self.personInfo = wxCheckBox(id=wxID_WXFRAME1PERSONINFO,
              label='Show Person Info', name='personInfo', parent=self.panel1,
              pos=wxPoint(40, 168), size=wxSize(120, 13), style=0)
        self.personInfo.SetValue(False)

        self.resources = wxCheckBox(id=wxID_WXFRAME1RESOURCES,
              label='Show Resources', name='resources', parent=self.panel1,
              pos=wxPoint(40, 192), size=wxSize(120, 13), style=0)
        self.resources.SetValue(False)

        self.personRelationships = wxCheckBox(id=wxID_WXFRAME1PERSONRELATIONSHIPS,
              label="A Person's Relationships", name='personRelationships',
              parent=self.panel1, pos=wxPoint(40, 216), size=wxSize(152, 13),
              style=0)
        self.personRelationships.SetValue(False)

        self.groupRelationships = wxCheckBox(id=wxID_WXFRAME1GROUPRELATIONSHIPS,
              label="A Group's Relationships", name='groupRelationships',
              parent=self.panel1, pos=wxPoint(40, 240), size=wxSize(144, 13),
              style=0)
        self.groupRelationships.SetValue(False)

    def __init__(self, parent):
        self._init_ctrls(parent)

    def OnCreateButton(self, event):
        wxBeginBusyCursor()
        self.graph = GraphGenerator()
        self.graph.setServer(self.server.GetValue(), int(self.port.GetValue()))
        self.graph.makeHeader()
        if self.groupTree.GetValue():
            self.graph.drawGroupTree()
        if self.groupInfo.GetValue():
            self.graph.drawGroupInfo()
        if self.personInfo.GetValue():
            self.graph.drawPersonInfo()
        if self.resources.GetValue():
            self.graph.drawResources()
        if self.personRelationships.GetValue():
            persons = self.graph.getListOfPersons()
            person = random.choice(persons)[1]
        if self.personRelationships.GetValue():
            self.graph.drawRelationships(person)
        if self.groupRelationships.GetValue():
            groups = self.graph.getListOfGroups()
            group = random.choice(groups)[1]
        if self.groupRelationships.GetValue():
            self.graph.drawRelationships(group)
        self.graph.complete()
        self.htmlWindow1.SetPage('<img src="graph.png" />')
        wxEndBusyCursor()

