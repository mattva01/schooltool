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
import libxml2
import threading
from wxPython.wx import *
from wxPython.grid import *
from wxPython.lib.scrolledpanel import wxScrolledPanel
from schooltool.guiclient import SchoolToolClient, Unchanged, RollCallEntry
from schooltool.guiclient import SchoolToolError, ResponseStatusError
from schooltool.uris import URIMembership, URIGroup
from schooltool.uris import URITeaching, URITaught

__metaclass__ = type


class ServerSettingsDlg(wxDialog):
    """Server Settings dialog."""

    def __init__(self, *args, **kwds):
        if len(args) < 1: kwds.setdefault('parent', None)
        if len(args) < 2: kwds.setdefault('id', -1)
        if len(args) < 3: kwds.setdefault('title', 'Server Settings')

        # begin wxGlade: ServerSettingsDlg.__init__
        kwds["style"] = wxDIALOG_MODAL|wxCAPTION|wxSYSTEM_MENU
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


class RollCallInfoDlg(wxDialog):
    """More info popup of the roll call dialog"""

    def __init__(self, parent, title, show_resolved):
        wxDialog.__init__(self, parent, -1, title,
                          style=wxDIALOG_MODAL|wxCAPTION|wxSYSTEM_MENU)
        self.show_resolved = show_resolved
        self.CenterOnScreen(wx.wxBOTH)

        vsizer = wxBoxSizer(wxVERTICAL)
        hsizer = wxBoxSizer(wxHORIZONTAL)

        self.text_ctrl = wxTextCtrl(self, -1, style=wxTE_MULTILINE,
                                    size=wxSize(300, 100))
        hsizer.Add(self.text_ctrl, 1, wxEXPAND)

        radio_sizer = wxBoxSizer(wxVERTICAL)
        self.undecided_btn = wxRadioButton(self, -1, "Unset", style=wxRB_GROUP)
        self.undecided_btn.Hide()

        self.resolve_btn = wxRadioButton(self, -1, "Resolve")
        if not show_resolved:
            self.resolve_btn.Hide()
        radio_sizer.Add(self.resolve_btn)

        self.dont_resolve_btn = wxRadioButton(self, -1, "Do not resolve")
        if not show_resolved:
            self.dont_resolve_btn.Hide()
        radio_sizer.Add(self.dont_resolve_btn)

        if show_resolved:
            hsizer.Add(radio_sizer, 0, wxLEFT, 4)

        vsizer.Add(hsizer, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, "OK")
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        cancel_btn = wxButton(self, wxID_CANCEL, "Cancel")
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()

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
        title = "Roll Call for %s" % group_title
        wxDialog.__init__(self, parent, -1, title,
            style=wxDIALOG_MODAL|wxCAPTION|wxSYSTEM_MENU|wxRESIZE_BORDER|
                  wxTHICK_FRAME)
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
                presence = "reported absent"
            grid.Add(wxStaticText(scrolled_panel, -1, presence),
                     0, wxALIGN_CENTER_VERTICAL|wxRIGHT, 4)

            unknown_btn = wxRadioButton(scrolled_panel, -1, "Unset",
                                        style=wxRB_GROUP)
            unknown_btn.Hide()

            present_btn = wxRadioButton(scrolled_panel, -1, "Present")
            self.entries_by_id[present_btn.GetId()] = entry
            EVT_RADIOBUTTON(self, present_btn.GetId(), self.OnPresentSelected)
            grid.Add(present_btn)

            absent_btn = wxRadioButton(scrolled_panel, -1, "Absent")
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
        ok_btn = wxButton(self, wxID_OK, "OK")
        cancel_btn = wxButton(self, wxID_CANCEL, "Cancel")
        ok_btn.SetDefault()
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()

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
            wxMessageBox("Could not submit the roll call: %s" % e,
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
              style=wxCAPTION|wxSYSTEM_MENU|wxRESIZE_BORDER|wxTHICK_FRAME)
        self.client = client
        self.title = title
        self.path = path
        self.absence_data = []
        self.persons = persons
        self.detailed = detailed

        main_sizer = wxBoxSizer(wxVERTICAL)
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)

        panel1 = wxPanel(splitter, -1)
        label1 = wxStaticText(panel1, -1, "Absences")
        ID_ABSENCE_LIST = wxNewId()
        self.absence_list = wxListCtrl(panel1, ID_ABSENCE_LIST,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        if self.detailed:
            self.absence_list.InsertColumn(0, "Date", width=140)
            self.absence_list.InsertColumn(1, "Ended?", width=80)
            self.absence_list.InsertColumn(2, "Resolved?", width=80)
            self.absence_list.InsertColumn(3, "Expected Presence", width=150)
            self.absence_list.InsertColumn(4, "Last Comment", width=200)
            if self.persons:
                self.absence_list.InsertColumn(1, "Person", width=110)
        else:
            self.absence_list.InsertColumn(0, "Absence", width=580)
        EVT_LIST_ITEM_SELECTED(self, ID_ABSENCE_LIST, self.DoSelectAbsence)
        sizer1 = wxBoxSizer(wxVERTICAL)
        sizer1.Add(label1)
        sizer1.Add(self.absence_list, 1, wxEXPAND)
        panel1.SetSizer(sizer1)

        panel2 = wxPanel(splitter, -1)
        label2 = wxStaticText(panel2, -1, "Comments")
        self.comment_list = wxListCtrl(panel2, -1,
                style=wxLC_REPORT|wxSUNKEN_BORDER|wxLC_SINGLE_SEL)
        self.comment_list.InsertColumn(0, "Date", width=140)
        self.comment_list.InsertColumn(1, "Reporter", width=110)
        self.comment_list.InsertColumn(2, "Absent From", width=110)
        self.comment_list.InsertColumn(3, "Ended?", width=80)
        self.comment_list.InsertColumn(4, "Resolved?", width=80)
        self.comment_list.InsertColumn(5, "Expected Presence", width=150)
        self.comment_list.InsertColumn(6, "Comment", width=200)
        sizer2 = wxBoxSizer(wxVERTICAL)
        sizer2.Add(label2)
        sizer2.Add(self.comment_list, 1, wxEXPAND)
        panel2.SetSizer(sizer2)

        splitter.SetMinimumPaneSize(50)
        splitter.SplitHorizontally(panel1, panel2, 200)
        main_sizer.Add(splitter, 1, wxEXPAND|wxLEFT|wxRIGHT|wxTOP, 8)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        close_btn = wxButton(self, wxID_CLOSE, "Close")
        EVT_BUTTON(self, wxID_CLOSE, self.OnClose)
        close_btn.SetDefault()
        button_bar.Add(close_btn)
        main_sizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(main_sizer)
        self.SetSizeHints(minW=200, minH=200)
        self.Layout()

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
                wxMessageBox("Could not get the list of absences: %s" % e,
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
                        absence.ended and "Yes" or "No")
                self.absence_list.SetStringItem(idx, n+2,
                        absence.resolved and "Yes" or "No")
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
                        comment.ended and "Yes" or "No")
            if comment.resolved is not Unchanged:
                self.comment_list.SetStringItem(idx, 4,
                        comment.resolved and "Yes" or "No")
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
        return "\n".join([title for title, path in self.tt.tt[row][col]])

    def SetValue(self, row, col, value):
        pass


