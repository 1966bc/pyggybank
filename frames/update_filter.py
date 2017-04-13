#-----------------------------------------------------------------------------
# project:  pyggy bank
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   28/05/2015
# version:  0.4
# description: update categories and suppliers data
#-----------------------------------------------------------------------------

import wx
from string import strip


class Dialog(wx.Dialog,):
    def __init__(self,parent):
        wx.Dialog.__init__(self,parent,wx.ID_ANY,name = 'dlg_update_filter')
        

        #set some frame properties
        self.SetIcon(wx.Icon(wx.GetApp().engine.icon,wx.BITMAP_TYPE_ICO)) 
        p = wx.Panel(self, -1)
      

        #widgets
        self.stFilter = wx.StaticText(p, wx.ID_ANY, 'Filter')
        self.txFilter = wx.TextCtrl(p, wx.ID_ANY, "",size = (wx.GetApp().engine.get_font() * 20, -1))
        self.txFilter.SetMaxLength(16)
        message  = 'Max chars 16'
        self.txFilter.SetToolTipString(message)
       

        self.stEnable = wx.StaticText(p,wx.ID_ANY, 'Enable')
        self.ckEnable = wx.CheckBox(p, wx.ID_ANY,)

        sbb = wx.StaticBox(p,wx.ID_ANY,"")

        bts = [(wx.ID_SAVE,'&Save','save data!'),
              (wx.ID_CLOSE,'&Close','close'),]
        for (id, label, help_text) in bts:
            b = wx.Button(p, id, label,)
            b.SetToolTipString(help_text)
            b.Bind(wx.EVT_BUTTON, self.OnClick)

        #sizers
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.FlexGridSizer(cols = 2, hgap = 5, vgap = 5)
        s2 = wx.StaticBoxSizer(sbb,wx.VERTICAL)

        w =  (self.stFilter,self.txFilter,
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

    #event hanlding
    def OnOpen(self, table, pk, dict_record = None):

        self.table = table
        self.pk = pk
        
        if dict_record is not None:

            self.insert_mode = False
            self.dict_record = dict_record
            message = ("Update %s" % self.dict_record[1].encode("latin-1"))
            self.SetTitle (message)
            self.txFilter.SetValue(str(self.dict_record[1].encode("latin-1")))
            if self.dict_record[2] == 1:
                self.ckEnable.SetValue(True)
            else:
                self.ckEnable.SetValue(False)

        else:
            self.insert_mode = True
            message = 'Insert new item in %s' % self.table
            self.SetTitle (message)
            self.ckEnable.SetValue(True)
            

    def OnClick(self,event):


        if event.GetId() == wx.ID_SAVE:

            if self.OnFieldsControl()==0:return

            if (wx.GetApp().engine.ask("Save data?") == wx.ID_YES):

                
                if self.insert_mode == False:
              
                    args = (strip(str(self.txFilter.GetValue().encode("utf-8"))),
                            self.ckEnable.GetValue(),
                            self.dict_record[0])

                    sql = wx.GetApp().engine.get_update_sql(self.table,wx.GetApp().engine.get_pk_name(self.table))
           

                elif self.insert_mode == True:

                     args = (strip(str(self.txFilter.GetValue().encode("utf-8"))),
                             self.ckEnable.GetValue(),)

                     sql = wx.GetApp().engine.get_insert_sql(self.table, len(args))

        
                wx.GetApp().engine.write(sql, args)
                self.GetParent().OnOpen(self.table,self.pk)
                self.OnClick(self.FindWindowById(wx.ID_CLOSE))

            else:
                wx.GetApp().engine.answer_info("Operation abort!")
                self.txFilter.SetFocus()

        elif event.GetId() == wx.ID_CLOSE:
            self.Destroy()

    def OnExit(self, event):
        self.OnClick(self.FindWindowById(wx.ID_CLOSE))                

    def OnFieldsControl(self):

        d = {self.txFilter:self.stFilter.GetLabel()}
        return wx.GetApp().engine.fields_control(d)
        

        
