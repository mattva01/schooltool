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

import os
import sets
import libxml2
import datetime
import threading
from cStringIO import StringIO
from wxPython.wx import *
from wxPython.grid import *
from wxPython.calendar import *
from wxPython.lib.popupctl import wxPopupControl
from wxPython.lib.scrolledpanel import wxScrolledPanel
from wxPython.html import wxHtmlWindow
from schooltool.clients.guiclient import SchoolToolClient, Unchanged
from schooltool.clients.guiclient import RollCallEntry, PersonInfo
from schooltool.clients.guiclient import SchoolToolError, ResponseStatusError
from schooltool.uris import URIMembership, URIGroup
from schooltool.uris import URITeaching, URITaught
from schooltool.uris import nameURI
from schooltool.common import parse_date, parse_time
from schooltool.translation import gettext as _

__metaclass__ = type


about_text = _("SchoolTool GUI client.\n"
"\n"
"SchoolTool is a common information systems platform for school administration"
"\nVisit http://www.schooltool.org/\n"
"\n"
"Copyright (c) 2003 Shuttleworth Foundation\n"
"\n"
"This program is free software; you can redistribute it and/or modify\n"
"it under the terms of the GNU General Public License as published by\n"
"the Free Software Foundation; either version 2 of the License, or\n"
"(at your option) any later version.")


#
# Common sets of window style flags
#

DEFAULT_DLG_STYLE = wxCAPTION | wxSYSTEM_MENU | wxDIALOG_MODAL
NONMODAL_DLG_STYLE = wxCAPTION | wxSYSTEM_MENU
RESIZABLE_WIN_STYLE = (wxCAPTION | wxSYSTEM_MENU | wxMINIMIZE_BOX
                       | wxMAXIMIZE_BOX | wxRESIZE_BORDER | wxTHICK_FRAME)
RESIZABLE_DLG_STYLE = (RESIZABLE_WIN_STYLE | wxDIALOG_MODAL) &~ wxMINIMIZE_BOX


#
# Helpers for building wxWindows menus
#

def menubar(*items):
    """Create a menu bar.

    Example:
      main_menu = menubar(menu(...), menu(...), menu(...))
      frame.SetMenuBar(main_menu)
    """
    menubar = wxMenuBar()
    for menu, title in items:
        menubar.Append(menu, title)
    return menubar


def menu(title, *items):
    """Create a submenu.

    Use as an argument to menubar.

    Example:
      menu("&File",
        item(...),
        item(...),
        separator(),
        menu(...))
    """
    return popupmenu(*items), title


def popupmenu(*items):
    """Create a popup menu.

    Example:
      popup = popupmenu(item(...), separator(...), submenu(...))
      control.PopupMenu(popup, wxPoint(10, 10))
    """
    menu = wxMenu()
    for item in items:
        getattr(menu, item[0])(*item[1:])
    return menu


def separator():
    """Create a separator.

    Use as an argument to menu, popupmenu or submenu,
    """
    return ('AppendSeparator', )


def item(title, description='', action=None, id=None, window=None):
    """Create a menu item.

    Use as an argument to menu, popupmenu or submenu,
    """
    if not id:
        id = wxNewId()
    if action:
        if window is None:
            try:
                window = action.im_self
            except AttributeError:
                raise TypeError("action argument should be a method"
                                " of the window object if the window is"
                                " not specified explicitly")
        EVT_MENU(window, id, action)
    return ('Append', id, title, description)


def submenu(title, *items, **kw):
    """Create a submenu.

    Use as an argument to menu, popupmenu or submenu,
    """
    description = kw.get('description', '')
    id = kw.get('id', None)
    if not id:
        id = wxNewId()
    submenu, title = menu(title, items)
    return ('AppendMenu', id, title, submenu, description)


def setupPopupMenu(control, menu):
    """Hook up a popup menu to the control."""

    # Event handlers

    def list_mouse_down(event):
        """Right mouse button down (on a list control)"""
        item, flags = control.HitTest(event.GetPosition())
        if item != -1:
            control.Select(item)
        event.Skip()

    def tree_mouse_down(event):
        """Right mouse button down (on a tree control)"""
        item, flags = control.HitTest(event.GetPosition())
        if item.IsOk():
            control.SelectItem(item)
        event.Skip()

    def mouse_up(event):
        """Right mouse button up"""
        control.PopupMenu(menu, event.GetPosition())

    def click(event):
        """Right mouse button click"""
        # event is a wxCommandEvent and, sadly, does not have GetPosition()
        pos = control.ScreenToClient(wxGetMousePosition())
        control.PopupMenu(menu, pos)

    # This is tricky.  Tree controls need as much as four event
    # handlers for the popup menu to work correctly on all platforms.
    # List controls need "only" three.
    if isinstance(control, wxListCtrl):
        EVT_RIGHT_DOWN(control, list_mouse_down)
    if isinstance(control, wxTreeCtrl):
        EVT_RIGHT_DOWN(control, tree_mouse_down)
        EVT_TREE_ITEM_RIGHT_CLICK(control, control.GetId(), click)
    # The following ones work for all controls
    EVT_RIGHT_UP(control, mouse_up)
    EVT_COMMAND_RIGHT_CLICK(control, control.GetId(), click)


#
# A date entry box
#

class DateCtrl(wxPopupControl):
    """A text control with a popup for calendars.

    wxPopupControl has bugs:
     - DateCtrl is ugly, especially on Windows.
     - You cannot close the popup calendar by clicking outside it.
     - And automatic sizing work, you need to call SetSize manually before
       adding a DateCtrl into a sizer.
    """

    def __init__(self, *args, **kw):
        wxPopupControl.__init__(self, *args, **kw)
        self.win = wxWindow(self, -1, pos=(0, 0), style=wxSIMPLE_BORDER)
        self.cal = wxCalendarCtrl(self.win, -1, pos=(0, 0))
        self.win.SetSize(self.cal.GetBestSize())
        self.SetPopupContent(self.win)
        EVT_CALENDAR_DAY(self.cal, self.cal.GetId(), self.OnCalSelected)

    def OnCalSelected(self, event):
        self.PopDown()
        date = self.cal.GetDate()
        self.SetValue('%04d-%02d-%02d' %
                      (date.GetYear(), date.GetMonth() + 1, date.GetDay()))
        event.Skip()

    def FormatContent(self):
        """Called just before the popup is displayed.

        Method overridden from wxPopupControl.

        Parse the text in the control and select the correct date in the
        calendar control.
        """
        try:
            d = parse_date(self.GetValue())
        except ValueError:
            self.cal.SetDate(wxDateTime_Today())
        else:
            self.cal.SetDate(wxDateTimeFromDMY(d.day, d.month - 1, d.year))


#
# Dialog windows
#

