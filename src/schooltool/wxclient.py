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

import sets
from wxPython.wx import *
from guiclient import SchoolToolClient, SchoolToolError

__metaclass__ = type


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
ID_GROUP_TREE = wxNewId()


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
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)
        self.groupTreeCtrl = wxTreeCtrl(splitter, ID_GROUP_TREE,
                style=wxTR_HAS_BUTTONS|wxTR_HIDE_ROOT|wxSUNKEN_BORDER)
        splitter2 = wxSplitterWindow(splitter, -1, style=wxSP_NOBORDER)

        panel2a = wxPanel(splitter2, -1)
        label2a = wxStaticText(panel2a, -1, "Members")
        self.personListCtrl = wxListCtrl(panel2a, style=wxSUNKEN_BORDER)
        sizer2a = wxBoxSizer(wxVERTICAL)
        sizer2a.Add(label2a)
        sizer2a.Add(self.personListCtrl, 1, wxEXPAND)
        panel2a.SetSizer(sizer2a)

        panel2b = wxPanel(splitter2, -1)
        label2b = wxStaticText(panel2b, -1, "Relationships")
        self.relationshipListCtrl = wxListCtrl(panel2b,
                style=wxSUNKEN_BORDER|wxLC_REPORT)
        self.relationshipListCtrl.InsertColumn(0, "Title", width=110)
        self.relationshipListCtrl.InsertColumn(1, "Role", width=110)
        self.relationshipListCtrl.InsertColumn(2, "Relationship", width=110)
        sizer2b = wxBoxSizer(wxVERTICAL)
        sizer2b.Add(label2b)
        sizer2b.Add(self.relationshipListCtrl, 1, wxEXPAND)
        panel2b.SetSizer(sizer2b)

        splitter2.SetMinimumPaneSize(50)
        splitter2.SplitHorizontally(panel2a, panel2b, 150)
        splitter.SetMinimumPaneSize(20)
        splitter.SplitVertically(self.groupTreeCtrl, splitter2, 150)

        EVT_TREE_SEL_CHANGED(self, ID_GROUP_TREE, self.DoSelectGroup)

        self.SetSizeHints(minW=100, minH=150)
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

    def DoSelectGroup(self, event):
        self.personListData = []
        self.personListCtrl.DeleteAllItems()
        self.relationshipListData = []
        self.relationshipListCtrl.DeleteAllItems()
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            return
        group_id = self.groupTreeCtrl.GetPyData(item)

        try:
            info = self.client.getGroupInfo(group_id)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            return
        self.SetStatusText(self.client.status)
        self.personListData = info.members
        for idx, (title, person_id) in enumerate(self.personListData):
            self.personListCtrl.InsertStringItem(idx, title)
            self.personListCtrl.SetItemData(idx, idx)

        def compare(x, y):
            return cmp(self.personListData[x], self.personListData[y])

        self.personListCtrl.SortItems(compare)

        try:
            self.relationshipListData = self.client.getObjectRelationships(
                                                                    group_id)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            return
        self.SetStatusText(self.client.status)
        self.relationshipListData.sort()
        for idx, (arcrole, role, title, href) in enumerate(
                                                    self.relationshipListData):
            self.relationshipListCtrl.InsertStringItem(idx, title)
            self.relationshipListCtrl.SetItemData(idx, idx)
            self.relationshipListCtrl.SetStringItem(idx, 1, role)
            self.relationshipListCtrl.SetStringItem(idx, 2, arcrole)

    def DoRefresh(self, event):
        self.refresh()

    def refresh(self):
        # XXX reentrancy problems -- hold down Alt-R and watch

        try:
            group_tree = self.client.getGroupTree()
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            group_tree = []
        else:
            self.SetStatusText(self.client.status)

        # Remember current selection
        old_selection = None
        item = self.groupTreeCtrl.GetSelection()
        if item.IsOk():
            old_selection = self.groupTreeCtrl.GetPyData(item)

        # Remember which items were expanded
        expanded = sets.Set()
        stack = []
        root = self.groupTreeCtrl.GetRootItem()
        stack = [root]
        while stack:
            item = stack.pop()
            if item is not root and self.groupTreeCtrl.IsExpanded(item):
                expanded.add(self.groupTreeCtrl.GetPyData(item))
            next, cookie = self.groupTreeCtrl.GetFirstChild(item, 0)
            if next.IsOk():
                stack.append(next)
            next = self.groupTreeCtrl.GetNextSibling(item)
            if next.IsOk():
                stack.append(next)

        # Reload tree
        self.groupTreeCtrl.DeleteAllItems()
        root = self.groupTreeCtrl.AddRoot("Roots")
        self.groupTreeCtrl.Expand(root)
        stack = [(root, None)]
        selected_anything = False
        for level, title, href in group_tree:
            del stack[level+1:]
            assert len(stack) == level+1
            item = self.groupTreeCtrl.AppendItem(stack[-1][0], title)
            if level == 1 or stack[-1][1] in expanded:
                self.groupTreeCtrl.Expand(stack[-1][0])
            self.groupTreeCtrl.SetPyData(item, href)
            if href == old_selection and not selected_anything:
                selected_anything = True
                self.groupTreeCtrl.SelectItem(item)
            stack.append((item, href))

        if not selected_anything:
            self.groupTreeCtrl.Unselect()
            self.DoSelectGroup(None)


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
