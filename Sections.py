#!/usr/bin/env python

import logging
from urlparse import ParseResult

import requests
from requests.exceptions import ConnectionError

from gi.repository import GLib
from gi.repository import Gtk
from SignPages import KeysPage, SelectedKeyPage

FINGERPRINT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeySignSection(Gtk.VBox):

    def __init__(self):
        super(KeySignSection, self).__init__()

        # create notebook container
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(KeysPage(), None)
        self.notebook.append_page(SelectedKeyPage(), None)

        #TODO make notebook change pages according to current step

        self.notebook.set_show_tabs(True) # TODO

        # create progress bar
        self.progressBar = Gtk.ProgressBar()
        self.progressBar.set_text("Step 1: Choose a key and click on 'Next' button.")
        self.progressBar.set_show_text(True)
        self.progressBar.set_fraction(0.50) #TODO : Fix Hardcoded

        # create proceed button
        self.proceedButton = Gtk.Button('Next')
        self.proceedButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.BUTTON))
        self.proceedButton.set_always_show_image(True)

        hBox = Gtk.HBox()
        hBox.pack_start(self.progressBar, True, True, 0)
        hBox.pack_start(self.proceedButton, False, False, 0)

        self.pack_start(self.notebook, True, True, 0)
        self.pack_start(hBox, False, False, 0)


class GetKeySection(Gtk.Box):

    def __init__(self, app):
        '''Initialises the section which lets the user
        start signing a key.
        
        ``app'' should be the "app" itself. The place
        which holds global app data, especially the discovered
        clients on the network.
        '''
        super(GetKeySection, self).__init__()
        
        self.app = app
        self.log = logging.getLogger()

        # create main container
        container = Gtk.VBox(spacing=10)

        # create fingerprint entry
        self.fingerprintEntryLabel = Gtk.Label()
        self.fingerprintEntryLabel.set_markup('<span size="15000">' + 'Type fingerprint'+ '</span>')
        self.fingerprintEntryLabel.set_margin_top(10)

        self.fingerprintEntry = Gtk.Entry()

        container.pack_start(self.fingerprintEntryLabel, False, False, 0)
        container.pack_start(self.fingerprintEntry, False, False, 0)

        # create scanner frame
        self.scanFrameLabel = Gtk.Label()
        self.scanFrameLabel.set_markup('<span size="15000">' + '... or scan QR code'+ '</span>')

        self.scanFrame = Gtk.Frame(label='QR Scanner')

        container.pack_start(self.scanFrameLabel, False, False, 0)
        container.pack_start(self.scanFrame, True, True, 0)

        # create save key button
        self.saveButton = Gtk.Button('Save key')
        self.saveButton.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_SAVE, Gtk.IconSize.BUTTON))
        self.saveButton.set_always_show_image(True)
        self.saveButton.set_margin_bottom(10)
        self.saveButton.connect('clicked', self.on_button_clicked)

        container.pack_start(self.saveButton, False, False, 0)

        self.pack_start(container, True, False, 0)



    def download_key_http(self, address, port):
        url = ParseResult(
            scheme='http',
            # This seems to work well enough with both IPv6 and IPv4
            netloc="[[%s]]:%d" % (address, port),
            path='/',
            params='',
            query='',
            fragment='')
        return requests.get(url.geturl()).text
        

    def try_download_keys(self, clients):
        for client in clients:
            self.log.debug("Getting key from client %s",
                           client)
            name, address, port = client
            try:
                keydata = self.download_key_http(address, port)
                yield keydata
            except ConnectionError, e:
                # We probably have other errors to catch
                self.log.exception("While downloading key from %s %i",
                                   address, port)


    def obtain_key_async(self, fingerprint, callback=None, data=None, error_cb=None):
        other_clients = self.app.discovered_services
        self.log.debug("The clients found on the network: %s", other_clients)
        for keydata in self.try_download_keys(other_clients):
            # check whether the keydata makes sense,
            # i.e. compute the fingerprint from the obtained key and
            # compare it with the intended key
            # We skip it for now...
            is_valid = True
            if is_valid:
                break
        else:
            self.log.error("Could not find fingerprint %s " +\
                           " with the avaiable clients (%s)",
                           fingerprint, other_clients)
            self.log.debug("Calling error callback, if available: %s",
                           error_cb)
            if error_cb:
                GLib.idle_add(error_cb, data)
            # I dislike returning here
            return

        GLib.idle_add(callback, keydata, data)
        # I wanted to return the idle_add result, maybe for
        # someone to cancel that.  But if this function here is
        # itself added via idle_add, then idle_add will keep
        # adding this function to the loop until this function
        # returns False...
        return False


    def on_button_clicked(self, button):
        # We probably want to rework pretty much everything here
        # and show a separate page in the notebook or so
        statuslabel = self.scanFrameLabel
        fingerprint = "x"
        statuslabel.set_markup("downloading key with fingerprint %s" % fingerprint)
        err = lambda x: statuslabel.set_markup("Error downloading")
        # Only simulating the download now...
        GLib.idle_add(self.obtain_key_async, fingerprint,
            self.received_key, fingerprint,
            # Does not work as expected, probably because idle_add swallows
            #error_cb=err)
            err)
        print "clicked"


    def received_key(self, keydata, *data):
        print "Received key %s", keydata
