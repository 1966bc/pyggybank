#!/usr/bin/env python
#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   pyggy.py
# authors:  1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   29/05/2015
# version:  0.4
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007                      
# license: wxWindows License 
#-----------------------------------------------------------------------------

"""
Lanch script of PyggyBank
"""


import wx
import sys
import os
import traceback


from engine import Engine
import frames.main


def ExceptionHook(exctype, value, trace):
    #trace = traceback.format_exc().splitlines()
    exc = traceback.format_exception(exctype, value, trace)
    ftrace = "".join(exc)
    app = wx.GetApp()
    if app:
        msg = "Houstonn\n we've had a problem\n%s"% ftrace
        wx.MessageBox(msg,wx.GetApp().GetAppName(),style = wx.ICON_ERROR|wx.OK)
    else:
        sys.stderr.write(ftrace)


class PyggyBank(wx.App):
    """The PyggyBank Object"""

    def OnInit(self):

        self.SetAppName("PyggyBank")

        self.engine = Engine()

        sys.excepthook = ExceptionHook
        
        #control app istance
        self.instance = wx.SingleInstanceChecker('client_lock',os.getcwd())
        if self.instance.IsAnotherRunning():
            msg = "Okay, Houston, we've had a problem here.\nAnother instance is running"
            wx.MessageBox(msg,wx.GetApp().GetAppName(),style = wx.ICON_ERROR|wx.OK)
            return False

        try:
            obj = frames.main.MainFrame()
            self.SetTopWindow(obj)
            obj.OnOpen()
            obj.Show()
            return True
        except:
            print sys.exc_info()[0]
            print sys.exc_info()[1]
            print sys.exc_info()[2]
            return False
            


    def OnExit(self):
        try:
            wx.GetApp().engine.con.close()
        except:
            pass
        for window in wx.GetTopLevelWindows():
            if window != self:  
                window.Destroy()
        wx.GetApp().Exit()
        return False
        
def main():

    wx.SetDefaultPyEncoding('latin-1')
    wx.Log.EnableLogging(False)
    app = PyggyBank(True,"log.txt")
    app.MainLoop()

if __name__ == '__main__':
    main()

