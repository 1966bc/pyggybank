#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   main.py
# authors:  1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   29/05/2015
# version:  0.4
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007                      
# license: wxWindows License 
#-----------------------------------------------------------------------------

"""
This module provides the MainFrame class for pyggybank.
The MainFrame is Top Window of the project that contains
all the other components.
"""


import wx
import os
import sys
import datetime
import xlwt
import tempfile
import threading
from string import strip
import wx.lib.mixins.listctrl
from wx.lib.wordwrap import wordwrap
import  wx.lib.dialogs

import update_data
import filters
import reports.rpt_flows



ID_FLOW = wx.NewId()
ID_SETTLED = wx.NewId()
ID_ENABLED = wx.NewId()
ID_LIST = wx.NewId()
ID_COMBO = wx.NewId()
ID_OPTIONS = wx.NewId()



class Launcher(threading.Thread):
    def __init__(self,path,app):
        threading.Thread.__init__(self)
       
        self.path = path
        self.app = app
    def run(self):
        self.app.engine.open_file(self.path)

class MainFrame(wx.Frame, wx.lib.mixins.listctrl.ColumnSorterMixin,):
    """PyggyBank Main Window"""
    def __init__(self,):
        
        wx.Frame.__init__(self,
                          None,
                          wx.ID_ANY,
                          style = wx.GetApp().engine.frame_style(),
                          name  ='main')
        
        #set some frame attributes 
        self.SetIcon(wx.Icon(wx.GetApp().engine.icon,wx.BITMAP_TYPE_ICO))   
        self.SetTitle("%s %s" %(wx.GetApp().GetAppName(), wx.GetApp().engine.version))
        self.Bind(wx.EVT_CLOSE, self.OnExit)

        p = wx.Panel(self, -1)

        #menu
        menu_file = wx.Menu()
        menu_utilities = wx.Menu()
        menu_info = wx.Menu()

        item_exit = menu_file.Append(-1, "E&xit", "Quit PyggyBank!")
        self.Bind(wx.EVT_MENU, self.OnExit, item_exit)

        item_readme = menu_utilities.Append(-1, "Read me", "read me!")
        self.Bind(wx.EVT_MENU, self.OnRead, item_readme)
        item_category = menu_utilities.Append(-1, "Categories", "update categories!")
        self.Bind(wx.EVT_MENU, self.menuCategories, item_category)
        item_supplier = menu_utilities.Append(-1, "Suppliers", "update suppliers!")
        self.Bind(wx.EVT_MENU, self.menuSuppliers, item_supplier)
        item_log = menu_utilities.Append(-1, "L&og file", "log info!")
        self.Bind(wx.EVT_MENU, self.OnOpenLogFile, item_log)

        
        item_info = menu_info.Append(-1, "A&bout", "developer info!")
        self.Bind(wx.EVT_MENU, self.OnAbout, item_info)
        item_licence = menu_info.Append(-1, "C&opyleft", "copyleft info!")
        self.Bind(wx.EVT_MENU, self.OnLicence, item_licence)
        
        menubar = wx.MenuBar()
        menubar.Append(menu_file, "&File")
        menubar.Append(menu_utilities, "&Utilities")
        menubar.Append(menu_info, "?")
        self.SetMenuBar(menubar)

        #statusbar
        self.StatusBar = self.CreateStatusBar(1,wx.ST_SIZEGRIP)
        self.StatusBar.SetFieldsCount(2)
        self.StatusBar.SetStatusWidths([-8, -2])
        self.StatusBar.SetStatusText('Total:0',1)

        #widgets
        self.calStartDate = wx.DatePickerCtrl(p,style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        self.calStartDate.SetToolTipString('start date!')
        self.calStartDate.Bind(wx.EVT_DATE_CHANGED, self.on_date_changed)
        
       
        self.cbFilter = wx.ComboBox(p,ID_COMBO,
                                    size=(wx.GetApp().engine.get_font() * 20,-1),
                                    style = wx.CB_READONLY|wx.CB_DROPDOWN)
        self.cbFilter.Bind(wx.EVT_COMBOBOX, self.OnItemSelected)


        self.stEvents = wx.StaticText(p, -1, 'Records')
        self.stEvents.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.BOLD))
        self.lstEvents = wx.ListCtrl(p,ID_LIST,
                                     style = wx.LC_REPORT|wx.LC_HRULES|wx.LC_VRULES,
                                     size=(wx.GetApp().engine.get_font() * 70,
                                           wx.GetApp().engine.get_font() * 30),)
        
        self.lstEvents.SetToolTipString('Double click to edit!')
        self.lstEvents.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.lstEvents.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        self.lstEvents.InsertColumn(0, 'id', width = 0)
        self.lstEvents.InsertColumn(1, 'Flow',  wx.LIST_FORMAT_CENTER,width=wx.GetApp().engine.get_font() * 5)
        self.lstEvents.InsertColumn(2, 'Suppliers', wx.LIST_FORMAT_LEFT, width=wx.GetApp().engine.get_font() * 10)
        self.lstEvents.InsertColumn(3, 'Category', wx.LIST_FORMAT_LEFT, width=wx.GetApp().engine.get_font() * 10)
        self.lstEvents.InsertColumn(4, 'Settled', wx.LIST_FORMAT_CENTER,width=wx.GetApp().engine.get_font() * 10)
        self.lstEvents.InsertColumn(5, 'Reference', wx.LIST_FORMAT_CENTER,width=wx.GetApp().engine.get_font() * 10)
        self.lstEvents.InsertColumn(6, 'Currency',  wx.LIST_FORMAT_CENTER,width=wx.GetApp().engine.get_font() * 10)
        self.lstEvents.InsertColumn(7, 'Issued', wx.LIST_FORMAT_CENTER,width=wx.GetApp().engine.get_font() * 10)

        #ListCtrl columns sort
        self.itemDataMap = {}
        il = wx.ImageList(16,16, True)
        self.up = il.AddWithColourMask(wx.Bitmap(wx.GetApp().engine.up_icon, wx.BITMAP_TYPE_BMP), "blue")
        self.dn = il.AddWithColourMask(wx.Bitmap(wx.GetApp().engine.down_icon, wx.BITMAP_TYPE_BMP), "blue")
        wx.lib.mixins.listctrl.ColumnSorterMixin.__init__(self,8)
        self.lstEvents.AssignImageList(il, wx.IMAGE_LIST_SMALL)


        sbb = wx.StaticBox(p,wx.ID_ANY)

        bts = [(wx.ID_REFRESH,'&Refresh','reload data'),
               (wx.ID_ADD,'&Add ','add record!'),
               (wx.ID_EDIT,'&Edit','edit selected record'),
               (wx.ID_DELETE,'&Delete','delete selected record'),
               (wx.ID_PREVIEW,'&Preview','print preview'),
               (wx.ID_FILE,'&Xls','export data in xls'),
               (wx.ID_CLOSE,'&Close','close app'),]

        
        for (id, label, help_text) in bts:
             b = wx.Button(p, id, label,)
             b.SetToolTipString(help_text)
             b.Bind(wx.EVT_BUTTON, self.OnClick)


        cks = [(ID_FLOW, "FLow"),
               (ID_SETTLED, "Settled"),
               (ID_ENABLED, "Enabled"),]

        for (id, label,) in cks:
            c = wx.CheckBox(p, id, label,style=(wx.CHK_3STATE|wx.CHK_ALLOW_3RD_STATE_FOR_USER))
            c.Bind(wx.EVT_CHECKBOX, self.OnClick)

        sbo = wx.StaticBox(p,wx.ID_ANY)
        ops = ['None','Categories','Suppliers']
        self.rbOptions = wx.RadioBox(p, ID_OPTIONS,"Combo filter",
                                     wx.DefaultPosition,wx.DefaultSize,
                                     ops,3, wx.RA_SPECIFY_COLS | wx.NO_BORDER)
        self.rbOptions.Bind(wx.EVT_RADIOBOX, self.OnClick,)            

        #sizers
        s0 = wx.BoxSizer(wx.HORIZONTAL)
        s1 = wx.BoxSizer(wx.VERTICAL)
        s2 = wx.StaticBoxSizer(sbb,wx.VERTICAL)
        s3 = wx.StaticBoxSizer(sbo,wx.VERTICAL)


        w = (self.rbOptions,self.cbFilter)
        for i in w:
            s3.Add(i,0,wx.EXPAND|wx.ALL)
        
        w = (self.stEvents,self.lstEvents,s3,)
        for i in w:
            s1.Add(i, 0,wx.EXPAND|wx.ALL, 2)
            
        for i in p.GetChildren():
            if type(i) in(wx.DatePickerCtrl,wx.Button,wx.CheckBox,):
                s2.Add(i,0,wx.EXPAND|wx.ALL, 5)

        w = (s1,s2,)
        for i in w:
             s0.Add(i, 0,wx.ALL, 10)

        p.SetSizer(s0)
        s0.Fit(self)
        s0.SetSizeHints(self)
            
    
    def OnOpen(self):
        
        self.OnClick(self.FindWindowById(wx.ID_REFRESH))

    def OnClick(self,evt):

        """Every click is management in this function
           
            @evt : such as wx.ID_REFRESH,wx.ID_ADD and so on
            @return: it depends by event that is called
            @rtype: it depends by event that is called
        """

        if evt.GetId() == wx.ID_REFRESH:


            sql = "SELECT issued AS issued FROM events ORDER BY issued ASC LIMIT 1"
            rs =  wx.GetApp().engine.read(False, sql, ())

            self.calStartDate.SetValue(wx.GetApp().engine.set_calendar_date(rs[0]))
            self.lst_transactions = None
            self.get_args()

        elif evt.GetId() == wx.ID_ADD:
           
            obj = update_data.Dialog(parent = self)
            obj.OnOpen()
            obj.Center()
            obj.ShowModal()
             
        elif evt.GetId() == wx.ID_EDIT:

            index = self.lstEvents.GetFirstSelected()

            if index != -1:
                obj = update_data.Dialog(parent = self)
                obj.OnOpen(self.selected_event)
                obj.Center()
                obj.ShowModal()
            else:
                wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)
            
        elif evt.GetId() == wx.ID_DELETE:

            index = self.lstEvents.GetFirstSelected()

            if index != -1:
                
                msg = ("Confirm operation:\nDelete transaction :\n%s"
                            % self.selected_event[5].encode("latin1"))
               
                if (wx.GetApp().engine.ask(msg) == wx.ID_YES):

                    wx.GetApp().engine.write(wx.GetApp().engine.dict_queries['delete_transaction'],
                                             (self.selected_event[0],))
                    self.get_args()
                else:
                    wx.GetApp().engine.answer_info(wx.GetApp().engine.abort_by_user)
            else:
                    wx.GetApp().engine.answer_info(wx.GetApp().engine.no_select)                    
                
        elif evt.GetId() == ID_OPTIONS:
            
            if self.rbOptions.GetSelection() == 0:
                rs = []
                self.get_args()
            else:
                if self.rbOptions.GetSelection() == 1:
                    rs = wx.GetApp().engine.read(True, wx.GetApp().engine.dict_queries['cbo_categories'])
                elif self.rbOptions.GetSelection() == 2:
                    rs = wx.GetApp().engine.read(True, wx.GetApp().engine.dict_queries['cbo_suppliers'])

            self.set_values(ID_COMBO,rs)
                                        
        elif evt.GetId() in (ID_FLOW, ID_SETTLED, ID_ENABLED):
            self.get_args()

        elif evt.GetId() == wx.ID_PREVIEW:
            self.get_values((wx.ID_PREVIEW, True, wx.GetApp().engine.dict_queries['report'], self.args))

        elif evt.GetId() == wx.ID_FILE:

            #build excel file

            b = wx.GetApp().engine.busy(self)
            path = tempfile.mktemp (".xls")
            obj = xlwt.Workbook()
            ws = obj.add_sheet(wx.GetApp().GetAppName(), cell_overwrite_ok=True)
            row = 0
            #indexing is zero based, row then column
            ws.write(row,0,'FLOW')
            ws.write(row,1,'SETTLED')
            ws.write(row,2,'SUPPLIER')     
            ws.write(row,3,'CATEGORY')
            ws.write(row,4,'REFERENCE')
            ws.write(row,5,'ISSUED')
            ws.write(row,6,'IN')
            ws.write(row,7,'OUT')
               
            row +=1
                
            for i in self.rs:
                rows = []
                
                ws.write(row,0,int(i[1]),)
                ws.write(row,1,int(i[4]),)
                ws.write(row,2,str(i[2]),wx.GetApp().engine.xls_style_font(True,False,'Times New Roman'))
                ws.write(row,3,str(i[3]),wx.GetApp().engine.xls_style_font(True,False,'Times New Roman'))
                ws.write(row,4,str(i[5]),)
                ws.write(row,5,str(i[7]),)
                if i[1] !=0:
                    ws.write(row,6,float(i[6]),wx.GetApp().engine.xls_bg_colour("green"))
                else:
                    ws.write(row,7,float(i[6]),wx.GetApp().engine.xls_bg_colour("yellow"))
                
                row +=1
                       
            #some formula...                         
            f = "SUM(G%s:G%s)"%(2,row)
            ws.write(row, 6, xlwt.Formula(f),wx.GetApp().engine.xls_style_font(True,False,'Times New Roman'))
            f = "SUM(H%s:H%s)"%(2,row)
            ws.write(row, 7, xlwt.Formula(f),wx.GetApp().engine.xls_style_font(True,False,'Times New Roman'))
            f = "(G%s-H%s)"%(row+1,row+1)
            ws.write(row, 8, xlwt.Formula(f),wx.GetApp().engine.xls_style_font(True,True,'Times New Roman'))
                       
            obj.save(path)
            Launcher(path, wx.GetApp()).start()
            b = None

        elif evt.GetId() == wx.ID_CLOSE:
            self.OnExit(self)
    
    def on_date_changed(self, evt):
        self.get_args()

    def OnItemSelected(self, evt):

        if evt.GetId() == ID_LIST:
            index = self.lstEvents.GetFirstSelected()
            if index != -1:
                pk = int(evt.GetItem().GetText())
                #make a dict for the selected row
                self.selected_event = wx.GetApp().engine.get_selected('events', 'event_id', pk)

        elif evt.GetId() == ID_COMBO:
            self.get_args()
            
    def OnItemActivated(self, evt):
        self.OnClick(self.FindWindowById(wx.ID_EDIT))

    def get_args(self,):

        """get arguments to populate ListCtrl
           call self.get_values

        """
        
        self.args = (self.get_state(self.FindWindowById(ID_FLOW).Get3StateValue()),
                     self.get_state(self.FindWindowById(ID_SETTLED).Get3StateValue()),
                     self.get_state(self.FindWindowById(ID_ENABLED).Get3StateValue()),
                     self.get_combo_filter()[0],self.get_combo_filter()[1],
                     wx.GetApp().engine.get_calendar_date(self.calStartDate.GetValue()))

        self.get_values((ID_LIST, True, wx.GetApp().engine.dict_queries['flows'], self.args))

          
    def get_values(self, args):
        """This function make callback to database and return a recordeset
           
            @param name: args
                         args[0]: widget id,
                         args[1]: True/False = fetchall/fetchone
                         args[2]: sql statement
                         args[3]: sql arguments
            @return: recordset
            @rtype: tuple
        """

        rs = wx.GetApp().engine.read(args[1], args[2], args[3])
        
        if args[0] == wx.ID_PREVIEW:
           
            paper = reports.rpt_flows.GeneratePDF(rs,self.args,wx.GetApp())
            paper.create_doc()
        else:
            self.set_values(args[0],rs)

    def set_values(self,which,rs):
        
        if which == ID_LIST:
            self.rs = rs
            self.wallet_in = 0
            self.wallet_out = 0
            self.lstEvents.DeleteAllItems()
            self.stEvents.SetLabel("Events %s"%(len(rs)))
            
            for i in rs:
                index = self.lstEvents.InsertStringItem(sys.maxint,str(i[0]))
                self.lstEvents.SetStringItem(index, 1,str(i[1]))
                self.lstEvents.SetStringItem(index, 2, (strip(str(i[2].encode("latin-1")))))
                self.lstEvents.SetStringItem(index, 3, (strip(str(i[3].encode("latin-1")))))
                self.lstEvents.SetStringItem(index, 4, str(i[4]))
                self.lstEvents.SetStringItem(index, 5, str(i[5]))
                #if flow = 1 add to wallet
                if i[1]==True:
                    self.wallet_in += i[6]
                else:
                    self.wallet_out += i[6]
                self.lstEvents.SetStringItem(index, 6, (str(i[6])))
                self.lstEvents.SetStringItem(index, 7, (str(i[7])))

                self.lstEvents.SetItemData(index, index)
                self.itemDataMap[index]=(i[0],i[1],i[2],i[3],i[4],i[5],i[6],i[7])
            #keep a reference to selected row
            if self.lst_transactions is not None:
                self.lstEvents.Select(self.lst_transactions ,1)
                self.lstEvents.EnsureVisible(self.lst_transactions)
                
            msg = 'Wallet: %s' %(self.wallet_in - self.wallet_out)
            self.StatusBar.SetStatusText(msg,1)
            msg = 'In: %s Out: %s' %(self.wallet_in ,self.wallet_out)
            self.StatusBar.SetStatusText(msg,0)                

        elif which == ID_COMBO:
            self.cbFilter.SetValue('')
            self.cbFilter.Clear()
            if rs:
                for i in rs:
                    pk = int(i[0])
                    data = (strip(str(i[1].encode("latin-1"))))
                    self.cbFilter.Append(data, (pk, data))
           
            
    def get_state(self,state):
        """return the correct value by Get3StateValue"""
        if state == 0:
            state = '%'
        elif state == 1:
            state = 1
        elif state == 2:
            state = 0

        return  state

    def get_combo_filter(self):
        """Which combo data are selected?..if are
           
            @return: pk of supppliers or categories
            @rtype: int,str
        """
        
        if self.rbOptions.GetSelection() == 0:
            supplier_id = '%'
            category_id = '%'
        else:
            s = int(self.cbFilter.GetSelection())
            data = self.cbFilter.GetClientData(s)
            combo_id = (int(data[0]))
        
            if self.rbOptions.GetSelection() == 1:
                supplier_id = '%'
                category_id = combo_id
            elif self.rbOptions.GetSelection() == 2:
                supplier_id = combo_id
                category_id = '%'
        
        return    supplier_id, category_id              
               
    
    def menuCategories(self,evt):

        #checks if there's already an instance
        if wx.GetApp().engine.match_instance('filters')== True:return

        obj = filters.Frame(parent = self)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen('categories', 'category_id')
        obj.Show()
        obj.Center() 
       
    def menuSuppliers(self,evt):

        #checks if there's already an instance
        if wx.GetApp().engine.match_instance('filters')== True:return

        obj = filters.Frame(parent = self)
        wx.GetApp().engine.get_instance(obj)
        obj.OnOpen('suppliers', 'supplier_id')
        obj.Show()
        obj.Center()

    def GetListCtrl(self):
        return self.lstEvents

    def GetSortImages(self):
        return (self.dn, self.up)        

    def OnRead(self,evt):
        try:
            f = open('readme', "r")
            msg = f.read()
            f.close()
        except IOError:
            msg = "Log file doesn't exist!"
            wx.MessageBox(msg, wx.GetApp().GetAppName(), wx.OK|wx.ICON_INFORMATION)
            return

        dlg = wx.lib.dialogs.ScrolledMessageDialog(self,msg,"Read me")
        dlg.ShowModal()

    def OnAbout(self,evt):
        
        info = wx.AboutDialogInfo()
        info.Name = wx.GetApp().engine.title
        info.Version = wx.GetApp().engine.version
        info.Copyright = wx.GetApp().engine.copyleft
        info.Description = wordwrap(wx.GetApp().engine.description, 350, wx.ClientDC(self))
        info.WebSite = (wx.GetApp().engine.web,wx.GetApp().engine.web)
        info.Developers = [wx.GetApp().engine.developer]

        wx.AboutBox(info)
        
    def OnLicence(self,evt):
        
        f = open(os.path.join(os.getcwd(),"copying"), "r")
        msg = f.read()
        f.close()
        dlg = wx.lib.dialogs.ScrolledMessageDialog(self,msg,'Copyleft' )
        dlg.ShowModal()

    def OnOpenLogFile(self,evt):
        try:
            f = open(wx.GetApp().engine.log, "r")
            msg = f.read()
            f.close()
        except IOError:
            msg = "Log file doesn't exist!"
            wx.MessageBox(msg, wx.GetApp().GetAppName(), wx.OK|wx.ICON_INFORMATION)
            return

        dlg = wx.lib.dialogs.ScrolledMessageDialog(self,msg,"Log file")
        dlg.ShowModal()

   
    def OnExit(self,evt):
        msg = "Quit me?"
        ret = wx.MessageBox(msg,wx.GetApp().GetAppName(),
                            wx.YES_NO|wx.ICON_QUESTION|wx.CENTRE|wx.NO_DEFAULT)
        if ret == 2:
            wx.GetApp().OnExit()
