#!/usr/bin/python3
# Gerrit QT5 UI
# created by Rene Kjellerup (c)2017
# published under GNU GPL version 3 or later
# for license details please see https://www.gnu.org/licenses/gpl.html

from paramiko import SSHClient
from paramiko import Agent
from paramiko import SSHException

from PyQt5.QtWidgets import QApplication
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QListView
from PyQt5.QtWidgets import QDialogButtonBox
from PyQt5.QtWidgets import QAbstractButton
from PyQt5.QtWidgets import QRadioButton
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtWidgets import QTextBrowser
from PyQt5.QtCore import QStringListModel
from PyQt5.QtCore import QModelIndex
from PyQt5.QtCore import QSize
from PyQt5.QtCore import pyqtSlot
from PyQt5.uic import loadUi
import sys
import os


def login(
        server='172.26.100.35',
        port=29418,
        username=os.getlogin(),
        cli=SSHClient(),
        keys=Agent().get_keys()
        ):
    cli.load_system_host_keys()
    for key in keys:
        try:
            cli.connect(server, port, username, pkey=key)
            return cli
        except SSHException:
            pass
    return None


class Change(QDialog):
    @pyqtSlot(QAbstractButton)
    def exit(self, btn):
        for lvl in range(-2, 3):
            rb = None
            if lvl > 0:
                rb = self.ui.findChild(QRadioButton,
                                       'code_u'+str(lvl))
            elif lvl < 0:
                rb = self.ui.findChild(QRadioButton,
                                       'code_d'+str(abs(lvl)))
            else:
                rb = self.ui.findChild(QRadioButton,
                                       'code_0')
            if rb.isChecked():
                self.review['code-review'] = lvl
                break

        for lvl in range(-1, 2):
            rb = None
            if lvl > 0:
                rb = self.ui.findChild(QRadioButton,
                                       'veri_u'+str(lvl))
            elif lvl < 0:
                rb = self.ui.findChild(QRadioButton,
                                       'veri_d'+str(abs(lvl)))
            else:
                rb = self.ui.findChild(QRadioButton,
                                       'veri_0')
            if rb.isChecked():
                self.review['verified'] = lvl
                break
        role = self.ui.findChild(QDialogButtonBox, 'bb').buttonRole(btn)
        if role == QDialogButtonBox.AcceptRole:
            self.accept()
        if role == QDialogButtonBox.RejectRole:
            self.reject()
        if role == QDialogButtonBox.ApplyRole:
            self.review['submit'] = True
            self.accept()
        if role == QDialogButtonBox.NoRole:
            self.review['abandon'] = True
            self.accept()
        if role == QDialogButtonBox.ResetRole:
            self.review['restore'] = True
            self.accept()

    def readComments(self):
        p = []
        ap = '{reviewer[name]} {message}'
        if 'comments' in self.data:
            for ps in self.data['comments']:
                p.append(ap.format(**ps))

        model = QStringListModel(self)
        model.setStringList(p)
        self.ui.findChild(QListView, 'actionLog').setModel(model)

    def applyApprovals(self):
        approvals = self.data['currentPatchSet']['approvals']
        for a in approvals:
            if a['by']['username'] == self.user:
                if a['type'] == 'Code-Review':
                    x = str(a['value'])
                    r = None
                    if int(a['value']) > 0:
                        r = self.ui.findChild(QRadioButton, 'code_u'+x)
                    else:
                        r = self.ui.findChild(QRadioButton, 'code_d'+x)
                    if r is not None:
                        r.setChecked(True)
                    self.review['code-review'] = int(a['value'])
                if a['type'] == 'Verified':
                    x = str(a['value'])
                    r = None
                    if int(a['value']) > 0:
                        r = self.ui.findChild(QRadioButton, 'veri_u'+x)
                    else:
                        r = self.ui.findChild(QRadioButton, 'veri_d'+x)
                    if r is not None:
                        r.setChecked(True)
                    self.review['verified'] = int(a['value'])

    def listFilesChanged(self):
        file_line = '{type:.2} {insertions:+5}/{deletions:5} {file}'
        fls = []
        for f in self.data['currentPatchSet']['files']:
            fls.append(file_line.format(**f))
        model = QStringListModel(self)
        model.setStringList(fls)
        self.ui.findChild(QListView, 'files').setModel(model)

    def applyData2Ui(self):
        self.setWindowTitle(self.data['status'] + ' ' + self.data['subject'])
        self.ui.findChild(QRadioButton, 'code_0').setChecked(True)
        self.ui.findChild(QRadioButton, 'veri_0').setChecked(True)
        msg = self.ui.findChild(QTextBrowser, 'message')
        msg.setText(self.data['commitMessage'])
        self.readComments()
        if 'approvals' in self.data['currentPatchSet']:
            self.applyApprovals()
        self.listFilesChanged()

    def __init__(self, user, gerrit_dict={}, parent=None):
        QDialog.__init__(self, parent)
        self.data = gerrit_dict
        self.user = user
        self.one_line = '{owner[name]: <30} {number: <5} {project: <15} '
        self.one_line += '{subject: <.40}'
        self.review = {
            'change': '{number},{currentPatchSet[number]}'.format(**self.data),
            'verified': 0,
            'code-review': 0,
            'submit': False,
            'abandon': False,
            'restore': False
        }
        self.ui = loadUi('ui/change.ui')
        QVBoxLayout(self).addWidget(self.ui)
        self.resize(self.ui.frameSize())
        self.ui.findChild(QDialogButtonBox, 'bb').clicked.connect(self.exit)
        status = self.data['status']
        if status != 'MERGED' and status != 'ABANDONED':
            self.ui.findChild(QDialogButtonBox, 'bb').addButton(
                'Submit',
                QDialogButtonBox.ApplyRole
            )
            self.ui.findChild(QDialogButtonBox, 'bb').addButton(
                'Abandon',
                QDialogButtonBox.NoRole
            )
        if status == 'ABANDONED':
            self.ui.findChild(QDialogButtonBox, 'bb').addButton(
                'Restore',
                QDialogButtonBox.ResetRole
            )
        self.applyData2Ui()

    def __str__(self):
        d = self.data
        try:
            return self.one_line.format(**d)
        except KeyError as k:
            print(d.keys())
            raise k