class ServerSettingsDlg(wxDialog):
    """Server Settings dialog."""

    def __init__(self, *args, **kwds):
        if len(args) < 1: kwds.setdefault('parent', None)
        if len(args) < 2: kwds.setdefault('id', -1)
        if len(args) < 3: kwds.setdefault('title', 'Server Settings')

        # begin wxGlade: ServerSettingsDlg.__init__
        kwds["style"] = wxDIALOG_MODAL|wxCAPTION|wxSYSTEM_MENU
        wxDialog.__init__(self, *args, **kwds)
        self.serverLabel = wxStaticText(self, -1, _("Server"))
        self.serverTextCtrl = wxTextCtrl(self, -1, "localhost")
        self.portLabel = wxStaticText(self, -1, _("Port"))
        self.portTextCtrl = wxTextCtrl(self, -1, "7001")
        self.userLabel = wxStaticText(self, -1, _("Username"))
        self.userTextCtrl = wxTextCtrl(self, -1, "")
        self.passwordLabel = wxStaticText(self, -1, _("Password"))
        self.passwordTextCtrl = wxTextCtrl(self, -1, "", style=wxTE_PASSWORD)
        self.okBtn = wxButton(self, wxID_OK, _("Ok"))
        self.cancelBtn = wxButton(self, wxID_CANCEL, _("Cancel"))

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.CenterOnScreen(wx.wxBOTH)

        EVT_BUTTON(self, wxID_OK, self.OnOk)

    def __set_properties(self):
        # begin wxGlade: ServerSettingsDlg.__set_properties
        self.SetTitle(_("Server Settings"))
        self.okBtn.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: ServerSettingsDlg.__do_layout
        rootSizer = wxBoxSizer(wxVERTICAL)
        btnSizer = wxBoxSizer(wxHORIZONTAL)
        mainSizer = wxFlexGridSizer(4, 2, 4, 16)
        mainSizer.Add(self.serverLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        mainSizer.Add(self.serverTextCtrl, 0,
                      wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)
        mainSizer.Add(self.portLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        mainSizer.Add(self.portTextCtrl, 0,
                      wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)
        mainSizer.Add(self.userLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        mainSizer.Add(self.userTextCtrl, 0,
                      wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)
        mainSizer.Add(self.passwordLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        mainSizer.Add(self.passwordTextCtrl, 0,
                      wxEXPAND|wxALIGN_CENTER_VERTICAL, 0)
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

    def getUser(self):
        return self.userTextCtrl.GetValue()

    def setUser(self, value):
        self.userTextCtrl.SetValue(value)

    def getPassword(self):
        return self.passwordTextCtrl.GetValue()

    def setPassword(self, value):
        self.passwordTextCtrl.SetValue(value)

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


class RollCallInfoDlg(wxDialog):
    """More info popup of the roll call dialog"""

    def __init__(self, parent, title, show_resolved):
        wxDialog.__init__(self, parent, -1, title, style=DEFAULT_DLG_STYLE)
        self.show_resolved = show_resolved

        vsizer = wxBoxSizer(wxVERTICAL)
        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.text_ctrl = wxTextCtrl(self, -1, style=wxTE_MULTILINE,
                                    size=wxSize(300, 100))
        hsizer.Add(self.text_ctrl, 1, wxEXPAND)

        radio_sizer = wxBoxSizer(wxVERTICAL)
        self.undecided_btn = wxRadioButton(self, -1, _("Unset"),
                                           style=wxRB_GROUP)
        self.undecided_btn.Hide()

        self.resolve_btn = wxRadioButton(self, -1, _("Resolve"))
        if not show_resolved:
            self.resolve_btn.Hide()
        radio_sizer.Add(self.resolve_btn)

        self.dont_resolve_btn = wxRadioButton(self, -1, _("Do not resolve"))
        if not show_resolved:
            self.dont_resolve_btn.Hide()
        radio_sizer.Add(self.dont_resolve_btn)

        if show_resolved:
            hsizer.Add(radio_sizer, 0, wxLEFT, 4)

        vsizer.Add(hsizer, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnOk(self, event):
        """Verify that all data is entered before closing the dialog."""
        if self.show_resolved:
            if self.resolve_btn.GetValue() == self.dont_resolve_btn.GetValue():
                self.resolve_btn.SetFocus()
                wxBell()
                return
        self.EndModal(wxID_OK)

    def setComment(self, comment):
        if comment is None:
            self.text_ctrl.SetValue("")
        else:
            self.text_ctrl.SetValue(comment)

    def getComment(self):
        return self.text_ctrl.GetValue()

    def setResolved(self, resolved):
        if resolved is Unchanged:
            self.undecided_btn.SetValue(True)
        elif resolved:
            self.resolve_btn.SetValue(True)
        else:
            self.dont_resolve_btn.SetValue(True)

    def getResolved(self):
        if self.resolve_btn.GetValue():
            return True
        elif self.dont_resolve_btn.GetValue():
            return False
        else:
            return Unchanged


class RollCallDlg(wxDialog):
    """Roll call dialog."""

    def __init__(self, parent, group_title, group_path, rollcall, client):
        title = _("Roll Call for %s") % group_title
        wxDialog.__init__(self, parent, -1, title, style=RESIZABLE_DLG_STYLE)
        self.title = title
        self.group_title = group_title
        self.group_path = group_path
        self.client = client

        vsizer = wxBoxSizer(wxVERTICAL)

        scrolled_panel = wxScrolledPanel(self, -1)
        grid = wxFlexGridSizer(len(rollcall), 5, 4, 8)
        self.items = []
        self.entries_by_id = {}
        for item in rollcall:
            entry = RollCallEntry(item.person_path)
            entry.item = item
            grid.Add(wxStaticText(scrolled_panel, -1, item.person_title),
                     0, wxALIGN_CENTER_VERTICAL|wxRIGHT, 4)

            if item.present:
                presence = ""
            else:
                presence = _("reported absent")
            grid.Add(wxStaticText(scrolled_panel, -1, presence),
                     0, wxALIGN_CENTER_VERTICAL|wxRIGHT, 4)

            unknown_btn = wxRadioButton(scrolled_panel, -1, _("Unset"),
                                        style=wxRB_GROUP)
            unknown_btn.Hide()

            present_btn = wxRadioButton(scrolled_panel, -1, _("Present"))
            self.entries_by_id[present_btn.GetId()] = entry
            EVT_RADIOBUTTON(self, present_btn.GetId(), self.OnPresentSelected)
            grid.Add(present_btn)

            absent_btn = wxRadioButton(scrolled_panel, -1, _("Absent"))
            self.entries_by_id[absent_btn.GetId()] = entry
            EVT_RADIOBUTTON(self, absent_btn.GetId(), self.OnAbsentSelected)
            grid.Add(absent_btn)

            more_btn = wxButton(scrolled_panel, -1, "...", style=wxBU_EXACTFIT)
            self.entries_by_id[more_btn.GetId()] = entry
            EVT_BUTTON(self, more_btn.GetId(), self.OnMoreInfo)
            grid.Add(more_btn, 0, wxRIGHT, 4)

            self.items.append((entry, present_btn))
        scrolled_panel.SetSizer(grid)
        scrolled_panel.SetupScrolling(scroll_x=False)
        grid.AddGrowableCol(3)
        grid.Fit(scrolled_panel)
        vsizer.Add(scrolled_panel, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        ok_btn.SetDefault()
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnPresentSelected(self, event):
        """Mark the person as present or absent."""
        entry = self.entries_by_id[event.GetId()]
        entry.presence = True
        if not entry.item.present and entry.resolved is Unchanged:
            self.moreInfoDlg(entry)

    def OnAbsentSelected(self, event):
        """Mark the person as present or absent."""
        entry = self.entries_by_id[event.GetId()]
        entry.presence = False

    def OnMoreInfo(self, event):
        """Show the more info dialog."""
        entry = self.entries_by_id[event.GetId()]
        self.moreInfoDlg(entry)

    def moreInfoDlg(self, entry):
        """Show the more info for an entry."""
        show_resolved = not entry.item.present and entry.presence == True
        dlg = RollCallInfoDlg(self, entry.item.person_title,
                              show_resolved=show_resolved)
        dlg.setComment(entry.comment)
        dlg.setResolved(entry.resolved)
        if dlg.ShowModal() == wxID_OK:
            entry.comment = dlg.getComment()
            entry.resolved = dlg.getResolved()
        dlg.Destroy()

    def OnOk(self, event):
        """Verify that all data is entered before closing the dialog."""
        rollcall = []
        for (entry, present_btn) in self.items:
            if entry.presence is Unchanged:
                present_btn.SetFocus()
                wxBell()
                return
            show_resolved = not entry.item.present and entry.presence == True
            if show_resolved and entry.resolved is Unchanged:
                wxBell()
                self.moreInfoDlg(entry)
            if not entry.presence:
                entry.resolved = Unchanged
            rollcall.append(entry)
        try:
            self.client.submitRollCall(self.group_path, rollcall)
        except SchoolToolError, e:
            wxMessageBox(_("Could not submit the roll call: %s") % e,
                         self.title, wxICON_ERROR|wxOK)
        else:
            self.EndModal(wxID_OK)


class AbsenceFrame(wxDialog):
    """Window showing the list of person's absences."""

    def __init__(self, client, path, title, parent=None, id=-1,
                 detailed=True, persons=True, absence_data=None):
        """Create an absence list window.

        Two arguments influence the contents of the absence list:
        - if detailed is False, only a single column containing an
          overview of an absence is shown (John Doe absent for 2h15m)
        - if detailed is True, the absence list has a number columns
          showing its exact state
        - person specifies whether the person name should be shown in
          a column in detailed mode (it makes sense to disable it when
          viewing absences for a single person)
        """
        wxDialog.__init__(self, parent, id, title, size=wxSize(600, 400),
                          style=RESIZABLE_WIN_STYLE)
        self.client = client
        self.title = title
        self.path = path
        self.absence_data = []
        self.persons = persons
        self.detailed = detailed

        main_sizer = wxBoxSizer(wxVERTICAL)
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)

        panel1 = wxPanel(splitter, -1)
        label1 = wxStaticText(panel1, -1, _("Absences"))
        ID_ABSENCE_LIST = wxNewId()
        self.absence_list = wxListCtrl(panel1, ID_ABSENCE_LIST,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        if self.detailed:
            self.absence_list.InsertColumn(0, _("Date"), width=140)
            self.absence_list.InsertColumn(1, _("Ended?"), width=80)
            self.absence_list.InsertColumn(2, _("Resolved?"), width=80)
            self.absence_list.InsertColumn(3, _("Expected Presence"),
                                           width=150)
            self.absence_list.InsertColumn(4, _("Last Comment"), width=200)
            if self.persons:
                self.absence_list.InsertColumn(1, _("Person"), width=110)
        else:
            self.absence_list.InsertColumn(0, _("Absence"), width=580)
        EVT_LIST_ITEM_SELECTED(self, ID_ABSENCE_LIST, self.DoSelectAbsence)
        sizer1 = wxBoxSizer(wxVERTICAL)
        sizer1.Add(label1)
        sizer1.Add(self.absence_list, 1, wxEXPAND)
        panel1.SetSizer(sizer1)

        panel2 = wxPanel(splitter, -1)
        label2 = wxStaticText(panel2, -1, _("Comments"))
        self.comment_list = wxListCtrl(panel2, -1,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        self.comment_list.InsertColumn(0, _("Date"), width=140)
        self.comment_list.InsertColumn(1, _("Reporter"), width=110)
        self.comment_list.InsertColumn(2, _("Absent From"), width=110)
        self.comment_list.InsertColumn(3, _("Ended?"), width=80)
        self.comment_list.InsertColumn(4, _("Resolved?"), width=80)
        self.comment_list.InsertColumn(5, _("Expected Presence"), width=150)
        self.comment_list.InsertColumn(6, _("Comment"), width=200)
        sizer2 = wxBoxSizer(wxVERTICAL)
        sizer2.Add(label2)
        sizer2.Add(self.comment_list, 1, wxEXPAND)
        panel2.SetSizer(sizer2)

        splitter.SetMinimumPaneSize(50)
        splitter.SplitHorizontally(panel1, panel2, 200)
        main_sizer.Add(splitter, 1, wxEXPAND|wxLEFT|wxRIGHT|wxTOP, 8)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        close_btn = wxButton(self, wxID_CLOSE, _("Close"))
        EVT_BUTTON(self, wxID_CLOSE, self.OnClose)
        close_btn.SetDefault()
        button_bar.Add(close_btn)
        main_sizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(main_sizer)
        self.SetSizeHints(minW=200, minH=200)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

        self.DoRefresh(data=absence_data)

    def OnClose(self, event=None):
        """Close the absence window."""
        self.Close(True)

    def DoRefresh(self, event=None, data=None):
        """Refresh the absence list."""
        self.absence_list.DeleteAllItems()
        self.absence_data = []
        self.comment_list.DeleteAllItems()
        self.comment_data = []
        if data is not None:
            self.absence_data = data
        else:
            try:
                self.absence_data = self.client.getAbsences(self.path)
            except SchoolToolError, e:
                wxMessageBox(_("Could not get the list of absences: %s") % e,
                             self.title, wxICON_ERROR|wxOK)
                return
        if self.detailed:
            # sort newest absences first
            self.absence_data.sort()
            self.absence_data.reverse()
            for idx, absence in enumerate(self.absence_data):
                self.absence_list.InsertStringItem(idx,
                        absence.datetime.strftime('%Y-%m-%d %H:%M'))
                self.absence_list.SetItemData(idx, idx)
                if self.persons:
                    self.absence_list.SetStringItem(idx, 1,
                                                    absence.person_title)
                    n = 1
                else:
                    n = 0
                self.absence_list.SetStringItem(idx, n+1,
                        absence.ended and _("Yes") or _("No"))
                self.absence_list.SetStringItem(idx, n+2,
                        absence.resolved and _("Yes") or _("No"))
                if absence.expected_presence is not None:
                    self.absence_list.SetStringItem(idx, n+3,
                        absence.expected_presence.strftime('%Y-%m-%d %H:%M'))
                self.absence_list.SetStringItem(idx, n+4, absence.last_comment)
                if not absence.ended:
                    item = self.absence_list.GetItem(idx)
                    item.SetTextColour(wxRED)
                    self.absence_list.SetItem(item)
                elif not absence.resolved:
                    item = self.absence_list.GetItem(idx)
                    item.SetTextColour(wxBLUE)
                    self.absence_list.SetItem(item)
        else:
            # sort unexpected absences first, then sort by date (oldest first)
            absences = [(absence.expected(),
                         absence.expected_presence or absence.datetime,
                         absence) for absence in self.absence_data]
            absences.sort()
            self.absence_data = [row[-1] for row in absences]
            for idx, absence in enumerate(self.absence_data):
                self.absence_list.InsertStringItem(idx, str(absence))
                self.absence_list.SetItemData(idx, idx)
                if not absence.expected():
                    item = self.absence_list.GetItem(idx)
                    item.SetTextColour(wxRED)
                    self.absence_list.SetItem(item)

    def DoSelectAbsence(self, event):
        """Refresh the absence comment list."""
        self.comment_list.DeleteAllItems()
        self.comment_data = []

        key = self.absence_list.GetItemData(event.m_itemIndex)
        absence = self.absence_data[key]
        try:
            self.comment_data = self.client.getAbsenceComments(
                                    absence.absence_path)
        except SchoolToolError, e:
            return
        # sort newest comments first
        self.comment_data.sort()
        self.comment_data.reverse()
        for idx, comment in enumerate(self.comment_data):
            self.comment_list.InsertStringItem(idx,
                    comment.datetime.strftime('%Y-%m-%d %H:%M'))
            self.comment_list.SetItemData(idx, idx)
            self.comment_list.SetStringItem(idx, 1, comment.reporter_title)
            self.comment_list.SetStringItem(idx, 2, comment.absent_from_title)
            if comment.ended is not Unchanged:
                self.comment_list.SetStringItem(idx, 3,
                        comment.ended and _("Yes") or _("No"))
            if comment.resolved is not Unchanged:
                self.comment_list.SetStringItem(idx, 4,
                        comment.resolved and _("Yes") or _("No"))
            if comment.expected_presence is not Unchanged:
                if comment.expected_presence is not None:
                    self.comment_list.SetStringItem(idx, 5,
                        comment.expected_presence.strftime('%Y-%m-%d %H:%M'))
                else:
                    self.comment_list.SetStringItem(idx, 5, "-")
            self.comment_list.SetStringItem(idx, 6, comment.text)


class SchoolTimetableGridTable(wxPyGridTableBase):
    """Back-end for the school time table grid."""

    def __init__(self, tt):
        wxPyGridTableBase.__init__(self)
        self.tt = tt

    def GetNumberCols(self):
        return len(self.tt.periods)

    def GetColLabelValue(self, col):
        return "%s, %s" % self.tt.periods[col]

    def GetNumberRows(self):
        return len(self.tt.teachers)

    def GetRowLabelValue(self, row):
        return self.tt.teachers[row][1]

    def IsEmptyCell(self, row, col):
        return len(self.tt.tt[row][col]) == 0

    def GetValue(self, row, col):
        rows = []
        for title, path, resources in self.tt.tt[row][col]:
            if resources:
                resource_titles = [rtitle for rtitle, rpath in resources]
                resource_titles.sort()
                rows.append("%s (%s)" % (title, ', '.join(resource_titles)))
            else:
                rows.append(title)
        rows.sort()
        return ",\n".join(rows)

    def SetValue(self, row, col, value):
        pass


class ResourceSelectionDlg(wxDialog):
    """Resource selection popup of the school timetable grid"""

    def __init__(self, parent, activity_title, teacher_title, period_key,
                 choices):
        title = _("Resource Assignment")
        wxDialog.__init__(self, parent, -1, title, style=DEFAULT_DLG_STYLE)

        self.choices = list(choices)
        self.choices.sort()

        vsizer = wxBoxSizer(wxVERTICAL)
        static_text = wxStaticText(self, -1,
                            _("%s, %s\nTeacher: %s\nActivity: %s") %
                            (period_key[0], period_key[1], teacher_title,
                             activity_title))
        vsizer.Add(static_text, 0, wxLEFT|wxRIGHT|wxTOP, 8)

        static_text = wxStaticText(self, -1, _("Resources"))
        vsizer.Add(static_text, 0, wxLEFT|wxRIGHT|wxTOP, 8)

        # wxLB_EXTENDED would be nicer, but then SetSelection stops working
        # for completely obscure reasons
        self.listbox = wxListBox(self, -1, style=wxLB_MULTIPLE,
                            choices=[title for title, value in self.choices])
        vsizer.Add(self.listbox, 1, wxEXPAND|wxLEFT|wxRIGHT|wxBOTTOM, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def setSelection(self, selection):
        selected = sets.Set()
        for title, path in selection:
            selected.add(path)
        for idx, (title, path) in enumerate(self.choices):
            if path in selected:
                self.listbox.SetSelection(idx)
            else:
                self.listbox.Deselect(idx)

    def getSelection(self):
        return [self.choices[idx] for idx in self.listbox.GetSelections()]


class ActivitySelectionDlg(wxDialog):
    """Activity selection popup of the school timetable grid"""

    def __init__(self, parent, teacher_title, period_key, choices, resources):
        title = _("Activity Selection")
        wxDialog.__init__(self, parent, -1, title, style=DEFAULT_DLG_STYLE)

        self.teacher_title = teacher_title
        self.period_key = period_key
        self.resources = resources
        self.choices = [(title, path, []) for title, path in choices]
        self.choices.sort()

        vsizer = wxBoxSizer(wxVERTICAL)
        static_text = wxStaticText(self, -1, _("%s, %s\nTeacher: %s") %
                            (period_key[0], period_key[1], teacher_title))
        vsizer.Add(static_text, 0, wxLEFT|wxRIGHT|wxTOP, 8)

        static_text = wxStaticText(self, -1, _("Activities"))
        vsizer.Add(static_text, 0, wxLEFT|wxRIGHT|wxTOP, 8)

        self.listbox = wxCheckListBox(self, -1,
                                      choices=[c[0] for c in self.choices])
        vsizer.Add(self.listbox, 1, wxEXPAND|wxLEFT|wxRIGHT|wxBOTTOM, 8)
        EVT_LISTBOX_DCLICK(self, self.listbox.GetId(), self.OnListDClick)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        resource_btn = wxButton(self, -1, _("&Assign Resources"))
        EVT_BUTTON(self, resource_btn.GetId(), self.OnAssignResources)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        ok_btn.SetDefault()
        button_bar.Add(resource_btn, 0, 0, 0)
        button_bar.Add(wxPanel(self, -1), 1, wxEXPAND)
        button_bar.Add(ok_btn, 0, wxLEFT|wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxEXPAND|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnListDClick(self, event):
        self.DoAssignResources(event.GetSelection())

    def OnAssignResources(self, event=None):
        idx = self.listbox.GetSelection()
        if idx != -1:
            self.DoAssignResources(idx)

    def DoAssignResources(self, idx):
        title, path, resources = self.choices[idx]
        dlg = ResourceSelectionDlg(self, title, self.teacher_title,
                                   self.period_key, self.resources)
        dlg.setSelection(resources)
        if dlg.ShowModal() == wxID_OK:
            # Important: in-place modification of self.choices
            resources[:] = dlg.getSelection()
            resources.sort()
            resource_titles = ', '.join([r[0] for r in resources])
            if resource_titles:
                title += ' (%s)' % resource_titles
            self.listbox.SetString(idx, title)
            self.listbox.Check(idx)
        dlg.Destroy()

    def setSelection(self, selection):
        selected = {}
        for title, path, resources in selection:
            selected[path] = resources
        for idx, (title, path, resources) in enumerate(self.choices):
            is_selected = path in selected
            if is_selected:
                # Important: in-place modification of self.choices
                resources[:] = selected[path]
                resources.sort()
            resource_titles = ', '.join([r[0] for r in resources])
            if resource_titles:
                title += ' (%s)' % resource_titles
            self.listbox.SetString(idx, title)
            self.listbox.Check(idx, is_selected)

    def getSelection(self):
        selection = []
        for idx, choice in enumerate(self.choices):
            if self.listbox.IsChecked(idx):
                selection.append(choice)
        return selection


class NewPersonDlg(wxDialog):
    """A dialog to enter the name, login, and password of a new user."""

    def __init__(self, parent):
        self.title = _("New Person")
        wxDialog.__init__(self, parent, -1, self.title,
                          style=wxDIALOG_MODAL|wxCAPTION)
        self.client = parent.client

        nameLabel = wxStaticText(self, -1, _("Name"))
        userLabel = wxStaticText(self, -1, _("Username"))
        passwdLabel = wxStaticText(self, -1, _("Password"))
        passwd2Label = wxStaticText(self, -1, _("Password (again)"))

        self.nameTextCtrl = wxTextCtrl(self, -1, "")
        self.userTextCtrl = wxTextCtrl(self, -1, "")
        self.passwdTextCtrl = wxTextCtrl(self, -1, "", style=wxTE_PASSWORD)
        self.passwd2TextCtrl = wxTextCtrl(self, -1, "", style=wxTE_PASSWORD)

        sizer = wxFlexGridSizer(4, 2, 4, 16)

        sizer.Add(nameLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        sizer.Add(self.nameTextCtrl, 0, wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)

        sizer.Add(userLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        sizer.Add(self.userTextCtrl, 0, wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)

        sizer.Add(passwdLabel, 2, wxALIGN_CENTER_VERTICAL, 0)
        sizer.Add(self.passwdTextCtrl, 0, wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)

        sizer.Add(passwd2Label, 2, wxALIGN_CENTER_VERTICAL, 0)
        sizer.Add(self.passwd2TextCtrl, 0, wxALIGN_CENTER_VERTICAL|wxEXPAND, 0)

        vsizer = wxBoxSizer(wxVERTICAL)
        vsizer.Add(sizer, 0, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxLEFT|wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxEXPAND|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnOk(self, event):
        """Verify that all data is entered before closing the dialog."""
        if self.passwdTextCtrl.GetValue() != self.passwd2TextCtrl.GetValue():
            wxMessageBox(_("Passwords do not match"), self.title,
                         wxICON_ERROR|wxOK)
            return
        name = self.nameTextCtrl.GetValue()
        username = self.userTextCtrl.GetValue()
        password = self.passwdTextCtrl.GetValue()

        try:
            self.client.createPerson(name, username, password)
        except SchoolToolError, e:
            wxMessageBox(_("Could not create a new person: %s") % e,
                         self.title, wxICON_ERROR|wxOK)
        else:
            self.EndModal(wxID_OK)


class SchoolTimetableGrid(wxGrid):

    def __init__(self, parent, tt, resources):
        wxGrid.__init__(self, parent, -1)
        self.tt = tt
        self.resources = resources
        self.SetTable(SchoolTimetableGridTable(tt), True)
        # There is no way to auto-size row labels.
        self.SetRowLabelSize(150)

        EVT_GRID_EDITOR_SHOWN(self, self.OnEditorShown)
        EVT_GRID_CELL_LEFT_DCLICK(self, self.OnEdit)

    def OnEdit(self, event=None):
        """Open the activity selection dialog"""
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

    def OnEditorShown(self, event):
        row = event.GetRow()
        col = event.GetCol()
        event.Veto()

        teacher_path, teacher_title, choices = self.tt.teachers[row]
        dlg = ActivitySelectionDlg(self, teacher_title, self.tt.periods[col],
                                   choices, self.resources)
        dlg.setSelection(self.tt.tt[row][col])
        if dlg.ShowModal() == wxID_OK:
            self.tt.tt[row][col] = dlg.getSelection()
            msg = wxGridTableMessage(self.GetTable(),
                                     wxGRIDTABLE_REQUEST_VIEW_GET_VALUES)
            self.ProcessTableMessage(msg)
        dlg.Destroy()


class SchoolTimetableFrame(wxDialog):
    """Window showing a timetable for the whole school."""

    def __init__(self, client, key, tt, resources, parent=None, id=-1):
        title = _("School Timetable (%s, %s)") % key
        wxDialog.__init__(self, parent, id, title, size=wxSize(600, 400),
                          style=RESIZABLE_WIN_STYLE)
        self.title = title
        self.client = client
        self.key = key
        self.tt = tt

        main_sizer = wxBoxSizer(wxVERTICAL)
        self.grid = grid = SchoolTimetableGrid(self, tt, resources)
        main_sizer.Add(grid, 1, wxEXPAND|wxALL, 8)
        self.OnResize()

        static_line = wxStaticLine(self, -1)
        main_sizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        resize_btn = wxButton(self, -1, _("&Fit Cells"))
        EVT_BUTTON(self, resize_btn.GetId(), self.OnResize)
        edit_btn = wxButton(self, -1, _("&Edit Cell"))
        EVT_BUTTON(self, edit_btn.GetId(), grid.OnEdit)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        ok_btn.SetDefault()
        button_bar.Add(resize_btn, 0, 0, 0)
        button_bar.Add(edit_btn, 0, wxLEFT, 16)
        button_bar.Add(wxPanel(self, -1), 1, wxEXPAND)
        button_bar.Add(ok_btn, 0, wxLEFT, 16)
        button_bar.Add(cancel_btn, 0, wxLEFT, 16)
        main_sizer.Add(button_bar, 0, wxEXPAND|wxALL, 16)

        self.SetSizer(main_sizer)
        min_size = main_sizer.GetMinSize()
        self.SetSizeHints(minW=max(200, min_size.width),
                          minH=max(200, min_size.height))
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnClose(self, event=None):
        """Close the window."""
        self.Close(True)

    def OnOk(self, event=None):
        """Save the edited timetable to the server."""
        try:
            period, schema = self.key
            self.client.putSchooltoolTimetable(period, schema, self.tt)
        except SchoolToolError, e:
            wxMessageBox(_("Could not submit the roll call: %s") % e,
                         self.title, wxICON_ERROR|wxOK)
        else:
            self.Close(True)

    def OnResize(self, event=None):
        """Auto-size the grid"""
        self.grid.AutoSizeRows()
        self.grid.AutoSizeColumns()


class BrowserFrame(wxDialog):
    """Window showing a web page."""

    def __init__(self, title, url, parent=None, id=-1):
        wxDialog.__init__(self, parent, id, title, size=wxSize(600, 400),
                          style=RESIZABLE_WIN_STYLE)

        main_sizer = wxBoxSizer(wxVERTICAL)
        self.htmlwin = wxHtmlWindow(self, -1)
        self.htmlwin.LoadPage(url)
        main_sizer.Add(self.htmlwin, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        main_sizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        back_btn = wxButton(self, -1, _("&Back"))
        EVT_BUTTON(self, back_btn.GetId(), self.OnBack)
        forward_btn = wxButton(self, -1, _("&Forward"))
        EVT_BUTTON(self, forward_btn.GetId(), self.OnForward)
        close_btn = wxButton(self, wxID_CLOSE, _("Close"))
        EVT_BUTTON(self, wxID_CLOSE, self.OnClose)
        close_btn.SetDefault()
        button_bar.Add(back_btn)
        button_bar.Add(forward_btn, 0, wxLEFT, 16)
        button_bar.Add(wxPanel(self, -1), 1, wxEXPAND)
        button_bar.Add(close_btn, 0, wxLEFT, 16)
        main_sizer.Add(button_bar, 0, wxEXPAND|wxALL, 16)

        self.SetSizer(main_sizer)
        min_size = main_sizer.GetMinSize()
        self.SetSizeHints(minW=max(200, min_size.width),
                          minH=max(200, min_size.height))
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnBack(self, event=None):
        """Go back in histrory."""
        self.htmlwin.HistoryBack()

    def OnForward(self, event=None):
        """Go forward in histrory."""
        self.htmlwin.HistoryForward()

    def OnClose(self, event=None):
        """Close the window."""
        self.Close(True)


class AvailabilitySearchFrame(wxDialog):
    """Window for doing resource availability searches."""

    default_hour_selection = range(9, 21)
    default_duration = 30

    def __init__(self, client, parent=None, id=-1):
        title = _("Search for Available Resources")
        wxDialog.__init__(self, parent, id, title, size=wxSize(600, 400),
                          style=RESIZABLE_WIN_STYLE)
        self.client = client
        self.title = title
        self.ok = False

        try:
            self.resources = self.client.getListOfResources()
        except SchoolToolError, e:
            wxMessageBox(_("Could not get the list of resources: %s") % e,
                         title, wxICON_ERROR|wxOK)
            return
        else:
            self.resources.sort()

        main_sizer = wxBoxSizer(wxVERTICAL)
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)

        panel1 = wxPanel(splitter, -1)
        sizer1 = wxBoxSizer(wxHORIZONTAL)

        sizer1a = wxBoxSizer(wxVERTICAL)
        label1 = wxStaticText(panel1, -1, _("Resources"))
        self.resource_list = wxListBox(panel1, -1, style=wxLB_MULTIPLE,
                                       choices=[r[0] for r in self.resources])
        sizer1a.Add(label1)
        sizer1a.Add(self.resource_list, 1, wxEXPAND)

        sizer1b = wxBoxSizer(wxVERTICAL)
        label2 = wxStaticText(panel1, -1, _("Hours"))
        self.hour_list = wxListBox(panel1, -1, style=wxLB_MULTIPLE,
                                   choices=[str(h) for h in range(24)])
        if self.default_hour_selection:
            for hour in self.default_hour_selection:
                self.hour_list.SetSelection(hour)
            self.hour_list.SetFirstItem(self.default_hour_selection[0])
        sizer1b.Add(label2)
        sizer1b.Add(self.hour_list, 1, wxEXPAND)

        sizer1c = wxBoxSizer(wxVERTICAL)

        self.first_date_ctrl = DateCtrl(panel1, -1)
        self.last_date_ctrl = DateCtrl(panel1, -1)
        self.duration_ctrl = wxTextCtrl(panel1, -1, str(self.default_duration))
        minute_label = wxStaticText(panel1, -1, _("min"))
        date_size = self.duration_ctrl.GetSize()
        date_size.width += 8 + minute_label.GetSize().GetWidth()

        grid_sizer = wxFlexGridSizer(cols=2, hgap=8, vgap=8)
        grid_sizer.Add(wxStaticText(panel1, -1, _("First date")))
        today = datetime.date.today().strftime('%Y-%m-%d')
        self.first_date_ctrl.SetValue(today)
        self.first_date_ctrl.SetSize(date_size)
        grid_sizer.Add(self.first_date_ctrl, 1)
        grid_sizer.Add(wxStaticText(panel1, -1, _("Last date")))
        self.last_date_ctrl.SetValue(today)
        self.last_date_ctrl.SetSize(date_size)
        grid_sizer.Add(self.last_date_ctrl, 1)
        grid_sizer.Add(wxStaticText(panel1, -1, _("Duration")))
        hsizer = wxBoxSizer(wxHORIZONTAL)
        hsizer.Add(self.duration_ctrl)
        hsizer.Add(minute_label, 0, wxLEFT, 8)
        grid_sizer.Add(hsizer)
        find_btn = wxButton(self, -1, _("&Find"))
        find_btn.SetDefault()
        EVT_BUTTON(self, find_btn.GetId(), self.OnFind)
        sizer1c.Add(grid_sizer)
        sizer1c.Add(wxPanel(panel1, -1), 1)
        sizer1c.Add(find_btn, 0, wxALIGN_RIGHT|wxTOP, 16)

        sizer1.Add(sizer1a, 1, wxEXPAND)
        sizer1.Add(sizer1b, 1, wxEXPAND|wxLEFT, 16)
        sizer1.Add(sizer1c, 0, wxEXPAND|wxLEFT, 16)
        panel1.SetSizer(sizer1)

        panel2 = wxPanel(splitter, -1)
        label2 = wxStaticText(panel2, -1, _("Results"))
        self.result_list = wxListCtrl(panel2, -1,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        self.result_list.InsertColumn(0, _("Resource"), width=280)
        self.result_list.InsertColumn(1, _("Available from"), width=140)
        self.result_list.InsertColumn(2, _("Available until"), width=140)
        sizer2 = wxBoxSizer(wxVERTICAL)
        sizer2.Add(label2)
        sizer2.Add(self.result_list, 1, wxEXPAND)
        panel2.SetSizer(sizer2)

        splitter.SetMinimumPaneSize(100)
        splitter.SplitHorizontally(panel1, panel2, 200)
        main_sizer.Add(splitter, 1, wxEXPAND|wxLEFT|wxRIGHT|wxTOP, 8)

        button_bar = wxBoxSizer(wxHORIZONTAL)

        book_btn = wxButton(self, -1, _("Book Resource"))
        EVT_BUTTON(self, book_btn.GetId(), self.OnBook)
        button_bar.Add(book_btn, 0, 0, 0)

        button_bar.Add(wxPanel(self, -1), 1, wxEXPAND)

        close_btn = wxButton(self, wxID_CLOSE, _("Close"))
        EVT_BUTTON(self, wxID_CLOSE, self.OnClose)
        button_bar.Add(close_btn, 0, wxLEFT, 16)

        main_sizer.Add(button_bar, 0, wxEXPAND|wxALL, 16)

        self.SetSizer(main_sizer)
        self.SetSizeHints(minW=500, minH=300)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)
        self.ok = True

    def OnClose(self, event=None):
        """Close the absence window."""
        self.Close(True)

    def OnFind(self, event=None):
        """Find available resources."""
        try:
            ctrl = self.first_date_ctrl
            first = parse_date(ctrl.GetValue())
            ctrl = self.last_date_ctrl
            last = parse_date(ctrl.GetValue())
            ctrl = self.duration_ctrl
            duration = int(ctrl.GetValue())
        except ValueError:
            ctrl.SetFocus()
            wxBell()
            return
        hours = self.hour_list.GetSelections()
        resources = [self.resources[idx][1]
                     for idx in self.resource_list.GetSelections()]
        self.result_list.DeleteAllItems()
        self.results = []

        try:
            self.results = self.client.availabilitySearch(first=first,
                                last=last, duration=duration, hours=hours,
                                resources=resources)
        except SchoolToolError, e:
            wxMessageBox(_("Could not get the list of available resources: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
            return
        else:
            self.results.sort()

        for idx, slot in enumerate(self.results):
            self.result_list.InsertStringItem(idx, slot.resource_title)
            self.result_list.SetItemData(idx, idx)
            available_until = slot.available_from + slot.available_for
            start = slot.available_from.strftime('%Y-%m-%d %H:%M')
            end = available_until.strftime('%Y-%m-%d %H:%M')
            self.result_list.SetStringItem(idx, 1, start)
            self.result_list.SetStringItem(idx, 2, end)

    def OnBook(self, event=None):
        """Book a resource."""
        duration = self.duration_ctrl.GetValue()
        dlg = ResourceBookingDlg(self, self.client, self.resources, duration)
        if not dlg.ok:
            dlg.Destroy()
            return
        idx = self.result_list.GetFirstSelected()
        if idx != -1:
            key = self.result_list.GetItemData(idx)
            dlg.preselect(self.results[key])
        dlg.Show()


class ResourceBookingDlg(wxDialog):
    """Dialog for resource booking"""

    def __init__(self, parent, client, resources, duration="30"):
        title = _("Resource Booking")
        wxDialog.__init__(self, parent, -1, title, style=NONMODAL_DLG_STYLE)
        self.title = title
        self.client = client
        self.resources = resources
        self.ok = False
        try:
            self.persons = self.client.getListOfPersons()
        except SchoolToolError, e:
            wxMessageBox(_("Could not get a list of persons: %s") % e,
                         title, wxICON_ERROR|wxOK)
            return
        else:
            self.persons.sort()

        vsizer = wxBoxSizer(wxVERTICAL)
        grid_sizer = wxFlexGridSizer(cols=2, hgap=8, vgap=8)
        grid_sizer.Add(wxStaticText(self, -1, _("Resource")))
        self.resource_ctrl = wxComboBox(self, -1, "",
                                        style=wxCB_READONLY|wxCB_DROPDOWN,
                                        choices=[r[0] for r in resources])
        grid_sizer.Add(self.resource_ctrl, 1, wxEXPAND)
        grid_sizer.Add(wxStaticText(self, -1, _("Person")))
        self.person_ctrl = wxComboBox(self, -1, "",
                                      style=wxCB_READONLY|wxCB_DROPDOWN,
                                      choices=[p[0] for p in self.persons])
        grid_sizer.Add(self.person_ctrl, 1, wxEXPAND)
        grid_sizer.Add(wxStaticText(self, -1, _("Date")))
        self.date_ctrl = DateCtrl(self, -1)
        today = datetime.date.today().strftime('%Y-%m-%d')
        self.date_ctrl.SetValue(today)
        self.date_ctrl.SetSize(self.person_ctrl.GetSize())
        grid_sizer.Add(self.date_ctrl)
        grid_sizer.Add(wxStaticText(self, -1, _("Time")))
        now = datetime.datetime.now().strftime('%H:%M')
        self.time_ctrl = wxTextCtrl(self, -1, now)
        grid_sizer.Add(self.time_ctrl)
        grid_sizer.Add(wxStaticText(self, -1, _("Duration")))
        hsizer = wxBoxSizer(wxHORIZONTAL)
        self.duration_ctrl = wxTextCtrl(self, -1, str(duration))
        hsizer.Add(self.duration_ctrl)
        hsizer.Add(wxStaticText(self, -1, _("min")), 0, wxLEFT, 8)
        grid_sizer.Add(hsizer)
        vsizer.Add(grid_sizer, 0, wxEXPAND|wxALL, 8)
        self.ignore_ctrl = wxCheckBox(self, -1, _("Ignore conflicts"))
        vsizer.Add(self.ignore_ctrl, 0, wxEXPAND|wxLEFT|wxRIGHT|wxBOTTOM, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_CENTER|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)
        self.ok = True

    def preselect(self, slot):
        for idx, (title, path) in enumerate(self.resources):
            if path == slot.resource_path:
                self.resource_ctrl.SetSelection(idx)
                break
        self.date_ctrl.SetValue(slot.available_from.strftime('%Y-%m-%d'))
        self.time_ctrl.SetValue(slot.available_from.strftime('%H:%M'))

    def OnOk(self, event=None):
        idx = self.resource_ctrl.GetSelection()
        if idx == -1:
            self.resource_ctrl.SetFocus()
            wxBell()
            return
        resource_path = self.resources[idx][1]
        idx = self.person_ctrl.GetSelection()
        if idx == -1:
            self.person_ctrl.SetFocus()
            wxBell()
            return
        person_path = self.persons[idx][1]
        try:
            ctrl = self.date_ctrl
            date = parse_date(ctrl.GetValue())
            ctrl = self.time_ctrl
            time = parse_time(ctrl.GetValue())
            ctrl = self.duration_ctrl
            duration = int(ctrl.GetValue())
        except ValueError:
            ctrl.SetFocus()
            wxBell()
            return
        else:
            when = datetime.datetime.combine(date, time)
        ignore_conflicts = self.ignore_ctrl.IsChecked()
        try:
            self.client.bookResource(resource_path, person_path, when,
                                     duration, ignore_conflicts)
        except SchoolToolError, e:
            wxMessageBox(_("Could not book the resource: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
        else:
            self.Close(True)


class PasswordDlg(wxDialog):
    """Dialog for changing passwords booking"""

    def __init__(self, parent, client, person):
        self.title = _("Change Password for %s") % person.person_title
        self.username = person.person_path.split('/')[-1]
        self.client = client
        wxDialog.__init__(self, parent, -1, self.title,
                          style=NONMODAL_DLG_STYLE)

        vsizer = wxBoxSizer(wxVERTICAL)
        vsizer.Add(wxStaticText(self, -1, person.person_title),
                   0, wxLEFT|wxTOP|wxRIGHT, 8)
        vsizer.Add(wxStaticText(self, -1, _("Username: %s") % self.username),
                   0, wxLEFT|wxTOP|wxRIGHT, 8)

        grid_sizer = wxFlexGridSizer(cols=2, hgap=8, vgap=8)
        grid_sizer.Add(wxStaticText(self, -1, _("New password")))
        self.new_pw_ctrl = wxTextCtrl(self, -1, "", style=wxTE_PASSWORD)
        grid_sizer.Add(self.new_pw_ctrl, 1, wxEXPAND)
        grid_sizer.Add(wxStaticText(self, -1, _("Confirm password")))
        self.confirm_pw_ctrl = wxTextCtrl(self, -1, "", style=wxTE_PASSWORD)
        grid_sizer.Add(self.confirm_pw_ctrl, 1, wxEXPAND)
        vsizer.Add(grid_sizer, 0, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_CENTER|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

    def OnOk(self, event=None):
        if self.new_pw_ctrl.GetValue() != self.confirm_pw_ctrl.GetValue():
            wxMessageBox(_("Passwords do not match"), self.title,
                         wxICON_ERROR|wxOK)
            return
        try:
            self.client.changePassword(self.username,
                                       self.new_pw_ctrl.GetValue())
        except SchoolToolError, e:
            wxMessageBox(_("Could not change password: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
        else:
            self.Close(True)


class PersonInfoDlg(wxDialog):
    """Person info dialog."""

    def __init__(self, parent, client, person):
        self.title = person.person_title
        self.person_path = person.person_path
        self.client = client
        self.mainframe = parent
        self.ok = False

        try:
            person_info = client.getPersonInfo(person.person_path)
        except SchoolToolError, e:
            wxMessageBox(_("Could not get person information: %s") % e,
                         self.title, wxICON_ERROR|wxOK)
            return

        try:
            photo = self.client.getPersonPhoto(self.person_path)
        except SchoolToolError, e:
            wxMessageBox(_("Could not get person photo: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
            return

        wxDialog.__init__(self, parent, -1, self.title,
                          style=NONMODAL_DLG_STYLE)

        vsizer = wxBoxSizer(wxVERTICAL)

        hsizer = wxBoxSizer(wxHORIZONTAL)

        grid_sizer = wxFlexGridSizer(cols=2, hgap=8, vgap=8)
        grid_sizer.AddGrowableCol(1)

        self.first_name_ctrl = wxTextCtrl(self, -1, person_info.first_name)
        grid_sizer.Add(wxStaticText(self, -1, _("First Name")), 0,
                       wxALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.first_name_ctrl, 1, wxEXPAND)

        self.last_name_ctrl = wxTextCtrl(self, -1, person_info.last_name)
        grid_sizer.Add(wxStaticText(self, -1, _("Last Name")), 0,
                       wxALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.last_name_ctrl, 1, wxEXPAND)

        self.date_of_birth_ctrl = DateCtrl(self, -1)
        if person_info.date_of_birth is not None:
            date_of_birth = person_info.date_of_birth.strftime('%Y-%m-%d')
            self.date_of_birth_ctrl.SetValue(date_of_birth)
        self.date_of_birth_ctrl.SetSize(self.last_name_ctrl.GetSize())
        grid_sizer.Add(wxStaticText(self, -1, _("Date of Birth")), 0,
                       wxALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.date_of_birth_ctrl, 1, wxEXPAND)

        self.comments_ctrl = wxTextCtrl(self, -1, person_info.comment,
                                        style=wxTE_MULTILINE,
                                        size=wxSize(200, 100))
        grid_sizer.Add(wxStaticText(self, -1, _("Comments")), 0,
                       wxALIGN_TOP)
        grid_sizer.Add(self.comments_ctrl, 1, wxEXPAND)

        hsizer.Add(grid_sizer, 0, wxEXPAND)

        if photo is None:
            filename = os.path.join(os.path.dirname(__file__), 'nophoto.png')
            photo = wxBitmap(filename, wxBITMAP_TYPE_PNG)
        else:
            photo = wxBitmapFromImage(wxImageFromStream(StringIO(photo)))
        self.photo_ctrl = wxBitmapButton(self, -1, photo,
                                         size=wxSize(250, 250))
        EVT_BUTTON(self, self.photo_ctrl.GetId(), self.OnPhoto)
        hsizer.Add(self.photo_ctrl, 0, wxLEFT, 8)

        vsizer.Add(hsizer, 0, wxEXPAND|wxALL, 8)

        vsizer.Add(wxStaticLine(self, -1), 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, _("OK"))
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        cancel_btn = wxButton(self, wxID_CANCEL, _("Cancel"))
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_CENTER|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()
        self.CenterOnScreen(wx.wxBOTH)

        self.ok = True

    def OnOk(self, event=None):
        person_info = PersonInfo(self.first_name_ctrl.GetValue(),
                                 self.last_name_ctrl.GetValue(),
                                 self.date_of_birth_ctrl.GetValue(),
                                 self.comments_ctrl.GetValue())
        try:
            self.client.savePersonInfo(self.person_path, person_info)
        except SchoolToolError, e:
            wxMessageBox(_("Could not update person information: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
        else:
            self.Close(True)
            self.mainframe.DoRefresh()

    def OnPhoto(self, event=None):
        global previous_photo_dir
        filename = wxFileSelector(_("Choose a new photo"), wildcard="*.jpg",
                                  default_path=previous_photo_dir,
                                  flags=wxOPEN|wxFILE_MUST_EXIST)
        if not filename:
            return
        previous_photo_dir = os.path.dirname(filename)
        try:
            photo = file(filename, 'rb').read()
        except IOError, e:
            wxMessageBox(_("Could not read %s") % filename, self.title,
                         wxICON_ERROR|wxOK)
            return
        try:
            self.client.savePersonPhoto(self.person_path, photo)
        except SchoolToolError, e:
            wxMessageBox(_("Could not update person photo: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
            return
        try:
            photo = self.client.getPersonPhoto(self.person_path)
        except SchoolToolError, e:
            wxMessageBox(_("Could not get person photo: %s")
                         % e, self.title, wxICON_ERROR|wxOK)
            return
        else:
            photo = wxBitmapFromImage(wxImageFromStream(StringIO(photo)))
            self.photo_ctrl.SetBitmapLabel(photo)
            self.photo_ctrl.SetBitmapSelected(photo)
            self.photo_ctrl.SetBitmapFocus(photo)
            self.photo_ctrl.SetBitmapDisabled(photo)
            self.Layout()

previous_photo_dir = ""


#
# Main application window
#

class MainFrame(wxFrame):
    """Main frame.

    The following attributes are defined:
      client                The SchoolToolClient instance that encapsulates
                            communication with the server.

      refresh_lock          A Lock to protect against reentrancy of _refresh.

      groupTreeCtrl         Group tree control.  The PyData object of every
                            tree item is a tuple (group_path, id) where
                            id is a unique identifier of this tree item that
                            is invariant to tree changes.  The id of an item is
                            actually a tuple of group_paths of itself and all
                            its parents.
      treePopupMenu         Popup menu for the group tree.

      personListCtrl        Person (member) list control.  The item data of
                            every item is an integer index to personListData.
      personListData        A list of MemberInfo objects.
      personPopupMenu       Popup menu for the person list control.

      relationshipListCtrl  Relationship tree control.  The item data of every
                            item is an integer index to relationshipListData.
      relationshipListData  A list of RelationshipInfo objects.
    """

    def __init__(self, client, parent=None, id=-1, title="SchoolTool"):
        """Create the main application window."""
        wxFrame.__init__(self, parent, id, title, size=wxSize(500, 400))
        self.client = client
        self.refresh_lock = threading.Lock()
        self.personListData = []
        self.relationshipListData = []

        filename = os.path.join(os.path.dirname(__file__), 'schooltool.xpm')
        icon = wxIcon(filename, wxBITMAP_TYPE_XPM)
        self.SetIcon(icon)

        self.CreateStatusBar()

        self.SetMenuBar(menubar(
            menu(_("&File"),
                 item(_("New &Person"), _("Create a new person"),
                      self.DoNewPerson),
                 item(_("New &Group"), _("Create a new group"),
                      self.DoNewGroup),
                 separator(),
                 item(_("E&xit\tCtrl+Q"), _("Terminate the program"),
                      self.DoExit),
                ),
            menu(_("&View"),
                 item(_("All &Absences"), _("List all absences in the system"),
                      self.DoViewAllAbsences),
                 item(_("&School Timetable"),
                      _("Edit a timetable for the whole school"),
                      self.DoViewSchoolTimetable),
                 item(_("Search &for Available Resources"),
                      _("Search for available resources"),
                      self.DoAvailabilitySearch),
                 separator(),
                 item(_("&Refresh\tCtrl+R"), _("Refresh data from the server"),
                      self.DoRefresh),
                 ),
            menu(_("&Settings"),
                 item(_("&Server"), _("Server settings"),
                      self.DoServerSettings),
                 ),
            menu(_("&Help"),
                 item(_("&About"), _("About SchoolTool"), self.DoAbout),
                 ),
            ))

        # client area: vertical splitter
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)

        # left pane of the splitter: group tree control
        ID_GROUP_TREE = wxNewId()
        self.groupTreeCtrl = wxTreeCtrl(splitter, ID_GROUP_TREE,
                style=wxTR_HAS_BUTTONS|wxTR_HIDE_ROOT|wxSUNKEN_BORDER)
        EVT_TREE_SEL_CHANGED(self, ID_GROUP_TREE, self.DoSelectGroup)
        self.treePopupMenu = popupmenu(
                item(_("Roll &Call"), _("Do a roll call"), self.DoRollCall),
                item(_("&Absence Tracker"),
                     _("Inspect the absence tracker for this group"),
                     self.DoGroupAbsenceTracker),
                item(_("View &Timetables"),
                     _("View a list of groups's timetables"),
                     self.DoViewGroupTimetables),
                item(_("View C&omposite Timetables"),
                     _("View a list of group's composite timetables"),
                     self.DoViewGroupCompositeTimetables),
                separator(),
                item(_("&Refresh"), _("Refresh"), self.DoRefresh)
            )
        setupPopupMenu(self.groupTreeCtrl, self.treePopupMenu)

        # right pane of the splitter: horizontal splitter
        splitter2 = wxSplitterWindow(splitter, -1, style=wxSP_NOBORDER)

        # top pane of the second splitter: member list
        panel2a = wxPanel(splitter2, -1)
        label2a = wxStaticText(panel2a, -1, _("Members"))
        ID_PERSON_LIST = wxNewId()
        self.personListCtrl = wxListCtrl(panel2a, ID_PERSON_LIST,
                style=wxSUNKEN_BORDER|wxLC_LIST|wxLC_SINGLE_SEL)
        EVT_LIST_ITEM_ACTIVATED(self, ID_PERSON_LIST, self.DoViewPersonInfo)
        self.personPopupMenu = popupmenu(
                item(_("View Person &Info"),
                     _("View person's information"), self.DoViewPersonInfo),
                item(_("View &Absences"),
                     _("View a list of person's absences"),
                     self.DoViewPersonAbsences),
                item(_("View &Timetables"),
                     _("View a list of person's timetables"),
                     self.DoViewPersonTimetables),
                item(_("View &Composite Timetables"),
                     _("View a list of person's composite timetables"),
                     self.DoViewPersonCompositeTimetables),
                item(_("Change &Password"),
                     _("Change the password of a person"),
                     self.DoViewPersonChangePassword),
                separator(),
                item(_("Add &Member"), _("Add a person to this group"),
                     self.DoAddMember),
                item(_("&Remove Member"), _("Remove a person from this group"),
                     self.DoRemoveMember),
            )
        setupPopupMenu(self.personListCtrl, self.personPopupMenu)
        sizer2a = wxBoxSizer(wxVERTICAL)
        sizer2a.Add(label2a)
        sizer2a.Add(self.personListCtrl, 1, wxEXPAND)
        panel2a.SetSizer(sizer2a)

        # bottom pane of the second splitter: relationship list
        panel2b = wxPanel(splitter2, -1)
        label2b = wxStaticText(panel2b, -1, _("Relationships"))
        ID_RELATIONSHIP_LIST = wxNewId()
        self.relationshipListCtrl = wxListCtrl(panel2b, ID_RELATIONSHIP_LIST,
                style=wxSUNKEN_BORDER|wxLC_REPORT|wxLC_SINGLE_SEL)
        self.relationshipListCtrl.InsertColumn(0, _("Title"), width=110)
        self.relationshipListCtrl.InsertColumn(1, _("Role"), width=110)
        self.relationshipListCtrl.InsertColumn(2, _("Relationship"), width=110)
        self.relationshipPopupMenu = popupmenu(
            item(_("&Add Member"), _("Add a person to this group"),
                 self.DoAddMember),
            item(_("Add &Teacher"), _("Add a teacher to this group"),
                 self.DoAddTeacher),
            item(_("Add &Subgroup"), _("Add a group to this group"),
                 self.DoAddSubgroup),
            item(_("&Remove Relationship"), _("Remove selected relationship"),
                 self.DoRemoveRelationship),
            )
        setupPopupMenu(self.relationshipListCtrl, self.relationshipPopupMenu)
        sizer2b = wxBoxSizer(wxVERTICAL)
        sizer2b.Add(label2b)
        sizer2b.Add(self.relationshipListCtrl, 1, wxEXPAND)
        panel2b.SetSizer(sizer2b)

        # connect panes to the second splitter
        splitter2.SetMinimumPaneSize(50)
        splitter2.SplitHorizontally(panel2a, panel2b, 150)

        # connect panes to the first splitter
        splitter.SetMinimumPaneSize(20)
        splitter.SplitVertically(self.groupTreeCtrl, splitter2, 150)

        # finishing touches
        self.SetSizeHints(minW=100, minH=150)

    def DoNewPerson(self, event):
        """Create a new person.

        Accessible from File|New Person.
        """
        dlg = NewPersonDlg(self)
        if dlg.ShowModal()  == wxID_OK:
            self.DoRefresh()
        dlg.Destroy()

    def DoNewGroup(self, event):
        """Create a new group.

        Accessible from File|New Group.
        """
        title = wxGetTextFromUser(_("Title"), _("New Group"))
        if title == "":
            return
        try:
            self.client.createGroup(title)
        except SchoolToolError, e:
            wxMessageBox(_("Could not create a group: %s") % e,
                         _("New Group"), wxICON_ERROR|wxOK)
            return

    def DoAddMember(self, event):
        """Add a person from the current group.

        Accessible from person list popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        try:
            persons = self.client.getListOfPersons()
        except SchoolToolError, e:
            wxMessageBox(_("Could not get a list of persons: %s") % e,
                         _("Add Teacher"), wxICON_ERROR|wxOK)
            return
        persons.sort()

        # wxGetMultipleChoice is defined in wxWindows API documentation,
        # but wxPython 2.4.2.4 does NOT have it.
        choice = wxGetSingleChoiceIndex(
            _("Select a person to add to %s") % group_title,
            _("Add Member"), [p[0] for p in persons])
        if choice == -1:
            return

        person_path = persons[choice][1]
        try:
            self.client.createRelationship(group_path, person_path,
                                           URIMembership, URIGroup)
        except SchoolToolError, e:
            wxMessageBox(_("Could not add member: %s") % e,
                         _("Add Member"), wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoAddTeacher(self, event):
        """Add a teacher from the current group.

        Accessible from relationships list popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        try:
            teachers_group = self.client.getGroupInfo('/groups/teachers')
        except SchoolToolError, e:
            wxMessageBox(_("Could not get a list of teachers: %s") % e,
                         _("Add Teacher"), wxICON_ERROR|wxOK)
            return
        persons = teachers_group.members
        persons.sort()

        # wxGetMultipleChoice is defined in wxWindows API documentation,
        # but wxPython 2.4.2.4 does NOT have it.
        choice = wxGetSingleChoiceIndex(
                        _("Select a teacher to add to %s") % group_title,
                        _("Add Teacher"), [p.person_title for p in persons])
        if choice == -1:
            return

        person_path = persons[choice].person_path
        try:
            self.client.createRelationship(group_path, person_path,
                                           URITeaching, URITaught)
        except SchoolToolError, e:
            wxMessageBox(_("Could not add teacher: %s") % e,
                         _("Add Teacher"), wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoAddSubgroup(self, event):
        """Add a subgroup from the current group.

        Accessible from person list popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        try:
            groups = self.client.getListOfGroups()
        except SchoolToolError, e:
            wxMessageBox(_("Could not get a list of groups: %s") % e,
                         _("Add Subgroup"), wxICON_ERROR|wxOK)
            return
        groups.sort()

        # wxGetMultipleChoice is defined in wxWindows API documentation,
        # but wxPython 2.4.2.4 does NOT have it.
        choice = wxGetSingleChoiceIndex(
            _("Select a group to add to %s") % group_title,
            _("Add Subgroup"), [g[0] for g in groups])
        if choice == -1:
            return

        subgroup_path = groups[choice][1]
        try:
            self.client.createRelationship(group_path, subgroup_path,
                                           URIMembership, URIGroup)
        except SchoolToolError, e:
            wxMessageBox(_("Could not add subgroup: %s") % e,
                         _("Add Subgroup"), wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoRemoveMember(self, event):
        """Remove a person from the current group.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No person selected"))
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]

        for relationship in self.relationshipListData:
            if relationship.target_path == member.person_path:
                break
        else:
            # should not happen
            self.SetStatusText(
                _("Selected person is not a member of this group"))
            return

        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        if wxMessageBox(_("Really remove %s from %s?")
                        % (member.person_title, group_title),
                        _("Remove Person"), wxYES_NO) != wxYES:
            return

        try:
            self.client.deleteObject(relationship.link_path)
        except SchoolToolError, e:
            wxMessageBox(_("Could not remove member: %s") % e,
                         _("Remove Person"), wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoRemoveRelationship(self, event):
        """Remove a relationship.

        Accessible from relationship list popup menu.
        """
        item = self.relationshipListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No relationship selected"))
            return
        key = self.relationshipListCtrl.GetItemData(item)
        relationship = self.relationshipListData[key]

        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        if wxMessageBox(_("Really remove %s (%s) from %s?")
                        % (relationship.target_title, relationship.role,
                           group_title),
                        _("Remove Relationship"), wxYES_NO) != wxYES:
            return

        try:
            self.client.deleteObject(relationship.link_path)
        except SchoolToolError, e:
            wxMessageBox(_("Could not remove relationship: %s") % e,
                         _("Remove Relationship"), wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoExit(self, event):
        """Exit the application.

        Accessible via Ctrl+Q and from File|Exit.
        """
        self.Close(True)

    def DoServerSettings(self, event=None):
        """Show the Server Settings dialog.

        Accessible from Settings|Server settings.
        """
        dlg = ServerSettingsDlg(self)
        dlg.setServer(self.client.server)
        dlg.setPort(self.client.port)
        if dlg.ShowModal() == wxID_OK:
            self.client.setServer(dlg.getServer(), dlg.getPort())
            self.client.setUser(dlg.getUser(), dlg.getPassword())
            self.DoRefresh()
        dlg.Destroy()

    def DoAbout(self, event):
        """Show the About dialog.

        Accessible from Help|About.
        """
        dlg = wxMessageDialog(self, about_text, _("About SchoolTool"), wxOK)
        dlg.ShowModal()
        dlg.Destroy()

    def DoSelectGroup(self, event):
        """Update member and relationship lists for the selected group.

        Called when the group tree control selection is changed and in
        some other cases (e.g. from DoRefresh).
        """

        # Clear lists and see if a group is selected
        self.personListData = []
        self.personListCtrl.Freeze()
        self.personListCtrl.DeleteAllItems()
        self.relationshipListData = []
        self.relationshipListCtrl.Freeze()
        self.relationshipListCtrl.DeleteAllItems()
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.personListCtrl.Thaw()
            self.relationshipListCtrl.Thaw()
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]

        # Fill in group member list
        try:
            info = self.client.getGroupInfo(group_path)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            self.personListCtrl.Thaw()
            self.relationshipListCtrl.Thaw()
            return
        self.SetStatusText(self.client.status)
        self.personListData = info.members
        self.personListData.sort()
        for idx, item in enumerate(self.personListData):
            self.personListCtrl.InsertStringItem(idx, item.person_title)
            self.personListCtrl.SetItemData(idx, idx)
        self.personListCtrl.Thaw()

        # Fill in group relationship list
        try:
            self.relationshipListData = self.client.getObjectRelationships(
                                                                    group_path)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            self.relationshipListCtrl.Thaw()
            return
        self.SetStatusText(self.client.status)
        self.relationshipListData.sort()
        for idx, item in enumerate(self.relationshipListData):
            self.relationshipListCtrl.InsertStringItem(idx, item.target_title)
            self.relationshipListCtrl.SetItemData(idx, idx)
            self.relationshipListCtrl.SetStringItem(idx, 1, nameURI(item.role))
            self.relationshipListCtrl.SetStringItem(idx, 2,
                                                    nameURI(item.arcrole))
        self.relationshipListCtrl.Thaw()

    def DoRefresh(self, event=None):
        """Refresh data from the server.

        Accessible via Ctrl+R, from View|Refresh and from the group tree
        popup menu.
        """

        # If the user holds down Ctrl+R, wxWindows tends to call DoRefresh
        # before the previous call finishes, thus causing reentrancy problems
        if not self.refresh_lock.acquire(False):
            return
        try:
            self._refresh()
        finally:
            self.refresh_lock.release()

    def _refresh(self):
        # Get the tree from the server
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
            old_selection = self.groupTreeCtrl.GetPyData(item)[1]

        # Remember which items were expanded
        expanded = sets.Set()
        root = self.groupTreeCtrl.GetRootItem()
        if root.IsOk(): # do not do this before the root item is first created
            stack = [root]
            while stack:
                item = stack.pop()
                if item is not root and self.groupTreeCtrl.IsExpanded(item):
                    expanded.add(self.groupTreeCtrl.GetPyData(item)[1])
                next, cookie = self.groupTreeCtrl.GetFirstChild(item, 0)
                while next.IsOk():
                    stack.append(next)
                    next, cookie = self.groupTreeCtrl.GetNextChild(item,
                                                                   cookie)

        # Reload tree
        self.groupTreeCtrl.Freeze()
        self.groupTreeCtrl.DeleteAllItems()
        root = self.groupTreeCtrl.AddRoot(_("Roots"))

        stack = [(root, None)]  # (item, id)
        item_to_select = None
        for level, title, path in group_tree:
            while len(stack) > level + 1:
                last = stack.pop()[0]
                self.groupTreeCtrl.SortChildren(last)
            assert len(stack) == level+1
            item = self.groupTreeCtrl.AppendItem(stack[-1][0], title)
            if level == 1 or stack[-1][1] in expanded:
                self.groupTreeCtrl.Expand(stack[-1][0])
            id = tuple([parent[1] for parent in stack[1:]] + [path])
            self.groupTreeCtrl.SetPyData(item, (path, id))
            if id == old_selection:
                item_to_select = item
            stack.append((item, id))
        while stack:
            last = stack.pop()[0]
            self.groupTreeCtrl.SortChildren(last)

        if item_to_select is None:
            self.groupTreeCtrl.Unselect()
            self.DoSelectGroup(None)
        else:
            self.groupTreeCtrl.SelectItem(item_to_select)
            self.groupTreeCtrl.EnsureVisible(item_to_select)
        self.groupTreeCtrl.Thaw()

    def DoRollCall(self, event=None):
        """Open the roll call dialog.

        Accessible from group tree popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)
        try:
            rollcall = self.client.getRollCall(group_path)
        except SchoolToolError, e:
            self.SetStatusText(str(e))
            return
        rollcall.sort()
        dlg = RollCallDlg(self, group_title, group_path, rollcall, self.client)
        if dlg.ShowModal() == wxID_OK:
            self.SetStatusText(self.client.status)
        dlg.Destroy()

    def DoViewPersonInfo(self, event=None):
        """Open the person info dialog.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No person selected"))
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]
        dlg = PersonInfoDlg(parent=self, client=self.client, person=member)
        if dlg.ok:
            dlg.Show()

    def DoViewPersonAbsences(self, event=None):
        """Open the absences window for the currently selected person.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No person selected"))
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]
        window = AbsenceFrame(self.client, "%s/absences" % member.person_path,
                              parent=self, persons=False,
                              title=_("%s's absences") % member.person_title)
        window.Show()

    def DoViewPersonTimetables(self, event=None):
        """Open the timetables window for the currently selected person.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No person selected"))
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]
        window = BrowserFrame("%s's timetables" % member.person_title,
                              "http://%s:%s%s/timetables"
                                  % (self.client.server, self.client.port,
                                     member.person_path),
                              parent=self)
        window.Show()

    def DoViewPersonCompositeTimetables(self, event=None):
        """Open the composite timetables window for the currently selected
        person.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No person selected"))
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]
        window = BrowserFrame(_("%s's composite timetables")
                                  % member.person_title,
                              "http://%s:%s%s/composite-timetables"
                                  % (self.client.server, self.client.port,
                                     member.person_path),
                              parent=self)
        window.Show()

    def DoViewPersonChangePassword(self, event=None):
        """Open the password change dialog.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText(_("No person selected"))
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]
        window = PasswordDlg(parent=self, client=self.client, person=member)
        window.Show()

    def DoViewAllAbsences(self, event=None):
        """Open the absences window for the whole system person.

        Accessible via View|All Absences.
        """
        window = AbsenceFrame(self.client, "/utils/absences", parent=self,
                              title=_("All absences"), detailed=False)
        window.Show()

    def DoGroupAbsenceTracker(self, event=None):
        """Open the absences window for the currently selected group.

        Accessible from group popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)
        path = "%s/facets/absences" % group_path
        title = _("Absences of %s") % group_title
        try:
            try:
                absence_data = self.client.getAbsences(path)
            except ResponseStatusError, e:
                if e.status != 404:
                    raise
                if wxMessageBox(_("Do you want to create a new absence"
                                  " tracker facet and put it on %s?")
                                % group_title, title, wxYES_NO) != wxYES:
                    return
                try:
                    self.client.createFacet(group_path, 'absence_tracker')
                except SchoolToolError, e:
                    wxMessageBox(_("Could not create an absence tracker: %s") %
                                 e,
                                 title, wxICON_ERROR|wxOK)
                    return
                else:
                    absence_data = self.client.getAbsences(path)
        except SchoolToolError, e:
            wxMessageBox(_("Could not get the list of absences: %s") % e,
                         title, wxICON_ERROR|wxOK)
            return
        window = AbsenceFrame(parent=self, title=title, detailed=False,
                              client=self.client, path=path,
                              absence_data=absence_data)
        window.Show()

    def DoViewGroupTimetables(self, event=None):
        """Open the timetables window for the currently selected group.

        Accessible from group tree popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)
        window = BrowserFrame(_("%s's timetables") % group_title,
                              "http://%s:%s%s/timetables"
                                  % (self.client.server, self.client.port,
                                     group_path),
                              parent=self)
        window.Show()

    def DoViewGroupCompositeTimetables(self, event=None):
        """Open the composite timetables window for the currently selected
        group.

        Accessible from group list popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.SetStatusText(_("No group selected"))
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)
        window = BrowserFrame(_("%s's timetables") % group_title,
                              "http://%s:%s%s/composite-timetables"
                                  % (self.client.server, self.client.port,
                                     group_path),
                              parent=self)
        window.Show()

    def DoViewSchoolTimetable(self, event=None):
        """Open a school timetable window for a selected timetable.

        Accessible from View|School Timetable
        """
        try:
            periods = self.client.getTimePeriods()
        except SchoolToolError, e:
            wxMessageBox(_("Could not get the list of time periods: %s") % e,
                         _("School Timetable"), wxICON_ERROR|wxOK)
            return
        else:
            periods.sort()
        try:
            schemas = self.client.getTimetableSchemas()
        except SchoolToolError, e:
            wxMessageBox(
                _("Could not get the list of timetable schemas: %s") % e,
                _("School Timetable"), wxICON_ERROR|wxOK)
            return
        else:
            schemas.sort()
        choices = [(p, s) for p in periods for s in schemas]
        choice = wxGetSingleChoiceIndex(
                        _("Select a timetable to edit"),
                        _("School Timetable"), ["%s, %s" % c for c in choices])
        if choice == -1:
            return
        key = choices[choice]
        try:
            tt = self.client.getSchoolTimetable(*key)
        except SchoolToolError, e:
            wxMessageBox(_("Could not get the school timetable: %s") % e,
                         _("School Timetable"), wxICON_ERROR|wxOK)
            return

        try:
            resources = self.client.getListOfResources()
        except SchoolToolError, e:
            wxMessageBox(_("Could not get the list of resources: %s") % e,
                         _("School Timetable"), wxICON_ERROR|wxOK)
            return

        window = SchoolTimetableFrame(self.client, key, tt, resources,
                                      parent=self)
        window.Show()

    def DoAvailabilitySearch(self, event=None):
        """Open the resource availability search window.

        Accessible via View|Search for Available Resources
        """
        window = AvailabilitySearchFrame(self.client, parent=self)
        if window.ok:
            window.Show()
        else:
            window.Destroy()


class SchoolToolApp(wxApp):
    """Main application."""

    def __init__(self, client):
        self.client = client
        wxApp.__init__(self, 0)
        # Passing 0 as the second argument to wxApp disables the capturing of
        # stderr and helps debugging on Win32 (especially when an exception
        # occurs before the main loop is entered)

    def OnInit(self):
        """Initialize the application (create the main window)."""
        self.frame = MainFrame(self.client)
        self.frame.Show(True)
        self.SetTopWindow(self.frame)
        self.frame.DoServerSettings()
        return True


def main():
    import schooltool.uris
    schooltool.uris.setUp()
    # Do not output XML parsing errors to the terminal
    libxml2.registerErrorHandler(lambda ctx, error: None, None)
    wxInitAllImageHandlers()
    client = SchoolToolClient()
    app = SchoolToolApp(client)
    app.MainLoop()


if __name__ == '__main__':
    main()
