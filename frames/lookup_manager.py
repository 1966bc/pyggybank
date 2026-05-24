#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   lookup_manager.py  (was filters.py)
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / wxPython 4 (Phoenix)
# version:  3.0
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
# license: wxWindows License
#-----------------------------------------------------------------------------

"""
Manager window for a lookup table: list the categories (or suppliers) and
add/edit them through the LookupEditor. It talks to the Controller only
(list_lookup / get_lookup), never to the database. Rows arrive normalised as
{'pk', 'name', 'enabled'}; the pk is kept as the ListCtrl item data.
"""

import wx

from frames import lookup_editor


class LookupManager(wx.Frame):
    def __init__(self, parent, controller, table: str) -> None:
        wx.Frame.__init__(self, parent, -1,
                          style=wx.GetApp().engine.frame_style(), name="lookup_manager")

        self.controller = controller
        self.table = table

        self.SetIcon(wx.Icon(wx.GetApp().engine.icon, wx.BITMAP_TYPE_ICO))
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        p = wx.Panel(self)
        fw = wx.GetApp().engine.get_font()

        self.stTitle = wx.StaticText(p, -1, '')
        self.stTitle.SetFont(wx.Font(10, wx.FONTFAMILY_SWISS,
                                     wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.lst = wx.ListCtrl(p, -1, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES,
                               size=(fw * 18, fw * 15))
        self.lst.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit)
        self.lst.InsertColumn(0, 'Name', wx.LIST_FORMAT_LEFT, width=fw * 15)

        sbb = wx.StaticBox(p, wx.ID_ANY, "")
        for (id, label, help_text, handler) in [(wx.ID_ADD, '&Add', 'add data!', self.on_add),
                                                (wx.ID_EDIT, '&Edit', 'edit data!', self.on_edit),
                                                (wx.ID_CLOSE, '&Close', 'close', self.on_close)]:
            b = wx.Button(p, id, label)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, handler)

        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.BoxSizer(wx.VERTICAL)
        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)
        for i in (self.stTitle, self.lst):
            s1.Add(i, 0, wx.ALL, 1)
        for i in p.GetChildren():
            if isinstance(i, wx.Button):
                s2.Add(i, 0, wx.EXPAND | wx.ALL, 5)
        for i in (s1, s2):
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    # ------------------------------------------------------------------ #
    def OnOpen(self) -> None:
        rows = self.controller.list_lookup(self.table)
        self.lst.DeleteAllItems()
        self.stTitle.SetLabel("%s list %s" % (self.table, len(rows)))
        self.SetTitle(self.table)
        for r in rows:
            index = self.lst.InsertItem(self.lst.GetItemCount(), str(r['name']).strip())
            self.lst.SetItemData(index, int(r['pk']))
            if not r['enabled']:
                self.lst.SetItemBackgroundColour(index, wx.Colour(wx.GetApp().engine.disable))

    def reload(self) -> None:
        self.OnOpen()

    def _selected_pk(self):
        index = self.lst.GetFirstSelected()
        return None if index == -1 else self.lst.GetItemData(index)

    # ------------------------------------------------------------------ #
    def on_add(self, evt) -> None:
        editor = lookup_editor.LookupEditor(self, self.controller, self.table)
        editor.OnOpen()
        editor.Center()
        editor.ShowModal()

    def on_edit(self, evt) -> None:
        pk = self._selected_pk()
        if pk is None:
            wx.MessageBox("Attention!\nSelect an item from list!",
                          wx.GetApp().GetAppName(), wx.OK | wx.ICON_INFORMATION)
            return
        editor = lookup_editor.LookupEditor(self, self.controller, self.table)
        editor.OnOpen(self.controller.get_lookup(self.table, pk))
        editor.Center()
        editor.ShowModal()

    def on_close(self, evt) -> None:
        wx.GetApp().engine.del_instance(self)
        self.Destroy()

    def OnExit(self, event) -> None:
        self.on_close(event)