class GerritUI(QWidget):
    def currentUser(self):
        return self.user

    @pyqtSlot(QAbstractButton)
    def menuSelect(self, button):
        if 'Open' in button.text():
            self.getOpen()
        if 'Merged' in button.text():
            self.getMerged()

    @pyqtSlot(QModelIndex)
    def ChangeSelected(self, index):
        change = self.reviews[index.row()]
        if change.exec_() == QDialog.Accepted:
            self.review(change.review)

    def query(self, q='status:open'):
        que = 'gerrit query --format=JSON --current-patch-set '
        que += '--all-approvals --files --commit-message '
        que += '--dependencies --submit-records --comments ' + q
        msg.show()
        print('sending: "{0}"'.format(que))
        out = self._cli.exec_command(que)
        raw = out[1].read().decode('utf-8')
        msg.hide()
        raw = raw.replace('true', 'True').replace('false', 'False')
        return raw.split('\n')

    def review(self, review):
        r = ['gerrit review']
        r.append('--verified {0:+}'.format(review['verified']))
        r.append('--code-review {0:+}'.format(review['code-review']))
        if review['submit']:
            r.append('--submit')
        elif review['abandon']:
            r.append('--abandon')
        elif review['restore']:
            r.append('--restore')
        else:
            r.append('--publish')
        r.append(review['change'])
        msg.show()
        print('sending: "{0}"'.format(' '.join(r)))
        out = self._cli.exec_command(' '.join(r))[1]
        out.read()
        msg.hide()
        self.getOpen()

    def getOpen(self):
        self.reviews = []
        change_list = self.query()
        for rev in change_list[:-2]:
            self.reviews.append(Change(self.currentUser(), eval(rev)))
        list_view = self.ui.findChild(QListView, 'change_list')
        model = QStringListModel(self.ui)
        opts = []
        for rev in self.reviews:
            opts.append(str(rev))
        model.setStringList(opts)
        list_view.setModel(model)

    def getMerged(self):
        self.reviews = []
        change_list = self.query('status:merged limit:25')
        for rev in change_list[:-2]:
            self.reviews.append(Change(self.currentUser(), eval(rev), self))
        list_view = self.ui.findChild(QListView, 'change_list')
        model = QStringListModel(self.ui)
        opts = []
        for rev in self.reviews:
            opts.append(str(rev))
        model.setStringList(opts)
        list_view.setModel(model)

    def __init__(self, user, parent=None, g_server=login()):
        QDialog.__init__(self, parent)
        self._cli = g_server
        self.user = user
        self.ui = loadUi('ui/main.ui')
        QVBoxLayout(self).addWidget(self.ui)
        self.resize(self.ui.frameSize())
        self.getOpen()
        menu = self.ui.findChild(QDialogButtonBox, 'menu')
        menu.clicked.connect(self.menuSelect)
        menu.addButton('Open', QDialogButtonBox.AcceptRole)
        menu.addButton('Merged', QDialogButtonBox.RejectRole)
        menu.addButton('Abandoned', QDialogButtonBox.DestructiveRole)
        view = self.ui.findChild(QListView, 'change_list')
        view.doubleClicked.connect(self.ChangeSelected)


class Message(QDialog):
    def __init__(self):
        QDialog.__init__(self, None)
        self.setWindowTitle('Quering Gerrit')
        vb = QVBoxLayout(self)
        self.msg = QLabel('please wait...')
        vb.addWidget(self.msg)
        self.msg.repaint()
        self.resize(QSize(350, 60))


if __name__ == '__main__':
    a = QApplication(sys.argv)
    msg = Message()
    connection = {
        'server': '',
        'port': 29418,
        'username': os.getlogin(),
        'cli': SSHClient(),
        'keys': Agent().get_keys()
    }
    if '-u' in sys.argv:
        i = sys.argv.index('-u') + 1
        if i >= len(sys.argv):
            print('User name not defined')
            sys.exit(1)
        connection['username'] = sys.argv[i]
    if '-h' in sys.argv:
        i = sys.argv.index('-h') + 1
        if i >= len(sys.argv):
            print('Host name expected')
            sys.exit(1)
        connection['server'] = sys.argv[i]
    if '-p' in sys.argv:
        i = sys.argv.index('-p') + 1
        if i >= len(sys.argv):
            print('Host name expected')
            sys.exit(1)
        connection['port'] = int(sys.argv[i])
    msg.setWindowTitle('Open connection to Gerrit')
    msg.show()
    msg.msg.repaint()
    cli = login(**connection)
    msg.hide()
    msg.setWindowTitle('Quering Gerrit')
    GUI = GerritUI(connection['username'], g_server=cli)
    GUI.show()
    sys.exit(a.exec_())
