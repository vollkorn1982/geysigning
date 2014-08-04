#!/usr/bin/python

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gtk
from MainWindow import MainWindow


DBusGMainLoop (set_as_default=True)
# setup the main window
window = MainWindow()
window.show_all()

Gtk.main()
