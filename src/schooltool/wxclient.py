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
#
"""
SchoolTool GUI client.

SchoolTool is a common information systems platform for school administration
Visit http://www.schooltool.org/

Copyright (c) 2003 Shuttleworth Foundation

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

from wxPython.wx import *
from wxPython.html import wxHtmlWindow
import httplib
import socket
from htmllib import HTMLParser
from formatter import AbstractFormatter, NullWriter

__metaclass__ = type


class SchoolToolClient:

    connectionFactory = httplib.HTTPConnection

    server = 'localhost'
    port = 8080
    status = ''

    def setServer(self, server, port):
        self.server = server
        self.port = port
        self.tryToConnect()

    def tryToConnect(self):
        self.get('/')

    def get(self, path):
        conn = self.connectionFactory(self.server, self.port)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            body = response.read()
            conn.close()
            self.status = "%d %s" % (response.status, response.reason)
            self.version = response.getheader('Server')
            return body
        except socket.error, e:
            conn.close()
            self.status = str(e)
            self.version = ''
            return None

    def getListOfPersons(self):
        people = self.get('/people')
        if people is not None:
            return self.parsePeopleList(people)
        else:
            return []

    def parsePeopleList(self, body):
        people = []
        parser = HTMLParser(AbstractFormatter(NullWriter()))
        parser.feed(body)
        parser.close()
        for anchor in parser.anchorlist:
            if anchor.startswith('/people/'):
                person = anchor[len('/people/'):]
                if '/' not in person:
                    people.append(person)
        return people

    def getPersonInfo(self, person_id):
        person = self.get('/people/%s' % person_id)
        return person


class ServerSettingsDlg(wxDialog):

    def __init__(self, *args, **kwds):
        if len(args) < 1: kwds.setdefault('parent', None)
        if len(args) < 2: kwds.setdefault('id', -1)
        if len(args) < 3: kwds.setdefault('title', 'Server Settings')

        # begin wxGlade: ServerSettingsDlg.__init__
        kwds["style"] = wxDIALOG_MODAL|wxCAPTION
        wxDialog.__init__(self, *args, **kwds)
        self.serverLabel = wxStaticText(self, -1, "Server")
        self.serverTextCtrl = wxTextCtrl(self, -1, "localhost")
        self.portLabel = wxStaticText(self, -1, "Port")
        self.portTextCtrl = wxTextCtrl(self, -1, "8080")
        self.okBtn = wxButton(self, wxID_OK, "Ok")
        self.cancelBtn = wxButton(self, wxID_CANCEL, "Cancel")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        EVT_BUTTON(self, wxID_OK, self.OnOk)

    def __set_properties(self):
        # begin wxGlade: ServerSettingsDlg.__set_properties
        self.SetTitle("Server Settings")
        self.okBtn.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ServerSettingsDlg.__do_layout
        rootSizer = wxBoxSizer(wxVERTICAL)
        btnSizer = wxBoxSizer(wxHORIZONTAL)
        mainSizer = wxFlexGridSizer(2, 2, 16, 16)
        mainSizer.Add(self.serverLabel, 2, 0, 0)
        mainSizer.Add(self.serverTextCtrl, 0, wxEXPAND, 0)
        mainSizer.Add(self.portLabel, 2, 0, 0)
        mainSizer.Add(self.portTextCtrl, 0, wxEXPAND, 0)
        mainSizer.AddGrowableCol(1)
        rootSizer.Add(mainSizer, 1, wxALL|wxEXPAND, 16)
        btnSizer.Add(self.okBtn, 0, 0, 0)
        btnSizer.Add(self.cancelBtn, 0, wxLEFT, 16)
        rootSizer.Add(btnSizer, 0, wxLEFT|wxRIGHT|wxBOTTOM|wxALIGN_RIGHT, 16)
        self.SetAutoLayout(1)
        self.SetSizer(rootSizer)
        rootSizer.Fit(self)
        rootSizer.SetSizeHints(self)
        self.Layout()
        # end wxGlade

    def getServer(self):
        return self.serverTextCtrl.GetValue()
    def setServer(self, value):
        self.serverTextCtrl.SetValue(value)

    def getPort(self):
        return int(self.portTextCtrl.GetValue())
    def setPort(self, value):
        self.portTextCtrl.SetValue(str(value))

    def OnOk(self, event):
        if not self.getServer().strip():
            self.serverTextCtrl.SetFocus()
            wxBell()
            return
        try:
            port = self.getPort()
        except ValueError:
            port = -1
        if not 0 < port <= 65535:
            self.portTextCtrl.SetFocus()
            wxBell()
            return
        self.EndModal(wxID_OK)


ID_EXIT = wxNewId()
ID_SERVER = wxNewId()
ID_PEOPLE_LIST = wxNewId()


class MainFrame(wxFrame):

    __super = wxFrame
    __super___init__ = __super.__init__

    def __init__(self, client, parent=None, id=-1, title="SchoolTool"):
        self.__super___init__(parent, id, title, size=wxSize(500, 400))
        self.client = client
        self.CreateStatusBar()

        # Menu bar
        def menubar(*items):
            menubar = wxMenuBar()
            for menu, title in items:
                menubar.Append(menu, title)
            return menubar

        def menu(title, *items):
            menu = wxMenu()
            for item in items:
                getattr(menu, item[0])(*item[1:]) 
            return menu, title

        def separator():
            return ('AppendSeparator', )

        def item(title, description='', action=None, id=None):
            if not id:
                id = wxNewId()
            if action:
                EVT_MENU(self, id, action)
            return ('Append', id, title, description)

        def submenu(title, *items, **kw):
            description = kw.get('description', '')
            id = kw.get('id', None)
            if not id:
                id = wxNewId()
            submenu, title = menu(title, items)
            return ('AppendMenu', id, title, submenu, description)

        self.SetMenuBar(menubar(
            menu("&File",
                item("E&xit\tAlt+X", "Terminate the program", self.DoExit),
                ),
            menu("&View",
                item("&Refresh\tAlt+R", "Refresh the list of persons",
                     self.DoRefresh),
                ),
            menu("&Settings",
                item("&Server", "Server settings", self.DoServerSettings),
                ),
            menu("&Help",
                item("&About", "About SchoolTool", self.DoAbout),
                ),
            ))

        # client area
        splitter = wxSplitterWindow(self, -1)
        self.peopleListBox = wxListBox(splitter, ID_PEOPLE_LIST)
        self.personInfoText = wxHtmlWindow(splitter, -1)
        splitter.SetMinimumPaneSize(20)
        splitter.SplitVertically(self.peopleListBox, self.personInfoText, 100)

        EVT_LISTBOX(self, ID_PEOPLE_LIST, self.DoSelectPerson)

        self.SetSizeHints(minW=100, minH=100)
        self.refresh()

    def DoExit(self, event):
        self.Close(True)

    def DoServerSettings(self, event):
        dlg = ServerSettingsDlg(self)
        dlg.setServer(self.client.server)
        dlg.setPort(self.client.port)
        if dlg.ShowModal() == wxID_OK:
            self.client.setServer(dlg.getServer(), dlg.getPort())
            self.refresh()
        dlg.Destroy()

    def DoAbout(self, event):
        dlg = wxMessageDialog(self, __doc__, "About SchoolTool", wxOK)
        dlg.ShowModal()
        dlg.Destroy()

    def DoSelectPerson(self, event):
        person_id = self.peopleListBox.GetStringSelection()
        if not person_id:
            return
        info = self.client.getPersonInfo(person_id)
        if info is None:
            info = 'Could not connect to server'
        else:
            # XXX: horrible, but good enough for a proof-of-concept prototype
            info = info.replace('<img src="/people',
                                '<img src="http://%s:%s/people'
                                % (self.client.server, self.client.port))
        self.personInfoText.SetPage(info)
        self.SetStatusText(self.client.status)

    def DoRefresh(self, event):
        self.refresh()

    def refresh(self):
        people = self.client.getListOfPersons()
        self.SetStatusText(self.client.status)
        old_selection = self.peopleListBox.GetStringSelection()
        self.peopleListBox.Set(people)
        self.peopleListBox.SetStringSelection(old_selection)
        self.personInfoText.SetPage('')
        self.DoSelectPerson(None)


class SchoolToolApp(wxApp):

    __super = wxApp
    __super___init__ = __super.__init__

    def __init__(self, client):
        self.client = client
        self.__super___init__()

    def OnInit(self):
        frame = MainFrame(self.client)
        frame.Show(True)
        self.SetTopWindow(frame)
        return True


def main():
    wxInitAllImageHandlers()
    client = SchoolToolClient()
    app = SchoolToolApp(client)
    app.MainLoop()


if __name__ == '__main__':
    main()
