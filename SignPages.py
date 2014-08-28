#!/usr/bin/env python
import logging
import sys

try:
    from gi.repository import Gtk, GdkPixbuf
    from monkeysign.gpg import Keyring
except ImportError, e:
    print "A required python module is missing!\n%s" % (e,)
    sys.exit()

from datetime import datetime

FINGERPRINT_DEFAULT = 'F628 D3A3 9156 4304 3113\nA5E2 1CB9 C760 BC66 DFE1'

class KeysPage(Gtk.VBox):

    def __init__(self, keySection):
        super(KeysPage, self).__init__()

        # pass a reference to KeySignSection in order to access its widgets
        self.keySection = keySection

        # set up the list store to be filled up with user's gpg keys
        self.store = Gtk.ListStore(str, str, str)

        # FIXME: this should be moved to KeySignSection
        self.keyring = Keyring() # the user's keyring

        self.keysDict = {}

        # FIXME: this should be a callback function to update the display
        # when a key is changed/deleted
        for key in self.keyring.get_keys(None, True, False).values():
            if key.invalid or key.disabled or key.expired or key.revoked:
                continue

            uidslist = key.uidslist #UIDs: Real Name (Comment) <email@address>
            keyid = str(key.keyid()) # the key's short id

            if not keyid in self.keysDict:
                self.keysDict[keyid] = key

            for e in uidslist:
                uid = str(e.uid)
                # remove the comment from UID (if it exists)
                com_start = uid.find('(')
                if com_start != -1:
                    com_end = uid.find(')')
                    uid = uid[:com_start].strip() + uid[com_end+1:].strip()

                # split into user's name and email
                tokens = uid.split('<')
                name = tokens[0].strip()
                email = 'unknown'
                if len(tokens) > 1:
                    email = tokens[1].replace('>','').strip()

                self.store.append((name, email, keyid))

        # create the tree view
        self.treeView = Gtk.TreeView(model=self.store)

        # setup 'Name' column
        nameRenderer = Gtk.CellRendererText()
        nameColumn = Gtk.TreeViewColumn("Name", nameRenderer, text=0)

        # setup 'Email' column
        emailRenderer = Gtk.CellRendererText()
        emailColumn = Gtk.TreeViewColumn("Email", emailRenderer, text=1)

        # setup 'Key' column
        keyRenderer = Gtk.CellRendererText()
        keyColumn = Gtk.TreeViewColumn("Key", keyRenderer, text=2)

        self.treeView.append_column(nameColumn)
        self.treeView.append_column(emailColumn)
        self.treeView.append_column(keyColumn)

        # make the tree view resposive to single click selection
        self.treeView.get_selection().connect('changed', self.on_selection_changed)

        # make the tree view scrollable
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled_window.add(self.treeView)
        self.scrolled_window.set_min_content_height(200)

        self.pack_start(self.scrolled_window, True, True, 0)

    def on_selection_changed(self, *args):
        self.keySection.nextButton.set_sensitive(True)


class KeyPresentPage(Gtk.HBox):
    def __init__(self):
        super(KeyPresentPage, self).__init__()

        # create left side Key labels
        fingerprintMark = Gtk.Label()
        fingerprintMark.set_markup('<span size="15000">' + 'Key Fingerprint' + '</span>')

        self.fingerprintLabel = Gtk.Label()
        self.fingerprintLabel.set_markup('<span size="20000">' + FINGERPRINT_DEFAULT + '</span>')

        # left vertical box
        leftVBox = Gtk.VBox(spacing=10)
        leftVBox.pack_start(fingerprintMark, False, False, 0)
        leftVBox.pack_start(self.fingerprintLabel, False, False, 0)

        # display QR code on the right side
        imageLabel = Gtk.Label()
        imageLabel.set_markup('<span size="15000">' + 'Key QR code' + '</span>')

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size('qrsample.png', 200, -1)
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(pixbuf)
        self.image.props.margin = 10

        # right vertical box
        rightVBox = Gtk.VBox(spacing=10)
        rightVBox.pack_start(imageLabel, False, False, 0)
        rightVBox.pack_start(self.image, False, False, 0)

        self.pack_start(leftVBox, True, True, 0)
        self.pack_start(rightVBox, False, False, 0)

    def display_fingerprint_qr_page(self, openPgpKey):
        rawfpr = openPgpKey.fpr

        fpr = ""
        for i in xrange(0, len(rawfpr), 4):

            fpr += rawfpr[i:i+4]
            if i != 0 and (i+4) % 20 == 0:
                fpr += "\n"
            else:
                fpr += " "

        fpr = fpr.rstrip()
        self.fingerprintLabel.set_markup('<span size="20000">' + fpr + '</span>')


class KeyDetailsPage(Gtk.VBox):

    def __init__(self):
        super(KeyDetailsPage, self).__init__()
        self.set_spacing(10)
        
        self.log = logging.getLogger()

        # FIXME: this should be moved to KeySignSection
        self.keyring = Keyring()

        uidsLabel = Gtk.Label()
        uidsLabel.set_text("UIDs")

        # this will later be populated with uids when user selects a key
        self.uidsBox = Gtk.VBox(spacing=5)

        expireLabel = Gtk.Label()
        expireLabel.set_text("Expires 0000-00-00")

        signaturesLabel = Gtk.Label()
        signaturesLabel.set_text("Signatures")

        # this will also be populated later
        self.signaturesBox = Gtk.VBox(spacing=5)

        self.pack_start(uidsLabel, False, False, 0)
        self.pack_start(self.uidsBox, True, True, 0)
        self.pack_start(expireLabel, False, False, 0)
        self.pack_start(signaturesLabel, False, False, 0)
        self.pack_start(self.signaturesBox, True, True, 0)

    def parse_sig_list(self, text):
        sigslist = []
        for block in text.split("\n"):
            record = block.split(":")
            if record[0] != "sig":
                continue
            self.log.debug("sig record (%d) %s", len(record), record)
            (rectype, null, null, algo, keyid, timestamp, null, null, null, uid, null, null) = record
            sigslist.append((keyid, timestamp, uid))

        return sigslist

    def display_uids_signatures_page(self, openPgpKey):

        # destroy previous uids
        for uid in self.uidsBox.get_children():
            self.uidsBox.remove(uid)
        for sig in self.signaturesBox.get_children():
            self.signaturesBox.remove(sig)

        # display a list of uids
        labels = []
        for uid in openPgpKey.uidslist:
            label = Gtk.Label(str(uid.uid))
            label.set_line_wrap(True)
            labels.append(label)

        for label in labels:
            self.uidsBox.pack_start(label, False, False, 0)
            label.show()
        # FIXME: this would be better if it was done in monkeysign
        self.keyring.context.call_command(['list-sigs', str(openPgpKey.keyid())])

        sigslist = self.parse_sig_list(self.keyring.context.stdout)
        # FIXME: what do we actually want to show here: the numbers of signatures
        # for this key or the number of times this key was used to signed others
        for (keyid,timestamp,uid) in sigslist:
            sigLabel = Gtk.Label()
            date = datetime.fromtimestamp(float(timestamp))
            sigLabel.set_markup(str(keyid) + "\t\t" + date.ctime())
            sigLabel.set_line_wrap(True)

            self.signaturesBox.pack_start(sigLabel, False, False, 0)
            sigLabel.show()
