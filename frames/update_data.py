#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   update_data.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / wxPython 4 (Phoenix)
# version:  3.0
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
# license: wxWindows License
#-----------------------------------------------------------------------------

"""
Add / edit dialog for an event (a money flow).

It is a view: it exchanges a named record (dict keyed by column name) with the
Controller and never builds SQL nor touches the DBMS. The combos are filled
from controller.list_lookup(); saving goes through controller.save_event().
UI-only services (calendar conversion, field validation, ask/info) still come
from the app context.
"""

import datetime
from typing import Any, Dict, Optional

import wx
import wx.adv
from wx.lib import masked

ID_SUPPLIERS = wx.NewIdRef()
ID_CATEGORIES = wx.NewIdRef()


class Dialog(wx.Dialog):
    def __init__(self, parent, controller) -> None:
        wx.Dialog.__init__(self, parent, wx.ID_ANY, name='update_event')

        self.controller = controller

        self.Bind(wx.EVT_CLOSE, self.OnExit)
        self.SetIcon(wx.Icon(wx.GetApp().engine.icon, wx.BITMAP_TYPE_ICO))
        p = wx.Panel(self)
        fw = wx.GetApp().engine.get_font()

        # widgets
        self.stSupplier = wx.StaticText(p, wx.ID_ANY, 'Company')
        self.cbSuppliers = wx.ComboBox(p, ID_SUPPLIERS, size=(fw * 20, -1), style=wx.CB_READONLY)
        self.cbSuppliers.SetToolTip('Select a supplier.')

        self.stCategory = wx.StaticText(p, wx.ID_ANY, 'Category')
        self.cbCategories = wx.ComboBox(p, ID_CATEGORIES, size=(fw * 20, -1), style=wx.CB_READONLY)
        self.cbCategories.SetToolTip('Select a category.')

        self.stReference = wx.StaticText(p, wx.ID_ANY, 'Reference')
        self.txReference = wx.TextCtrl(p, wx.ID_ANY, 'No', size=(fw * 20, -1))
        self.txReference.SetMaxLength(30)
        self.txReference.SetToolTip('Insert reference.\nMax 30 chars.')
        self.txReference.SetForegroundColour(wx.Colour(255, 0, 0))

        self.stDescription = wx.StaticText(p, wx.ID_ANY, 'Description')
        self.txDescription = wx.TextCtrl(p, wx.ID_ANY, 'No', size=(fw * 20, -1))

        self.stBill = wx.StaticText(p, wx.ID_ANY, 'Bill')
        self.txBill = masked.NumCtrl(p, wx.ID_ANY, integerWidth=4, fractionWidth=2,
                                     size=(fw * 12, -1))
        self.txBill.SetToolTip('Price.')

        self.stIssued = wx.StaticText(p, wx.ID_ANY, "Issued")
        self.dpcIssued = wx.adv.DatePickerCtrl(p, size=(fw * 12, -1),
                                               style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        self.dpcIssued.SetToolTip('Issued date!')

        self.stExpiration = wx.StaticText(p, -1, "Expiration")
        self.dpcExpiration = wx.adv.DatePickerCtrl(p, wx.ID_ANY, size=(fw * 12, -1),
                                                   style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        self.dpcExpiration.SetToolTip('Expiration date!')

        self.stFlow = wx.StaticText(p, wx.ID_ANY, 'Flow')
        self.ckFlow = wx.CheckBox(p, wx.ID_ANY)
        self.ckFlow.SetToolTip('Select = In\nDeselect = Out')

        self.stSettled = wx.StaticText(p, wx.ID_ANY, 'Settled')
        self.ckSettled = wx.CheckBox(p, wx.ID_ANY)
        self.ckSettled.SetToolTip('Select = settled\nDeselect = unsettle')

        self.stEnable = wx.StaticText(p, wx.ID_ANY, 'Enable')
        self.ckEnable = wx.CheckBox(p, wx.ID_ANY)

        sbb = wx.StaticBox(p, wx.ID_ANY, "")
        for (id, label, help_text) in [(wx.ID_SAVE, '&Save', 'save data!'),
                                       (wx.ID_CLOSE, '&Close', 'close frame')]:
            b = wx.Button(p, id, label)
            b.SetToolTip(help_text)
            b.Bind(wx.EVT_BUTTON, self.OnClick)

        # sizers
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        s2 = wx.StaticBoxSizer(sbb, wx.VERTICAL)

        for i in (self.stSupplier, self.cbSuppliers, self.stCategory, self.cbCategories,
                  self.stReference, self.txReference, self.stDescription, self.txDescription,
                  self.stBill, self.txBill, self.stIssued, self.dpcIssued,
                  self.stExpiration, self.dpcExpiration, self.stFlow, self.ckFlow,
                  self.stSettled, self.ckSettled, self.stEnable, self.ckEnable):
            s1.Add(i, 0, wx.ALL, 1)
        for i in p.GetChildren():
            if isinstance(i, wx.Button):
                s2.Add(i, 0, wx.EXPAND | wx.ALL, 5)
        for i in (s1, s2):
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    def OnOpen(self, selected_event: Optional[Dict[str, Any]] = None) -> None:

        self.dict_suppliers: Dict[int, int] = {}
        self.dict_category: Dict[int, int] = {}
        self._fill_combo(self.cbSuppliers, self.controller.list_lookup('suppliers'), self.dict_suppliers)
        self._fill_combo(self.cbCategories, self.controller.list_lookup('categories'), self.dict_category)

        if selected_event is not None:
            self.insert_mode = False
            self.selected_event = selected_event
            self.SetTitle("Update  %s" % (selected_event["reference"],))

            self.ckFlow.SetValue(selected_event["flow"])
            self.cbSuppliers.SetSelection(self.dict_suppliers[selected_event["supplier_id"]])
            self.cbCategories.SetSelection(self.dict_category[selected_event["category_id"]])
            self.ckSettled.SetValue(selected_event["settled"])
            self.txReference.SetValue(str(selected_event["reference"]))
            self.txBill.SetValue(str(selected_event["bill"]))
            self.dpcIssued.SetValue(wx.GetApp().engine.set_calendar_date(selected_event["issued"]))
            self.dpcExpiration.SetValue(wx.GetApp().engine.set_calendar_date(selected_event["expiration"]))
            self.txDescription.SetValue(str(selected_event["description"]))
            self.ckEnable.SetValue(selected_event["enable"])
        else:
            self.insert_mode = True
            self.SetTitle('Add Transaction')
            self.ckEnable.SetValue(True)
            self.ckSettled.SetValue(True)

    def _fill_combo(self, combo: wx.ComboBox, items, store: Dict[int, int]) -> None:
        """Populate a combo with lookup items and map each pk to its index."""
        combo.Clear()
        for it in items:
            name = str(it['name']).strip()
            combo.Append(name, (int(it['pk']), name))
        for index in range(combo.GetCount()):
            store[int(combo.GetClientData(index)[0])] = index

    @staticmethod
    def _combo_pk(combo: wx.ComboBox) -> int:
        return int(combo.GetClientData(combo.GetSelection())[0])

    def GetValue(self) -> Dict[str, Any]:
        """The dialog's content as a {column: value} record for the controller."""
        return {
            'flow': self.ckFlow.GetValue(),
            'supplier_id': self._combo_pk(self.cbSuppliers),
            'category_id': self._combo_pk(self.cbCategories),
            'settled': self.ckSettled.GetValue(),
            'reference': self.txReference.GetValue().strip(),
            'bill': self.txBill.GetValue(),
            'issued': wx.GetApp().engine.get_calendar_date(self.dpcIssued.GetValue()),
            'expiration': wx.GetApp().engine.get_calendar_date(self.dpcExpiration.GetValue()),
            'description': self.txDescription.GetValue().strip(),
            'modify': datetime.datetime.now(),
            'enable': self.ckEnable.GetValue(),
        }

    def OnClick(self, event: wx.CommandEvent) -> None:

        if event.GetId() == wx.ID_SAVE:
            if self.OnFieldsControl() == 0:
                return
            if wx.GetApp().engine.ask("Save data?") == wx.ID_YES:
                event_id = None if self.insert_mode else self.selected_event["event_id"]
                self.controller.save_event(self.GetValue(), event_id)
                self.GetParent().reload()
                self.OnClick(self.FindWindowById(wx.ID_CLOSE))
            else:
                wx.GetApp().engine.answer_info("Operation abort!")
                self.txReference.SetFocus()

        elif event.GetId() == wx.ID_CLOSE:
            self.Destroy()

    def OnExit(self, event) -> None:
        self.OnClick(self.FindWindowById(wx.ID_CLOSE))

    def OnFieldsControl(self) -> Optional[int]:
        return wx.GetApp().engine.fields_control({
            self.cbSuppliers: self.stSupplier.GetLabel(),
            self.cbCategories: self.stCategory.GetLabel(),
            self.txReference: self.stReference.GetLabel(),
            self.txDescription: self.stDescription.GetLabel()})
