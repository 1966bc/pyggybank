#!/usr/bin/env python3
#-----------------------------------------------------------------------------
# project:  pyggybank
# module:   pyggy.py
# authors:  1966bc
# mailto:   [giuseppe.costanzi@gmail.com]
# modify:   2026 - ported to Python 3 / wxPython 4 (Phoenix)
# version:  3.0
# copyright: GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007
# license: wxWindows License
#-----------------------------------------------------------------------------

"""
Launch script of PyggyBank
"""

import os
import sys
import traceback

import wx

from engine import Engine
from controller import Controller
from presenters import MainPresenter
import frames.main


def ExceptionHook(exctype, value, trace):
    exc = traceback.format_exception(exctype, value, trace)
    ftrace = "".join(exc)
    app = wx.GetApp()
    if app:
        try:
            app.engine.on_log("ExceptionHook", value, exctype, sys.modules[__name__])
        except Exception:
            pass
        msg = "Houston\n we've had a problem\n%s" % ftrace
        wx.MessageBox(msg, app.GetAppName(), style=wx.ICON_ERROR | wx.OK)
    else:
        sys.stderr.write(ftrace)


class PyggyBank(wx.App):
    """The PyggyBank Object"""

    def OnInit(self):

        self.SetAppName("PyggyBank")

        # dependency injection: engine (data source) -> Controller -> Presenter -> View
        self.engine = Engine()
        self.controller = Controller(self.engine)
        self.presenter = MainPresenter(self.controller)

        sys.excepthook = ExceptionHook

        # control app istance
        self.instance = wx.SingleInstanceChecker('client_lock', os.getcwd())
        if self.instance.IsAnotherRunning():
            msg = ("Okay, Houston, we've had a problem here.\n"
                   "Another instance is running")
            wx.MessageBox(msg, self.GetAppName(), style=wx.ICON_ERROR | wx.OK)
            return False

        try:
            obj = frames.main.MainFrame(self.presenter)
            self.presenter.set_view(obj)
            self.SetTopWindow(obj)
            obj.OnOpen()
            obj.Show()
            return True
        except Exception:
            traceback.print_exc()
            return False

    def OnExit(self):
        # called by wx after the main loop ends; just release resources.
        try:
            self.engine.close()
        except Exception:
            pass
        return 0


def main():

    wx.Log.EnableLogging(False)
    app = PyggyBank(redirect=False)
    app.MainLoop()


if __name__ == '__main__':
    main()
