#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   engine.py
# authors:  giuseppe costanzi aka 1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   29/05/2015
# version:  0.4
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007                      
# license: wxWindows License 
#-----------------------------------------------------------------------------

"""
This file contains variables that can be used in all modules of the the project.
Its purpose is to create a globally accessible access point for all common
variables in the project.

"""

import wx
import os
import xlwt
import datetime
import subprocess


from dbms import DBMS


class Engine(DBMS):
    
    def __init__(self,):
        super(Engine, self).__init__()

        """Initialize variables used in app"""

        self.title = "PyggyBank"
        self.icon = os.path.join(os.getcwd(),"icons/app.ico")
        self.logo = os.path.join(os.getcwd(),"images/report.gif")
        self.dict_instances = {}
        self.disable = (211,211,211)
        self.blue = (0,0, 139)
        self.log = ""
        self.up_icon = os.path.join(os.getcwd(),"icons/up.bmp")
        self.down_icon = os.path.join(os.getcwd(),"icons/down.bmp")
        self.no_selected = "Attention!\nNo record selected!"
        self.mandatory = "Attention!\nField %s is mandatory!"
        self.delete = "Delete data?"
        self.save = "Save data?"
        self.abort = "Operation aborted!"
        self.buttons = [(wx.ID_SAVE,"&Save","Save data"),
                        (wx.ID_CLOSE,"&Close","close window"),
                        (wx.ID_DELETE,'&Delete',"delete data!"),]
   
        self.version = '2.3'
        self.copyleft = "GNU GPL Version 3, 29 June 2007"
        self.developer = "hal9000\n1966bc mailto[giuseppe.costanzi@gmail.com] \nLocation:\nMilk Galaxy\nSolar System\nThird Planet (Earth)\nItaly\nRome"
        self.description = "welcome on %s"% self.title
        self.web = "www.1966bc.wordpress.com"

    def __str__(self):
        return "class: %s\napp title: %s\nversion: %s" % (self.__class__.__name__,
                                                          self.title,
                                                          self.version)    



    def get_calendar_date(self,my_calendar,get_time = None):
        """this function recive date from wx.DatePickerCtrl.GetValue()
           and return a  datetime to store in sqlite database
           datetime or timestamp field

           adapted from:
           http://www.blog.pythonlibrary.org/2014/08/27/wxpython-converting-wx-datetime-python-datetime/

           
           
            @my_calendar: wx.DatePickerCtrl.GetValue()
            @get_time : if we want use time
            @return: a datetime
            @rtype: datetime
        """
        

        now =   datetime.datetime.now()

        s = "%s%s%s%s%s%s" %(my_calendar.GetYear(),
                             my_calendar.GetMonth()+1,
                             my_calendar.GetDay(),
                             now.hour,
                             now.minute,
                             now.second)

        if get_time:
            return datetime.datetime.strptime(s,"%Y%m%d%H%M%S")
        else:
            return datetime.datetime(my_calendar.GetYear(),
                                     my_calendar.GetMonth()+1,
                                     my_calendar.GetDay())
                 
            
    def set_calendar_date(self,my_date):
        """this function set date on wx.DatePickerCtrl
            reciving a datetime from an sqlite
            recordset
            adapted from:
            http://www.blog.pythonlibrary.org/2014/08/27/wxpython-converting-wx-datetime-python-datetime/
           
            @my_date: a datetime data
            @return: a datetime
            @rtype: datetime for wxpython wx.DatePickerCtrl
        """
        
        if type(my_date) == unicode:
            try:
                my_date = datetime.datetime.strptime(my_date, "%Y-%m-%d")
               
            except ValueError, v:
                ulr = len(v.args[0].partition('unconverted data remains: ')[2])
                if ulr:
                    my_date = datetime.datetime.strptime(my_date[:-ulr], "%Y-%m-%d")
                else:
                    raise v
           
        return wx.DateTimeFromDMY(my_date.day, my_date.month-1, my_date.year)

    
    def xls_bg_colour(self,colour):
        """this function get a color name and return
           a pattern color for format xls data sheets
           
        """
        dict_colour = {"green":3,
                       "red":2,
                       "white":1,
                       "yellow":5,
                       "gray":22,
                       "blue":4,"magenta":6,"cyan":7}
        bg_colour = xlwt.XFStyle()
        p = xlwt.Pattern()
        p.pattern = xlwt.Pattern.SOLID_PATTERN
        p.pattern_fore_colour = dict_colour[colour]
        bg_colour.pattern = p
        return bg_colour

    def xls_style_font(self,is_bold,is_underline,font_name):
        """this function is used to format font on xls datasheets

           @is_bold: True/False
           @is_underline: True/False
           @font_name: font to use
           @return: xlwt.XFStyle()
           @rtype: unknow...
           
        """

        style = xlwt.XFStyle()
        # Create a font to use with the style
        font = xlwt.Font()
        font.name = font_name
        font.bold = is_bold
        font.underline = is_underline
        # Set the style's font to this new one you set up
        style.font = font
        return style

    def open_file(self,path):

        if os.path.exists(path):
            if os.name == 'posix':
                subprocess.call(["xdg-open", path])
                #os.popen("evince %s" % path)
            else:
                os.startfile(path)
        else:
            wx.MessageBox(self.report_no_found,
                          self.title,
                          wx.OK|wx.ICON_INFORMATION)

                      
    def get_instance(self,which):
        """this function is used to load
           in the dict_instances the instances
           of opened frames

        """
        self.dict_instances[which.GetName()]= which
        self.show_instances(False)

    def del_instance(self,which):
        """this function is used to delete
           from the dict_instances the instances
           of closed frames

        """
        del self.dict_instances[which.GetName()]
        self.show_instances(False)

    def match_instance(self,which):
        """this function is used to control
           if a frame is open

        """

        if self.dict_instances.has_key(which):
            return True
        else:
            return False

    def show_instances(self,enable):
        if enable:
            for k,v in self.dict_instances.iteritems():
                print k
            print '-'*30


    def explode_dict(self,dict):
        #for debug...
        for k, v in dict.iteritems():
                print k,v

    def busy(self,caller):
        return wx.BusyInfo("Attendere prego!\ncaricamento dati in corso...",caller)

    def ask(self, msg ):
        return (wx.MessageDialog(None,msg,self.title,wx.YES_NO|wx.ICON_QUESTION)).ShowModal()
         
    def answer_info(self, msg ):
        return wx.MessageBox(msg,self.title,wx.OK|wx.ICON_INFORMATION)

    def fields_control(self,dict):
        for k, v in dict.items():
            if len(k.GetValue())==0:
                self.answer_info(self.field_mandatory%(v))
                k.SetFocus()
                return 0

    def get_font(self):
        try:    # get system font width
            fw = wx.SystemSettings_GetFont(wx.SYS_DEFAULT_GUI_FONT).GetPointSize()+1
        except:
            fw = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT).GetPointSize()+1
        return fw

    def frame_style(self):
        return (wx.DEFAULT_FRAME_STYLE^
               (wx.RESIZE_BORDER|wx.MAXIMIZE_BOX)|
               wx.FRAME_FLOAT_ON_PARENT)


def main():

    foo = Engine()
    print foo
    print foo.con
 
    sql = "SELECT name FROM sqlite_master WHERE type = 'table'"
    rs = foo.read(True, sql)
    if rs:
        for i in enumerate(rs):
            print i

    
  
         
if __name__ == "__main__":
    main()
