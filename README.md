# pyggybank
Python, wxPython, Sqlite, Reportlab, xlwt in action all in one

to run pyggybank you need:

python <= 2.6
wxPython version 2.8.10.1
SQLite version 3.7.3
Reportlab version 2.4-4

on my linux shell
bc@hal9000:~/pyggy$ python pyggy.py

Change log[2.3]
Hello everyone,
in this new version of Pyggy Bank I changed my developer strategy.
Now all architecture is center on wx.GetApp().
This allows us to avoid strange alchemies to pass variables and constants 
from a frame to the other in the whole project.
I have even tried to follow Editra Coding Guidelines to comment my code
Heavy refatoring of all scripts.

Comments welcome ... better if caustic!


How it work:
Pyggy Bank is a piggy bank so you can put or take money....;)
To do this you need to handle events so ,once the program is opened,
to add an event press the 'Add' button,fill all field in the frame and
choice which type of event want to have selecting the Flow check box
(Select = IN, deselect = OUT).Notice that you can check if the event 
is settled or no.
Press Save button.
To delete an event select it on the listbox and press Delete button.
To 'modify' an event select it and press Edit button, make your update
and press Save button.
In the main frame, you see all event and you can even filter these using 
left check_box that have 3 state.
You can filter events using the combo under the listbox.
Play with these to see the effects on the event's listbox.
To print press Print button, the created report show what you are looking at the 
main frame.
To manage categories and suppliers from the menu bar press Utilities/Categories
or Utilities/Suppliers.
In the status bar:
on left you see total in and out money refer to the applied filters 
on right you see your 'Wallet' refer to the applied filters 
As last thing, note that when you open the program calendars is set to the oldest dates
in the database.
Add in [2.2]
To lunch plot from the menu bar press Utilities/Plot.
To lunch xls export press the relative button.

thechnical note:
Pyggy Bank is a project that shows (or should show) a 'real world' application.
In this new version the entire program revolves around a class named "Engine" 
that you can see in engine.py module.
All  operation are delegated to this class that inherits methods and attributes by
DBMS class in dbms.py module to work with the database.
It's important that you familiarize yourself with class and instance variables, 
and how to modify these to make them visible to the various instances.
Fynally you can run engine.py and dbms.py alone, try and see whats happen

Developed on Debian Squeeze 6.0.10

I hope that this work may be of help to someone!
enjoy yourself



