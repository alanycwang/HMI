from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIntValidator, QValidator, QRegExpValidator

import astropy.time

import copy, fnmatch, ar

class ARSearch(QWidget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.mainwidget = QWidget()
        self.setChildrenFocusPolicy(self, Qt.NoFocus)
        self.mainlayout = QVBoxLayout(self)
        self.layout = QGridLayout(self.mainwidget)
        self.setStyleSheet("QObject { background: white; }")
        self.mainlayout.addWidget(self.mainwidget)

        self.load_widgets()

    def load_widgets(self):
        self.i = 0

        #longevity
        self.ll = QLabel()
        self.ll.setText("Longevity: ")
        self.ll.setAlignment(Qt.AlignRight)

        self.le = QLineEdit()
        self.le.setValidator(QIntValidator())
        self.le.setMaxLength(2)
        self.le.setAlignment(Qt.AlignLeft)

        self.ll2 = QLabel()
        self.ll2.setText("days")
        self.ll2.setAlignment(Qt.AlignLeft)

        self.add_row(self.ll, self.le, self.ll2)

        #start time
        self.sl = QLabel()
        self.sl.setText("Start Date: ")
        self.sl.setAlignment(Qt.AlignRight)

        self.se = QLineEdit()
        self.se.setInputMask("09/09/9999")
        self.se.setAlignment(Qt.AlignLeft)

        self.add_row(self.sl, self.se)

        #end time
        self.el = QLabel()
        self.el.setText("End Date: ")
        self.el.setAlignment(Qt.AlignRight)

        self.ee = QLineEdit()
        self.ee.setInputMask("09/09/9999")
        self.ee.setAlignment(Qt.AlignLeft)

        self.add_row(self.el, self.ee)

        #date of crossing central meridian
        self.dl = QLabel()
        self.dl.setText("Date of Crossing the Central Meridian: ")
        self.dl.setAlignment(Qt.AlignRight)

        self.de = QLineEdit()
        self.de.setInputMask("09/09/9999")
        self.de.setAlignment(Qt.AlignLeft)

        self.add_row(self.dl, self.de)

        #centering
        self.cl = QLabel()
        self.cl.setText("Centering: ")
        self.cl.setAlignment(Qt.AlignRight)

        self.ce = QLineEdit()
        self.ce.setValidator(QRegExpValidator(QRegExp("^(\*\/)?([NS\*])(\d{1,2}|\*|((\d{1,2}|\*):(\d{1,2}|\*)))([EW\*])(\d{1,2}|\*|((\d{1,2}|\*):(\d{1,2}|\*)))(\/\*)?$")))
        self.ce.setAlignment(Qt.AlignLeft)

        self.cl2 = QLabel()
        self.cl2.setText(" Daily Step Vector: ")
        self.cl2.setAlignment(Qt.AlignLeft)

        self.ce2 = QLineEdit()
        self.ce2.setValidator(QRegExpValidator(QRegExp("^(\*\/)?(d{1,2})(\/\*)?")))
        self.ce2.setAlignment(Qt.AlignLeft)

        self.add_row(self.cl, self.ce, self.cl2, self.ce2)

        #class
        self.tl = QLabel()
        self.tl.setText("Class: ")
        self.tl.setAlignment(Qt.AlignRight)

        self.te = QLineEdit()
        self.te.setValidator(ClassValidator())
        self.te.setAlignment(Qt.AlignLeft)

        self.tl2 = QLabel()
        self.tl2.setText(" Persistence: ")
        self.tl2.setAlignment(Qt.AlignLeft)

        self.te2 = QLineEdit()
        self.te2.setValidator(PersistenceValidator())
        self.te2.setAlignment(Qt.AlignLeft)

        self.add_row(self.tl, self.te, self.tl2, self.te2)

        self.cb = QPushButton()
        self.cb.setText("Search")
        self.cb.clicked.connect(self.enter)
        self.layout.addWidget(self.cb, self.i, 1)

    def enter(self, _):
        print(self.checkEntries())

    def checkEntries(self):
        def fixtime(t):
            if t == "//":
                return t
            for i, c in reversed(list(enumerate(t))):
                if c == "/" and i == len(t) - 3:
                    t = t[:-2] + "20" + t[-2:]
                elif c == "/" and t[i + 2] == "/":
                    t = t[:i + 1] + "0" + t[i + 1:]
            if len(t) < 10:
                t = "0" + t
            t = t.replace('/', '-')
            return t

        t = [self.le.text(), fixtime(self.se.text()), fixtime(self.ee.text()), fixtime(self.de.text()), self.ce.text(), self.ce2.text(), self.te.text(), self.te2.text()]
        print(t)

        #validate centering

        if (self.te.text()[0:2] == "*/" and self.te2.text()[0:2] != "*/") or (self.te2.text()[:2] == "*/" and self.te.text()[:2] != "*/") or (self.te.text()[0:2] == "*/" and self.te2.text()[0:2] != "*/") or (self.te2.text()[0:2] == "*/" and self.te.text()[0:2] != "*/"):
            return "AR Centering and Daily Step Vector should match in format"

        #validate class
        if self.te.text().count("/") != self.te2.text().count("/"):
            return "AR Classes and Persistences should match in format"

        data = ar.update_ar_data()
        return ar.filter_ar(data, start=astropy.time.Time.strptime(t[1], "%m-%d-%Y"), end=astropy.time.Time.strptime(t[2], "%m-%d-%Y"), ct=astropy.time.Time.strptime(t[3], "%m-%d-%Y    "), longevity=t[0], centering=[t[4], t[5]], mag_type=[t[6], t[7]])

    def add_row(self, *args):
        for i, widget in enumerate(args):
            self.layout.addWidget(widget, self.i, i)
        self.i += 1

    def setChildrenFocusPolicy(self, w, policy):
        def recursiveSetChildFocusPolicy(parentQWidget):
            for childQWidget in parentQWidget.findChildren(QWidget):
                childQWidget.setFocusPolicy(policy)
                recursiveSetChildFocusPolicy(childQWidget)

        recursiveSetChildFocusPolicy(w)

class ClassValidator(QValidator):
    def validate(self, s, pos):
        intermediate = False
        for c in s:
            if c not in ['a', 'b', 'c', 'd', 'g', '/', 'α', 'β', 'γ', 'δ']:
                return (QValidator.Invalid, s, pos)
            elif c in ['a', 'b', 'c', 'd', 'g']:
                intermediate = True
        if intermediate:
            return (QValidator.Intermediate, s, pos)
        return (QValidator.Acceptable, s, pos)

    def fixup(self, s):
        s = s.replace('a', 'α')
        s = s.replace('b', 'β')
        s = s.replace('c', 'γ')
        s = s.replace('g', 'γ')
        s = s.replace('d', 'δ')
        return s

class PersistenceValidator(QValidator):
    def validate(self, s, pos):
        for c in s:
            if not c.isdigit() and c != '/':
                return (QValidator.Invalid, s, pos)
        return(QValidator.Acceptable, s, pos)

#^[NS\*]-?(\d{1,2}|\*|((\d{1,2}|\*):(\d{1,2}|\*)))[EW\*]-?(\d{1,2}|\*|((\d{1,2}\*):(\d{1,2}|\*)))$

#*, [0-9][0-9], [0-
# *, 09, 09:*, *:09, 09:09