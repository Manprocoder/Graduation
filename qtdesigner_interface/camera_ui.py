# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/manprocoder/test1/local_interface/camera.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1920, 1080)
        Dialog.setStyleSheet("border-color: rgb(52, 101, 164);\n"
"background-color: rgb(211, 215, 207);\n"
"")
        self.startButton = QtWidgets.QPushButton(Dialog)
        self.startButton.setGeometry(QtCore.QRect(1480, 170, 281, 51))
        self.startButton.setStyleSheet("background-color: rgb(114, 159, 207);")
        self.startButton.setObjectName("startButton")
        self.stopButton = QtWidgets.QPushButton(Dialog)
        self.stopButton.setGeometry(QtCore.QRect(1480, 250, 281, 51))
        self.stopButton.setStyleSheet("background-color: rgb(239, 41, 41);")
        self.stopButton.setObjectName("stopButton")
        self.savedButton = QtWidgets.QPushButton(Dialog)
        self.savedButton.setGeometry(QtCore.QRect(1480, 330, 281, 51))
        self.savedButton.setStyleSheet("background-color: rgb(138, 226, 52);")
        self.savedButton.setObjectName("savedButton")
        self.label = QtWidgets.QLabel(Dialog)
        self.label.setGeometry(QtCore.QRect(920, 30, 171, 101))
        self.label.setObjectName("label")
        self.graphicsView = QtWidgets.QGraphicsView(Dialog)
        self.graphicsView.setGeometry(QtCore.QRect(170, 150, 1280, 720))
        self.graphicsView.setStyleSheet("border-color: rgb(52, 101, 164);")
        self.graphicsView.setObjectName("graphicsView")

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.startButton.setText(_translate("Dialog", "START"))
        self.stopButton.setText(_translate("Dialog", "STOP"))
        self.savedButton.setText(_translate("Dialog", "VIEW SAVED VIDEO"))
        self.label.setText(_translate("Dialog", "<html><head/><body><p><span style=\" font-size:28pt; font-weight:600; color:#ef2929;\">CAMERA</span></p></body></html>"))