class ActivitySelectionDlg(wxDialog):
    """Activity selection popup of the school timetable grid"""

    def __init__(self, parent, teacher_title, period_key, choices):
        title = "%s, %s, %s" % (teacher_title, period_key[0], period_key[1])
        wxDialog.__init__(self, parent, -1, title,
                          style=wxDIALOG_MODAL|wxCAPTION|wxSYSTEM_MENU)
        self.CenterOnScreen(wx.wxBOTH)

        self.choices = list(choices)
        self.choices.sort()

        vsizer = wxBoxSizer(wxVERTICAL)
        # wxLB_EXTENDED would be nicer, but then SetSelection stops working
        # for completely obscure reasons
        self.listbox = wxListBox(self, -1, style=wxLB_MULTIPLE,
                            choices=[title for title, value in self.choices])
        vsizer.Add(self.listbox, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        vsizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        ok_btn = wxButton(self, wxID_OK, "OK")
        cancel_btn = wxButton(self, wxID_CANCEL, "Cancel")
        ok_btn.SetDefault()
        button_bar.Add(ok_btn, 0, wxRIGHT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        vsizer.Add(button_bar, 0, wxALIGN_RIGHT|wxALL, 16)

        self.SetSizer(vsizer)
        vsizer.SetSizeHints(self)
        self.Layout()

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


class SchoolTimetableGrid(wxGrid):

    def __init__(self, parent, tt):
        wxGrid.__init__(self, parent, -1)
        self.tt = tt
        self.SetTable(SchoolTimetableGridTable(tt), True)
        # There is no way to auto-size row labels.
        self.SetRowLabelSize(150)

        EVT_GRID_EDITOR_SHOWN(self, self.OnEditorShown)
        EVT_GRID_CELL_LEFT_DCLICK(self, self.OnLeftDClick)

    def OnLeftDClick(self, event):
        if self.CanEnableCellControl():
            self.EnableCellEditControl()

    def OnEditorShown(self, event):
        row = event.GetRow()
        col = event.GetCol()
        event.Veto()

        teacher_path, teacher_title, choices = self.tt.teachers[row]
        dlg = ActivitySelectionDlg(self, teacher_title, self.tt.periods[col],
                                   choices)
        dlg.setSelection(self.tt.tt[row][col])
        if dlg.ShowModal() == wxID_OK:
            self.tt.tt[row][col] = dlg.getSelection()
            msg = wxGridTableMessage(self.GetTable(),
                                     wxGRIDTABLE_REQUEST_VIEW_GET_VALUES)
            self.ProcessTableMessage(msg)
        dlg.Destroy()


class SchoolTimetableFrame(wxDialog):
    """Window showing a timetable for the whole school."""

    def __init__(self, client, key, tt, parent=None, id=-1):
        title = "School Timetable (%s, %s)" % key
        wxDialog.__init__(self, parent, id, title, size=wxSize(600, 400),
              style=wxCAPTION|wxSYSTEM_MENU|wxRESIZE_BORDER|wxTHICK_FRAME)
        self.title = title
        self.client = client
        self.key = key
        self.tt = tt

        main_sizer = wxBoxSizer(wxVERTICAL)
        self.grid = grid = SchoolTimetableGrid(self, tt)
        main_sizer.Add(grid, 1, wxEXPAND|wxALL, 8)

        static_line = wxStaticLine(self, -1)
        main_sizer.Add(static_line, 0, wxEXPAND, 0)

        button_bar = wxBoxSizer(wxHORIZONTAL)
        resize_btn = wxButton(self, -1, "&Fit cells")
        ok_btn = wxButton(self, wxID_OK, "OK")
        cancel_btn = wxButton(self, wxID_CANCEL, "Cancel")
        ok_btn.SetDefault()
        EVT_BUTTON(self, wxID_OK, self.OnOk)
        EVT_BUTTON(self, resize_btn.GetId(), self.OnResize)
        button_bar.Add(resize_btn, 0, 0, 0)
        button_bar.Add(wxPanel(self, -1), 1, wxEXPAND)
        button_bar.Add(ok_btn, 0, wxRIGHT|wxLEFT, 16)
        button_bar.Add(cancel_btn, 0, 0, 0)
        main_sizer.Add(button_bar, 0, wxEXPAND|wxALL, 16)

        self.SetSizer(main_sizer)
        min_size = main_sizer.GetMinSize()
        self.SetSizeHints(minW=max(200, min_size.width),
                          minH=max(200, min_size.height))
        self.Layout()

    def OnClose(self, event=None):
        """Close the window."""
        self.Close(True)

    def OnOk(self, event=None):
        """Save the edited timetable to the server."""
        try:
            period, schema = self.key
            self.client.putSchooltoolTimetable(period, schema, self.tt)
        except SchoolToolError, e:
            wxMessageBox("Could not submit the roll call: %s" % e,
                         self.title, wxICON_ERROR|wxOK)
        else:
            self.Close(True)

    def OnResize(self, event=None):
        """Auto-size the grid"""
        self.grid.AutoSizeRows()
        self.grid.AutoSizeColumns()


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

        self.CreateStatusBar()

        # Menu bar

        def menubar(*items):
            menubar = wxMenuBar()
            for menu, title in items:
                menubar.Append(menu, title)
            return menubar

        def popupmenu(*items):
            menu = wxMenu()
            for item in items:
                getattr(menu, item[0])(*item[1:])
            return menu

        def menu(title, *items):
            return popupmenu(*items), title

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
                item("New &Person", "Create a new person", self.DoNewPerson),
                item("New &Group", "Create a new group", self.DoNewGroup),
                separator(),
                item("E&xit\tCtrl+Q", "Terminate the program", self.DoExit),
                ),
            menu("&View",
                item("All &Absences", "List all absences in the system",
                     self.DoViewAllAbsences),
                item("&School Timetable",
                     "Edit a timetable for the whole school",
                     self.DoViewSchoolTimetable),
                separator(),
                item("&Refresh\tCtrl+R", "Refresh data from the server",
                     self.DoRefresh),
                ),
            menu("&Settings",
                item("&Server", "Server settings", self.DoServerSettings),
                ),
            menu("&Help",
                item("&About", "About SchoolTool", self.DoAbout),
                ),
            ))

        def setupPopupMenu(control, menu):

            def handler(event):
                mouse_pos = wxGetMousePosition()
                control.PopupMenu(menu, control.ScreenToClient(mouse_pos))

            EVT_RIGHT_UP(control, handler)
            EVT_COMMAND_RIGHT_CLICK(control, control.GetId(), handler)
            if isinstance(control, wxTreeCtrl):
                EVT_TREE_ITEM_RIGHT_CLICK(control, control.GetId(), handler)

        # client area: vertical splitter
        splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER)

        # left pane of the splitter: group tree control
        ID_GROUP_TREE = wxNewId()
        self.groupTreeCtrl = wxTreeCtrl(splitter, ID_GROUP_TREE,
                style=wxTR_HAS_BUTTONS|wxTR_HIDE_ROOT|wxSUNKEN_BORDER)
        EVT_TREE_SEL_CHANGED(self, ID_GROUP_TREE, self.DoSelectGroup)
        self.treePopupMenu = popupmenu(
                item("Roll &Call", "Do a roll call", self.DoRollCall),
                item("&Absence Tracker",
                     "Inspect the absence tracker for this group",
                     self.DoGroupAbsenceTracker),
                separator(),
                item("&Refresh", "Refresh", self.DoRefresh)
            )
        EVT_RIGHT_DOWN(self.groupTreeCtrl, self.DoTreeRightDown)
        setupPopupMenu(self.groupTreeCtrl, self.treePopupMenu)

        # right pane of the splitter: horizontal splitter
        splitter2 = wxSplitterWindow(splitter, -1, style=wxSP_NOBORDER)

        # top pane of the second splitter: member list
        panel2a = wxPanel(splitter2, -1)
        label2a = wxStaticText(panel2a, -1, "Members")
        ID_PERSON_LIST = wxNewId()
        self.personListCtrl = wxListCtrl(panel2a, ID_PERSON_LIST,
                style=wxSUNKEN_BORDER|wxLC_LIST|wxLC_SINGLE_SEL)
        self.personPopupMenu = popupmenu(
                item("View &Absences", "View a list of person's absences",
                     self.DoViewPersonAbsences),
                separator(),
                item("&Add Member", "Add a person to this group",
                     self.DoAddMember),
                item("&Remove Member", "Remove a person from this group",
                     self.DoRemoveMember),
            )
        EVT_RIGHT_DOWN(self.personListCtrl, self.DoPersonRightDown)
        setupPopupMenu(self.personListCtrl, self.personPopupMenu)
        sizer2a = wxBoxSizer(wxVERTICAL)
        sizer2a.Add(label2a)
        sizer2a.Add(self.personListCtrl, 1, wxEXPAND)
        panel2a.SetSizer(sizer2a)

        # bottom pane of the second splitter: relationship list
        panel2b = wxPanel(splitter2, -1)
        label2b = wxStaticText(panel2b, -1, "Relationships")
        ID_RELATIONSHIP_LIST = wxNewId()
        self.relationshipListCtrl = wxListCtrl(panel2b, ID_RELATIONSHIP_LIST,
                style=wxSUNKEN_BORDER|wxLC_REPORT|wxLC_SINGLE_SEL)
        self.relationshipListCtrl.InsertColumn(0, "Title", width=110)
        self.relationshipListCtrl.InsertColumn(1, "Role", width=110)
        self.relationshipListCtrl.InsertColumn(2, "Relationship", width=110)
        self.relationshipPopupMenu = popupmenu(
                item("&Add Member", "Add a person to this group",
                     self.DoAddMember),
                item("&Add Teacher", "Add a teacher to this group",
                     self.DoAddTeacher),
                item("&Add Subgroup", "Add a group to this group",
                     self.DoAddSubgroup),
                item("&Remove Relationship", "Remove selected relationship",
                     self.DoRemoveRelationship),
            )
        EVT_RIGHT_DOWN(self.relationshipListCtrl, self.DoRelationshipRightDown)
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
        self.DoRefresh()

    def DoNewPerson(self, event):
        """Create a new person.

        Accessible from File|New Person.
        """
        name = wxGetTextFromUser("Full name", "New Person")
        if name == "":
            return
        try:
            self.client.createPerson(name)
        except SchoolToolError, e:
            wxMessageBox("Could not create a person: %s" % e,
                         "New Person", wxICON_ERROR|wxOK)
            return

    def DoNewGroup(self, event):
        """Create a new group.

        Accessible from File|New Group.
        """
        title = wxGetTextFromUser("Title", "New Group")
        if title == "":
            return
        try:
            self.client.createGroup(title)
        except SchoolToolError, e:
            wxMessageBox("Could not create a group: %s" % e,
                         "New Group", wxICON_ERROR|wxOK)
            return

    def DoAddMember(self, event):
        """Add a person from the current group.

        Accessible from person list popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText("No group selected")
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        try:
            persons = self.client.getListOfPersons()
        except SchoolToolError, e:
            wxMessageBox("Could not get a list of persons: %s" % e,
                         "Add Teacher", wxICON_ERROR|wxOK)
            return
        persons.sort()

        # wxGetMultipleChoice is defined in wxWindows API documentation,
        # but wxPython 2.4.2.4 does NOT have it.
        choice = wxGetSingleChoiceIndex(
                        "Select a person to add to %s" % group_title,
                        "Add Member", [p[0] for p in persons])
        if choice == -1:
            return

        person_path = persons[choice][1]
        try:
            self.client.createRelationship(group_path, person_path,
                                           URIMembership, URIGroup)
        except SchoolToolError, e:
            wxMessageBox("Could not add member: %s" % e,
                         "Add Member", wxICON_ERROR|wxOK)
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
            self.SetStatusText("No group selected")
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        try:
            teachers_group = self.client.getGroupInfo('/groups/teachers')
        except SchoolToolError, e:
            wxMessageBox("Could not get a list of teachers: %s" % e,
                         "Add Teacher", wxICON_ERROR|wxOK)
            return
        persons = teachers_group.members
        persons.sort()

        # wxGetMultipleChoice is defined in wxWindows API documentation,
        # but wxPython 2.4.2.4 does NOT have it.
        choice = wxGetSingleChoiceIndex(
                        "Select a teacher to add to %s" % group_title,
                        "Add Teacher", [p.person_title for p in persons])
        if choice == -1:
            return

        person_path = persons[choice].person_path
        try:
            self.client.createRelationship(group_path, person_path,
                                           URITeaching, URITaught)
        except SchoolToolError, e:
            wxMessageBox("Could not add teacher: %s" % e,
                         "Add Teacher", wxICON_ERROR|wxOK)
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
            self.SetStatusText("No group selected")
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        try:
            groups = self.client.getListOfGroups()
        except SchoolToolError, e:
            wxMessageBox("Could not get a list of groups: %s" % e,
                         "Add Subgroup", wxICON_ERROR|wxOK)
            return
        groups.sort()

        # wxGetMultipleChoice is defined in wxWindows API documentation,
        # but wxPython 2.4.2.4 does NOT have it.
        choice = wxGetSingleChoiceIndex(
                        "Select a group to add to %s" % group_title,
                        "Add Subgroup", [g[0] for g in groups])
        if choice == -1:
            return

        subgroup_path = groups[choice][1]
        try:
            self.client.createRelationship(group_path, subgroup_path,
                                           URIMembership, URIGroup)
        except SchoolToolError, e:
            wxMessageBox("Could not add subgroup: %s" % e,
                         "Add Subgroup", wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoRemoveMember(self, event):
        """Remove a person from the current group.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText("No person selected")
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]

        for relationship in self.relationshipListData:
            if relationship.target_path == member.person_path:
                break
        else:
            # should not happen
            self.SetStatusText("Selected person is not a member of this group")
            return

        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText("No group selected")
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        if wxMessageBox("Really remove %s from %s?"
                        % (member.person_title, group_title),
                        "Remove Person", wxYES_NO) != wxYES:
            return

        try:
            self.client.deleteObject(relationship.link_path)
        except SchoolToolError, e:
            wxMessageBox("Could not remove member: %s" % e,
                         "Remove Person", wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoRemoveRelationship(self, event):
        """Remove a relationship.

        Accessible from relationship list popup menu.
        """
        item = self.relationshipListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText("No relationship selected")
            return
        key = self.relationshipListCtrl.GetItemData(item)
        relationship = self.relationshipListData[key]

        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            # should not happen
            self.SetStatusText("No group selected")
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)

        if wxMessageBox("Really remove %s (%s) from %s?"
                        % (relationship.target_title, relationship.role,
                           group_title),
                        "Remove Relationship", wxYES_NO) != wxYES:
            return

        try:
            self.client.deleteObject(relationship.link_path)
        except SchoolToolError, e:
            wxMessageBox("Could not remove relationship: %s" % e,
                         "Remove Relationship", wxICON_ERROR|wxOK)
            return
        else:
            self.DoRefresh()

    def DoExit(self, event):
        """Exit the application.

        Accessible via Ctrl+Q and from File|Exit.
        """
        self.Close(True)

    def DoServerSettings(self, event):
        """Show the Server Settings dialog.

        Accessible from Settings|Server settings.
        """
        dlg = ServerSettingsDlg(self)
        dlg.setServer(self.client.server)
        dlg.setPort(self.client.port)
        if dlg.ShowModal() == wxID_OK:
            self.client.setServer(dlg.getServer(), dlg.getPort())
            self.DoRefresh()
        dlg.Destroy()

    def DoAbout(self, event):
        """Show the About dialog.

        Accessible from Help|About.
        """
        dlg = wxMessageDialog(self, __doc__, "About SchoolTool", wxOK)
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
            self.relationshipListCtrl.SetStringItem(idx, 1, item.role)
            self.relationshipListCtrl.SetStringItem(idx, 2, item.arcrole)
        self.relationshipListCtrl.Thaw()

    def DoTreeRightDown(self, event):
        """Select the group under mouse cursor.

        Called when the right mouse buton is pressed on the group tree
        control.
        """
        item, flags = self.groupTreeCtrl.HitTest(event.GetPosition())
        if item.IsOk():
            self.groupTreeCtrl.SelectItem(item)
        event.Skip()

    def DoPersonRightDown(self, event):
        """Select the person under mouse cursor.

        Called when the right mouse buton is pressed on the person list
        control.
        """
        item, flags = self.personListCtrl.HitTest(event.GetPosition())
        if flags & wxLIST_HITTEST_ONITEM:
            self.personListCtrl.Select(item)
        event.Skip()

    def DoRelationshipRightDown(self, event):
        """Select the relationship under mouse cursor.

        Called when the right mouse buton is pressed on the relationship list
        control.
        """
        item, flags = self.relationshipListCtrl.HitTest(event.GetPosition())
        if flags & wxLIST_HITTEST_ONITEM:
            self.relationshipListCtrl.Select(item)
        event.Skip()

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
        root = self.groupTreeCtrl.GetRootItem()
        expanded = sets.Set()
        stack = [root]
        while stack:
            item = stack.pop()
            if item is not root and self.groupTreeCtrl.IsExpanded(item):
                expanded.add(self.groupTreeCtrl.GetPyData(item)[1])
            next, cookie = self.groupTreeCtrl.GetFirstChild(item, 0)
            while next.IsOk():
                stack.append(next)
                next, cookie = self.groupTreeCtrl.GetNextChild(item, cookie)

        # Reload tree
        self.groupTreeCtrl.Freeze()
        self.groupTreeCtrl.DeleteAllItems()
        root = self.groupTreeCtrl.AddRoot("Roots")

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
            self.SetStatusText("No group selected")
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

    def DoViewPersonAbsences(self, event=None):
        """Open the absences window for the currently selected person.

        Accessible from person list popup menu.
        """
        item = self.personListCtrl.GetFirstSelected()
        if item == -1:
            self.SetStatusText("No person selected")
            return
        key = self.personListCtrl.GetItemData(item)
        member = self.personListData[key]
        window = AbsenceFrame(self.client, "%s/absences" % member.person_path,
                              parent=self, persons=False,
                              title="%s's absences" % member.person_title)
        window.Show()

    def DoViewAllAbsences(self, event=None):
        """Open the absences window for the whole system person.

        Accessible via View|All Absences.
        """
        window = AbsenceFrame(self.client, "/utils/absences", parent=self,
                              title="All absences", detailed=False)
        window.Show()

    def DoGroupAbsenceTracker(self, event=None):
        """Open the absences window for the currently selected group.

        Accessible from group popup menu.
        """
        item = self.groupTreeCtrl.GetSelection()
        if not item.IsOk():
            self.SetStatusText("No group selected")
            return
        group_path = self.groupTreeCtrl.GetPyData(item)[0]
        group_title = self.groupTreeCtrl.GetItemText(item)
        path = "%s/facets/absences" % group_path
        title = "Absences of %s" % group_title
        try:
            try:
                absence_data = self.client.getAbsences(path)
            except ResponseStatusError, e:
                if e.status != 404:
                    raise
                if wxMessageBox("Do you want to create a new absence"
                                " tracker facet and put it on %s?"
                                % group_title, title, wxYES_NO) != wxYES:
                    return
                try:
                    self.client.createFacet(group_path, 'absence_tracker')
                except SchoolToolError, e:
                    wxMessageBox("Could not create an absence tracker: %s" % e,
                                 title, wxICON_ERROR|wxOK)
                    return
                else:
                    absence_data = self.client.getAbsences(path)
        except SchoolToolError, e:
            wxMessageBox("Could not get the list of absences: %s" % e,
                         title, wxICON_ERROR|wxOK)
            return
        window = AbsenceFrame(parent=self, title=title, detailed=False,
                              client=self.client, path=path,
                              absence_data=absence_data)
        window.Show()

    def DoViewSchoolTimetable(self, event=None):
        """Open a school timetable window for a selected timetable.

        Accessible from View|School Timetable
        """
        try:
            periods = self.client.getTimePeriods()
        except SchoolToolError, e:
            wxMessageBox("Could not get the list of time periods: %s" % e,
                         "School Timetable", wxICON_ERROR|wxOK)
            return
        else:
            periods.sort()
        try:
            schemas = self.client.getTimetableSchemas()
        except SchoolToolError, e:
            wxMessageBox("Could not get the list of timetable schemas: %s" % e,
                         "School Timetable", wxICON_ERROR|wxOK)
            return
        else:
            schemas.sort()
        choices = [(p, s) for p in periods for s in schemas]
        choice = wxGetSingleChoiceIndex(
                        "Select a timetable to edit",
                        "School Timetable", ["%s, %s" % c for c in choices])
        if choice == -1:
            return
        key = choices[choice]
        try:
            tt = self.client.getSchoolTimetable(*key)
        except SchoolToolError, e:
            wxMessageBox("Could not get the school timetable: %s" % e,
                         "School Timetable", wxICON_ERROR|wxOK)
            return
        window = SchoolTimetableFrame(self.client, key, tt, parent=self)
        window.Show()


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
        return True


def main():
    # Do not output XML parsing errors to the terminal
    libxml2.registerErrorHandler(lambda ctx, error: None, None)
    wxInitAllImageHandlers()
    client = SchoolToolClient()
    app = SchoolToolApp(client)
    app.MainLoop()


if __name__ == '__main__':
    main()
