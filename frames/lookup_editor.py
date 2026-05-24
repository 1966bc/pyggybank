#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   lookup_editor.py  (was update_filter.py)
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / wxPython 4 (Phoenix)
# version:  3.0
# description: add / edit one lookup-table row (a category or a supplier)
#-----------------------------------------------------------------------------

"""
Editor for a single lookup row: a category or a supplier (name + enabled flag).

It is generic over the two lookup tables. It exchanges named data with the
Controller (save_lookup) and never builds SQL. Records arrive normalised as
{'pk', 'name', 'enabled'} from controller.get_lookup().
"""

from typing import Any, Dict, Optional

import wx


class LookupEditor(wx.Dialog):
    def __init__(self, parent, controller, table: str) -> None:
        wx.Dialog.__init__(self, parent, wx.ID_ANY, name='lookup_editor')

        self.controller = controller
        self.table = table
        self.pk: Optional[int] = None
        self.insert_mode = True

        self.SetIcon(wx.Icon(wx.GetApp().engine.icon, wx.BITMAP_TYPE_ICO))
        p = wx.Panel(self, -1)
        fw = wx.GetApp().engine.get_font()

        self.stName = wx.StaticText(p, wx.ID_ANY, 'Name')
        self.txName = wx.TextCtrl(p, wx.ID_ANY, "", size=(fw * 20, -1))
        self.txName.SetMaxLength(16)
        self.txName.SetToolTip('Max chars 16')

        self.stEnable = wx.StaticText(p, wx.ID_ANY, 'Enable')
        self.ckEnable = wx.CheckBox(p, wx.ID_ANY)

        sbb = wx.StaticBox(p, wx.ID_ANY, "")
        for (id, label, help_text) in [(wx.ID_SAVE, '&Save', 'save data!'),
                                       (wx.ID_CLOSE, '&Close', 'close')]:
            b = wx.Button(p, id, label)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, self.OnClick)

        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)
        for i in (self.stName, self.txName, self.stEnable, self.ckEnable):
            s1.Add(i, 0, wx.ALL, 1)
        for i in p.GetChildren():
            if isinstance(i, wx.Button):
                s2.Add(i, 0, wx.EXPAND | wx.ALL, 5)
        for i in (s1, s2):
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    def OnOpen(self, record: Optional[Dict[str, Any]] = None) -> None:
        if record is not None:
            self.insert_mode = False
            self.pk = record['pk']
            self.SetTitle("Update %s" % record['name'])
            self.txName.SetValue(str(record['name']))
            self.ckEnable.SetValue(bool(record['enabled']))
        else:
            self.insert_mode = True
            self.pk = None
            self.SetTitle("Insert new item in %s" % self.table)
            self.ckEnable.SetValue(True)

    def OnClick(self, event: wx.CommandEvent) -> None:
        if event.GetId() == wx.ID_SAVE:
            if self.OnFieldsControl() == 0:
                return
            if wx.GetApp().engine.ask("Save data?") == wx.ID_YES:
                self.controller.save_lookup(self.table,
                                            self.txName.GetValue().strip(),
                                            self.ckEnable.GetValue(),
                                            self.pk)
                self.GetParent().reload()
                self.OnClick(self.FindWindowById(wx.ID_CLOSE))
            else:
                wx.GetApp().engine.answer_info("Operation abort!")
                self.txName.SetFocus()
        elif event.GetId() == wx.ID_CLOSE:
            self.Destroy()

    def OnExit(self, event) -> None:
        self.OnClick(self.FindWindowById(wx.ID_CLOSE))

    def OnFieldsControl(self) -> Optional[int]:
        return wx.GetApp().engine.fields_control({self.txName: self.stName.GetLabel()})
