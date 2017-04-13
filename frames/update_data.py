#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   update_data.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   29/05/2015
# version:  0.4
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007                      
# license: wxWindows License 
#-----------------------------------------------------------------------------

"""
This module is used to perform insert, update and delete operation
on database
"""

import wx
from wx.lib import masked
import datetime
from string import strip

ID_SUPPLIERS = wx.NewId()
ID_CATEGORIES = wx.NewId()

class Dialog(wx.Dialog):
    def __init__(self,parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, name = 'update_event')
        

        #set some frame properties
        self.Bind(wx.EVT_CLOSE, self.OnExit)
        self.SetIcon(wx.Icon(wx.GetApp().engine.icon,wx.BITMAP_TYPE_ICO)) 
        p = wx.Panel(self)
        #widgets
        self.stSupplier = wx.StaticText(p, wx.ID_ANY, 'Company')
        self.cbSuppliers = wx.ComboBox(p,ID_SUPPLIERS,
                                       size=(wx.GetApp().engine.get_font() * 20, -1),
                                       style= wx.CB_READONLY)
        self.cbSuppliers.SetToolTipString('Select a supplier.')

        self.stCategory = wx.StaticText(p, wx.ID_ANY, 'Category')
        self.cbCategories = wx.ComboBox(p,ID_CATEGORIES,
                                       size=(wx.GetApp().engine.get_font() * 20, -1),
                                       style= wx.CB_READONLY)
        self.cbCategories.SetToolTipString('Select a category.')


        self.stReference = wx.StaticText(p, wx.ID_ANY, 'Reference')
        self.txReference = wx.TextCtrl(p, wx.ID_ANY, 'No',
                                     size = (wx.GetApp().engine.get_font() * 20,-1))
        self.txReference.SetMaxLength(30)
        message = 'Insert reference.\nMax 30 chars.'
        self.txReference.SetToolTipString(message)
        #to fix...in debian 8 jessie i get an error with wx.Color call
        try:
            self.txReference.SetForegroundColour(wx.Color(255, 0, 0))
        except:pass            

        self.stDescription = wx.StaticText(p, wx.ID_ANY, 'Description')
        self.txDescription = wx.TextCtrl(p, wx.ID_ANY, 'No',
                                         size = (wx.GetApp().engine.get_font() *20, -1))
        
        self.stBill = wx.StaticText(p, wx.ID_ANY, 'Bill')
        self.txBill = masked.NumCtrl(p,wx.ID_ANY,
                                     integerWidth = 4,
                                     fractionWidth = 2,
                                     size = (wx.GetApp().engine.get_font() *12 ,-1))
        self.txBill.SetToolTipString('Price.')

        self.stIssued = wx.StaticText(p, wx.ID_ANY, "Issued")
        self.dpcIssued = wx.DatePickerCtrl(p, size=(wx.GetApp().engine.get_font() *12,-1),
                                           style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        self.dpcIssued.SetToolTipString('Issued date!')

        self.stExpiration = wx.StaticText(p, -1, "Expiration")
        self.dpcExpiration = wx.DatePickerCtrl(p,wx.ID_ANY,
                                           size=(wx.GetApp().engine.get_font() *12,-1),
                                           style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        self.dpcExpiration.SetToolTipString('Expiration date!')

        self.stFlow = wx.StaticText(p, wx.ID_ANY, 'Flow')
        self.ckFlow = wx.CheckBox(p, wx.ID_ANY)
        self.ckFlow.SetToolTipString('Select = In\nDeselect = Out')
        
        self.stSettled = wx.StaticText(p, wx.ID_ANY, 'Settled')
        self.ckSettled = wx.CheckBox(p, wx.ID_ANY)
        self.ckSettled.SetToolTipString('Select = settled\nDeselect = unsettle')
         
        self.stEnable = wx.StaticText(p, wx.ID_ANY, 'Enable')
        self.ckEnable = wx.CheckBox(p, wx.ID_ANY)
        
        sbb = wx.StaticBox(p,wx.ID_ANY,"")

        bts = [(wx.ID_SAVE,'&Save','save data!'),
              (wx.ID_CLOSE,'&Close','close frame'),]
        for (id, label, help_text) in bts:
            b = wx.Button(p, id, label,)
            b.SetToolTipString(help_text)
            b.Bind(wx.EVT_BUTTON, self.OnClick)

        #sizers
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.FlexGridSizer(cols = 2, hgap = 5, vgap = 5)
        s2 = wx.StaticBoxSizer(sbb,wx.VERTICAL)

        w = (self.stSupplier,self.cbSuppliers,
              self.stCategory,self.cbCategories,
              self.stReference,self.txReference,
              self.stDescription,self.txDescription,
              self.stBill,self.txBill,
              self.stIssued,self.dpcIssued,
              self.stExpiration,self.dpcExpiration,
              self.stFlow,self.ckFlow,
              self.stSettled,self.ckSettled,
              self.stEnable,self.ckEnable,)
        for i in w:
            s1.Add(i,0,wx.ALL, 1)

        for i in p.GetChildren():
            if type(i) in(wx.Button,):
                s2.Add(i,0,wx.EXPAND|wx.ALL, 5)

        w = (s1,s2)
        for i in w:
            s0.Add(i, 0, wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)

    def OnOpen(self, selected_event = None):

        self.dict_suppliers ={}
        self.dict_category ={}

        d = {ID_SUPPLIERS:(self.dict_suppliers,"SELECT * FROM suppliers ORDER BY supplier", (),None), 
             ID_CATEGORIES:(self.dict_category,"SELECT * FROM categories ORDER BY category", (),None),}

        wx.GetApp().engine.set_combo(d,self)
        
        
        if selected_event is not None:
            self.insert_mode = False
            self.selected_event = selected_event
            message = "Update  %s" % (self.selected_event[5],)
            self.SetTitle (message)


            self.ckFlow.SetValue(self.selected_event[1])
            self.cbSuppliers.SetSelection(self.dict_suppliers[self.selected_event[2]])
            self.cbCategories.SetSelection(self.dict_category[self.selected_event[3]])
            self.ckSettled.SetValue(self.selected_event[4])
            self.txReference.SetValue(str(self.selected_event[5].encode("latin-1")))
            self.txBill.SetValue(str(self.selected_event[6]))
            self.dpcIssued.SetValue(wx.GetApp().engine.set_calendar_date(self.selected_event[7]))
            self.dpcExpiration.SetValue(wx.GetApp().engine.set_calendar_date(self.selected_event[8]))
            self.txDescription.SetValue(str(self.selected_event[9].encode("latin-1")))
            self.ckEnable.SetValue(self.selected_event[11])
            
        else:
            self.insert_mode = True
            self.SetTitle ('Add Transaction')
            self.ckEnable.SetValue(True)
            self.ckSettled.SetValue(True)

    def GetValue(self,):

        return (self.ckFlow.GetValue(),
                wx.GetApp().engine.get_combo_id(self,ID_SUPPLIERS),
                wx.GetApp().engine.get_combo_id(self,ID_CATEGORIES),
                self.ckSettled.GetValue(),
                strip(self.txReference.GetValue()),
                self.txBill.GetValue(),
                wx.GetApp().engine.get_calendar_date(self.dpcIssued.GetValue()),
                wx.GetApp().engine.get_calendar_date(self.dpcExpiration.GetValue()),
                strip(str(self.txDescription.GetValue().encode("utf-8"))),
                datetime.datetime.now(),
                self.ckEnable.GetValue(),)            

    def OnClick(self,event):

        if event.GetId() == wx.ID_SAVE:

            if self.OnFieldsControl()==0:return

            if (wx.GetApp().engine.ask("Save data?") == wx.ID_YES):

                args = self.GetValue()

                if self.insert_mode == False:

                    sql = wx.GetApp().engine.get_update_sql('events','event_id')

                    args = wx.GetApp().engine.get_update_sql_args(args, self.selected_event[0])

                elif self.insert_mode == True:

                    sql = wx.GetApp().engine.get_insert_sql('events',len(args))

                wx.GetApp().engine.write(sql,args)
                self.GetParent().get_args()
                self.OnClick(self.FindWindowById(wx.ID_CLOSE))
                    
            else:
                wx.GetApp().engine.answer_info("Operation abort!")
                self.txReference.SetFocus()

        elif event.GetId() == wx.ID_CLOSE:
            self.Destroy()

    def OnExit(self, event):
        self.OnClick(self.FindWindowById(wx.ID_CLOSE))                

    def OnFieldsControl(self):

        d = {self.cbSuppliers:self.stSupplier.GetLabel(),
             self.cbCategories: self.stCategory.GetLabel(),
             self.txReference: self.stReference.GetLabel(),
             self.txDescription: self.stDescription.GetLabel()}
        
        return wx.GetApp().engine.fields_control(d)            
