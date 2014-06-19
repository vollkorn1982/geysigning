#!/usr/bin/env python
import avahi, dbus
from dbus import DBusException
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gio
#from gi.repository import Gtk
from gi.repository import GObject

# Looks for _demo._tcp share

TYPE = '_demo._tcp'

def service_resolved(*args):
    print 'service resolved'
    print 'name:', args[2]
    print 'address:', args[7]
    print 'port:', args[8]

def print_error(*args):
    print 'error_handler'
    print args[0]


class AvahiBrowser:
    __gsignals__ = (
        (),
    )
    
    def __init__(self, loop=None, service='_demo._tcp'):
        self.service = service

        self.loop = loop or DBusGMainLoop()
        self.bus = dbus.SystemBus(mainloop=self.loop)
        
        self.server = dbus.Interface( self.bus.get_object(avahi.DBUS_NAME, '/'),
                'org.freedesktop.Avahi.Server')

        self.sbrowser = dbus.Interface(self.bus.get_object(avahi.DBUS_NAME,
          self.server.ServiceBrowserNew(avahi.IF_UNSPEC,
                avahi.PROTO_UNSPEC, TYPE, 'local', dbus.UInt32(0))),
          avahi.DBUS_INTERFACE_SERVICE_BROWSER)

        self.sbrowser.connect_to_signal("ItemNew", self.on_new_item)



    def on_new_item(self, interface, protocol, name, stype, domain, flags):
        print "Found service '%s' type '%s' domain '%s' " % (name, stype, domain)
    
        if flags & avahi.LOOKUP_RESULT_LOCAL:
                # local service, skip
                pass

        self.server.ResolveService(interface, protocol, name, stype,
            domain, avahi.PROTO_UNSPEC, dbus.UInt32(0),
            reply_handler=service_resolved, error_handler=print_error)

    def on_service_resolved(self, *args):
        '''called when the browser successfully found a service'''
        print 'service resolved'
        print 'name:', args[2]
        print 'address:', args[7]
        print 'port:', args[8]


    def on_error(self, *args):
        print 'error_handler'
        print args[0]


if __name__ == '__main__':
    ab = AvahiBrowser()
    GObject.MainLoop().run()
    
