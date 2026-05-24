#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   filters.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / wxPython 4 (Phoenix)
# version:  3.0
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
# license: wxWindows License
#-----------------------------------------------------------------------------

"""
This module provides frame to manage some database operation.
"""

import wx

from frames import update_filter


class Frame(wx.Frame):
    def __init__(self, parent) -> None:
        wx.Frame.__init__(self, parent, -1, style=wx.GetApp().engine.frame_style(), name="filters")

        self.SetIcon(wx.Icon(wx.GetApp().engine.icon, wx.BITMAP_TYPE_ICO))
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        p = wx.Panel(self)

        # widgets
        self.stFilter = wx.StaticText(p, -1, '')
        self.stFilter.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS,
                                      wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.lstFilters = wx.ListCtrl(p, -1,
                                      style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES,
                                      size=(wx.GetApp().engine.get_font() * 18,
                                            wx.GetApp().engine.get_font() * 15),)
        self.lstFilters.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.lstFilters.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        self.lstFilters.InsertColumn(0, '', width=0)
        self.lstFilters.InsertColumn(1, '', wx.LIST_FORMAT_LEFT, width=wx.GetApp().engine.get_font() * 15)

        sbb = wx.StaticBox(p, wx.ID_ANY, "")

        bts = [(wx.ID_ADD, '&Add', 'add data!'),
               (wx.ID_EDIT, '&Edit', 'edit data!'),
               (wx.ID_CLOSE, '&Close', 'close'), ]
        for (id, label, help_text) in bts:
            b = wx.Button(p, id, label,)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, self.OnClick)

        # sizer
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.BoxSizer(wx.VERTICAL)
        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)

        w = (self.stFilter, self.lstFilters)

        for i in w:
            s1.Add(i, 0, wx.ALL, 1)

        for i in p.GetChildren():
            if isinstance(i, wx.Button):
                s2.Add(i, 0, wx.EXPAND | wx.ALL, 5)

        w = (s1, s2)
        for i in w:
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    # event handling
    def OnOpen(self, table: str, pk: str) -> None:
        """this function recive a table name and his primary key
           and populate le lstctrl

           #table: the table to use
           @pk : the primary key field name
        """

        self.table = table
        self.pk = pk
        rs = wx.GetApp().engine.read(True, wx.GetApp().engine.dict_queries[self.table])

        self.lstFilters.DeleteAllItems()
        format_label = "%s list %s" % (table, len(rs))
        self.stFilter.SetLabel(format_label)
        self.SetTitle(table)
        for i in rs:
            values = list(i.values())
            index = self.lstFilters.InsertItem(self.lstFilters.GetItemCount(), str(values[0]).strip())
            self.lstFilters.SetItem(index, 1, str(values[1]).strip())
            if values[2] == 0:
                self.lstFilters.SetItemBackgroundColour(index, wx.Colour(wx.GetApp().engine.disable))

    def OnClick(self, event: wx.CommandEvent) -> None:

        if event.GetId() == wx.ID_ADD:

            obj = update_filter.Dialog(parent=self)
            obj.OnOpen(self.table, self.pk)
            obj.Center()
            obj.ShowModal()

        elif event.GetId() == wx.ID_EDIT:

            index = self.lstFilters.GetFirstSelected()
            if index == -1:
                message = "Attention!\nSelect an item from list!"
                wx.MessageBox(message,
                              wx.GetApp().GetAppName(),
                              wx.OK | wx.ICON_INFORMATION)
                return

            obj = update_filter.Dialog(parent=self)
            obj.OnOpen(self.table, self.pk, self.dict_record)
            obj.Center()
            obj.ShowModal()

        elif event.GetId() == wx.ID_CLOSE:
            wx.GetApp().engine.del_instance(wx.GetApp().engine.dict_instances[self.GetName()])
            self.Destroy()

    def OnExit(self, event) -> None:
        self.OnClick(self.FindWindowById(wx.ID_CLOSE))

    def OnItemSelected(self, event: wx.ListEvent) -> None:

        index = self.lstFilters.GetFirstSelected()
        if index == -1:
            return
        item = int(event.GetItem().GetText())
        self.dict_record = wx.GetApp().engine.get_selected(self.table, self.pk, item)

    def OnItemActivated(self, event: wx.ListEvent) -> None:
        self.OnClick(self.FindWindowById(wx.ID_EDIT))
