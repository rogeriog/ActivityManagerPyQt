# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'untitled2.ui'
#
# Created by: PyQt5 UI code generator 5.9.2
#
# WARNING! All changes made in this file will be lost!

#### boa parte das entradas e saidas no csv estavam escritas com o uso do pacote
### de csv, however, this package doesnt offer good flexibility, therefore now
# the code uses readlines and takes the csv to memory what may be problem to very
# large data, but is much easier to edit.

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QDate, QTime, QDateTime, Qt, QSize
import pyqtgraph as pg

from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import colors
import numpy as np
import random
import sys, os
import re
import pandas as pd
import datetime as dt
import time


### read data from files
def update_csv():
    date=ui.ControlBaP.dateEdit.date().toPyDate() #.strftime('%d.%m.%Y')
    pts=np.zeros(len(ui.AEs))
    counters=[]
    for i in range(len(ui.AEs)):
        pts[i]=ui.AEs[i].plainTextEdit_daymark.toPlainText()
        counters.append(ui.AEs[i].stopwatch.get_counter())
    weights=ui.DS.checkActivities[1]
    labels=ui.DS.checkActivities[0]
    dates=[date]*len(ui.AEs)
    data_to_file=list(map(list, zip(dates,labels,weights,pts.astype(int),counters)))
    df_new=pd.DataFrame(data_to_file, columns=['date','activity','weight','points','crono'])
    df_new["date"] = pd.to_datetime(df_new.date)
    ui.DS.df=ui.DS.df[pd.to_datetime(ui.DS.df['date']).dt.date<date] ## exclude data on same date, so only what is in labels count
    ui.DS.df=pd.concat([df_new,ui.DS.df]).sort_values("date",ascending=False)
    ui.DS.df=ui.DS.correctDf()
    ui.DS.df.to_csv('dados.csv', index = False)
class DataAndSettings:
    def __init__(self, *args, **kwargs):
        #super().__init__(self,*args, **kwargs)
        df=pd.read_csv('dados.csv',names=['date','activity','weight','points','crono'],skiprows=1)
        df["date"] = pd.to_datetime(df['date'])
        self.df=df.sort_values("date",ascending=False)
        self.df=self.correctDf()
        self.nowDate=df.iloc[0].date
        self.lastMonday = self.nowDate-dt.timedelta(self.nowDate.weekday())
        self.firstDayMonth=self.nowDate.replace(day=1)
        self.checkDays=(self.nowDate,self.lastMonday,self.firstDayMonth)
        
        df["score"]=df['weight']*df['points']
        self.todayScore=df[df['date']==self.nowDate]['score'].sum()
        self.weekScore=df[df['date']>=self.lastMonday]['score'].sum()
        self.monthScore=df[df['date']>=self.firstDayMonth]['score'].sum()
        self.checkScores=(self.todayScore,self.weekScore,self.monthScore)
        
        self.settings_activities=pd.read_csv('settings.txt',names=['activity','weight','color'])

        self.activityName=list(self.settings_activities['activity'])
        self.activityWeight=list(self.settings_activities['weight'])
        self.activityColor=list(self.settings_activities['color'])
        self.checkActivities=(self.activityName,self.activityWeight,self.activityColor)
        dfweek=df[df['date']>=self.lastMonday]
        self.dfweekGrouped=dfweek.groupby(['date','activity'])['score'].sum().unstack('activity').fillna(0)
        self.df_columns=self.dfweekGrouped.columns
        ## so only activities declared in settings are takin into account
        self.activityCrono=[]
        self.df_columns = np.intersect1d(self.df_columns.to_numpy(),self.settings_activities['activity'].to_numpy())
        for column in self.activityName:
            crono=self.df[self.df['date']==self.nowDate]
            crono=crono.loc[self.df['activity']==column]['crono']
            if len(crono) == 0:
                crono='0000:00:00'
            else:
                crono=crono.to_string(index = False)
            self.activityCrono.append(crono)


    def correctDf(self):
        ## to remove duplicates in df summing the points for same date and keeping the higher weight for each activity in that day.
        df=self.df
        dfdupl=df[df.duplicated(['date', 'activity'],keep=False)].reset_index()
        jexclude=[] ## not recount
        for irow in range(len(dfdupl)):
            if irow not in jexclude:
                for jrow in range(len(dfdupl)):
                    if irow != jrow:
                        if jrow not in jexclude:
                            if dfdupl.loc[irow,['date', 'activity']].equals(dfdupl.loc[jrow,['date', 'activity']]):
                                dfdupl.loc[irow,'points']+=dfdupl.loc[jrow,'points']
                                if dfdupl.loc[irow,'weight']<dfdupl.loc[jrow,'weight']:
                                    dfdupl.loc[irow,'weight']=dfdupl.loc[jrow,'weight']
                                jexclude.append(jrow)
        dfdupl=dfdupl.drop_duplicates(subset=['date', 'activity'],keep='first')
        df.drop_duplicates(subset=['date', 'activity'],keep=False,inplace=True)
        df = pd.concat([dfdupl,df]).sort_values("date",ascending=False).drop('index',axis=1)
        return df

class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=6.7, height=3,**kwargs):
        fig,self.ax1 = plt.subplots(figsize=(7,4), constrained_layout=True)

        FigureCanvas.__init__(self, fig)
        self.PlotBars()
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Fixed,
                                   QtWidgets.QSizePolicy.Fixed)
#        FigureCanvas.setSizePolicy(self,
#                                   QtWidgets.QSizePolicy.Expanding,
#                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class MyDynamicMplCanvas(MplCanvas):
    """A canvas that updates itself with a new plot."""

    def __init__(self, *args, **kwargs):
        MplCanvas.__init__(self, *args, **kwargs)
        ui.ControlBaP.SaveButton.clicked.connect(self.PlotBars)
        ui.ControlBaP.StartNewDay.clicked.connect(self.PlotBars)

    def PlotBars(self):           
        ui.DS=DataAndSettings() ## needs to regenerate dfweekGrouped
        df_index=ui.DS.dfweekGrouped.index.strftime('%d/%m')
        ## cumulative score to use in the bar plot.
        cumptsActivities=np.zeros(len(df_index))
        #fig, ax = plt.subplots()

        #self.ax1.cla() ## senao fica mudando de cor
        firstColumn=True
        for column in ui.DS.df_columns:
            ptsActivity=ui.DS.dfweekGrouped[column]
            color=ui.DS.settings_activities[ui.DS.settings_activities['activity']==column]['color'].to_string(index = False)
            if color == 'nan' or color =='NaN':
                color=None
            if firstColumn:
                self.ax1.bar(df_index, ptsActivity,color=color)
                firstColumn=False
            else:
                self.ax1.bar(df_index, ptsActivity, bottom=cumptsActivities,color=color)
            cumptsActivities+=ptsActivity
        self.ax1.set_xlabel("Date")
        self.ax1.set_ylabel("Points")
        self.ax1.legend(ui.DS.df_columns,prop={'size': 8},bbox_to_anchor=(1.00, 1))
        self.draw()    


class stopwatch():
    def __init__(self,*args,**kwargs):
        self.mscounter=0
        self.icounter=0
        x,y,counter,i=args
        self.Window=kwargs.get('Dialog',Dialog)
        self.set_counter(counter)
        self.i=i # to track which AE owns it
        self.isreset = True
        self.isstart = False
        self.start = time.time()
        self.cronometer = QtWidgets.QLCDNumber(self.Window)
        #self.cronometer.setStyleSheet("QLCDNumber { background-color: cyan; color: black }""")
        self.cronometer.setSegmentStyle(QtWidgets.QLCDNumber.Flat)

        ## following code gets the font with higher contrast, either black or white depending on the background
        if str(ui.DS.activityColor[self.i]) != "nan":
            colorcode_activity=colors.to_rgba(str(ui.DS.activityColor[self.i]))
            r,g,b,_ = colorcode_activity
            lum = ((0.299 * r) + (0.587 * g) + (0.114 * b))
            font_color="black" if lum > 0.5 else "white" 
            self.cronometer.setStyleSheet("QLCDNumber { background-color: "+ str(ui.DS.activityColor[self.i]) + \
                    "; color: "+font_color+" }")
        else:
            self.cronometer.setStyleSheet("QLCDNumber { background-color: white; color: black }")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.run_watch)
        self.timer.setInterval(1)
        if self.Window == Dialog: ## can open float widget
            self.playButton = QtWidgets.QPushButton(self.Window)
            self.playButton.setIconSize(QSize(16, 16))
            self.playButton.setIcon(self.playButton.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
            self.playButton.clicked.connect(self.start_pause)
            self.playButton.setGeometry(QtCore.QRect(x, y, 21, 23))
        self.cronometer.setGeometry(QtCore.QRect(x+20, y, 95, 21))
        self.showLCD()
### make window buttons way smaller, eliminate margin in cronometer
    def set_counter(self,counter):
        dt_obj =counter.split(':') #   '109:38:42'.split(':')
        dt_obj=int(dt_obj[0])*3600+int(dt_obj[1])*60+int(dt_obj[2])
        if dt_obj > 5:
            self.mscounter = dt_obj * 1000 
        else:
            self.mscounter = 1
        try: ## if initializing this cant run but in update it will
            self.showLCD()
        except:
            pass
    def get_counter(self):
        ms=int(self.mscounter/1000) ## ms to s
        ms1=int(ms/3600)
        ms2=int((ms-3600*ms1)/60)
        ms3=ms-3600*ms1-60*ms2
        counter=f"{ms1:04d}:{ms2:02d}:{ms3:02d}"
        return counter

    def start_pause(self):
        if not self.isstart:
            self.isstart=True
            self.timer.start()
            self.isreset = False
            if self.Window == Dialog:
                ui.show_new_window(self,self)
#                self.playButton.clicked.connect( lambda : ui.show_new_window(self,self))
                self.playButton.setIcon(self.playButton.style().standardIcon(QtWidgets.QStyle.SP_MediaPause))
        else:
            self.isstart=False
            self.timer.stop()
            if self.Window == Dialog:
                self.playButton.setIcon(self.playButton.style().standardIcon(QtWidgets.QStyle.SP_MediaPlay))
    

    def showLCD(self):
        self.timer_text=self.get_counter()
        self.cronometer.setDigitCount(9)
        self.cronometer.display(self.timer_text)

    def run_watch(self):
        self.mscounter += 1
        self.icounter+=1
        if self.Window == Dialog:
            if self.icounter == 5*60*1000: #every 5 min
                ui.AEs[self.i].pushButton_plus.click()
                self.icounter=0
        self.showLCD()

class ActivityEntry():
    def __init__(self,*args,**kwargs): 
        x,y,i = args
        _translate = QtCore.QCoreApplication.translate
        self.label_activity = QtWidgets.QLabel(Dialog)
        self.label_activity.setGeometry(QtCore.QRect(x, y, 100, 21))
        self.label_activity.setText(_translate("Dialog", str(ui.DS.activityName[i])))
        
        self.plainTextEdit_fix = QtWidgets.QLabel(Dialog)
        self.plainTextEdit_fix.setGeometry(QtCore.QRect(x+115, y, 51, 21)) 
        self.plainTextEdit_fix.setText(_translate("Dialog", str(ui.DS.activityWeight[i])))
        
        self.plainTextEdit_daymark = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEdit_daymark.setGeometry(QtCore.QRect(x+190, y, 71, 21))
        self.plainTextEdit_daymark.setPlainText(_translate("Dialog", "0"))
        self.update_daymark() ## get daymark from dados.csv
        
        self.pushButton_minus = QtWidgets.QPushButton(Dialog)
        self.pushButton_minus.setGeometry(QtCore.QRect(x+170, y, 21, 23))
        self.pushButton_minus.clicked.connect(self.decrementValue(self.plainTextEdit_daymark))
        self.pushButton_minus.setText(_translate("Dialog", "-"))
        
        self.pushButton_plus = QtWidgets.QPushButton(Dialog)
        self.pushButton_plus.setGeometry(QtCore.QRect(x+260, y, 21, 23))
        self.pushButton_plus.clicked.connect(self.incrementValue(self.plainTextEdit_daymark))
        self.pushButton_plus.setText(_translate("Dialog", "+"))
        
        ## stopwatch play button doesnt work when declared here.
        self.stopwatch=stopwatch(x+290,y,ui.DS.activityCrono[i],i)
    def decrementValue(self, txtname):
        def dv():
            _translate = QtCore.QCoreApplication.translate
            str1=txtname.toPlainText()
            var1=int(str1)-1
            str1=str(var1)
            txtname.setPlainText(_translate("Dialog", str1))
            #perform a programmatic click
            ui.ControlBaP.SaveButton.click()
        return dv
        
    def incrementValue(self,txtname):
       def iv():
        _translate = QtCore.QCoreApplication.translate
        str1=txtname.toPlainText()
        var1=int(str1)+1
        str1=str(var1)
        txtname.setPlainText(_translate("Dialog", str1))        
        #perform a programmatic click
        ui.ControlBaP.SaveButton.click()
       return iv

    def update_daymark(self):
        _translate = QtCore.QCoreApplication.translate
        activity=self.label_activity.text()
        updated_pts=ui.DS.df.loc[ui.DS.df['date']==ui.DS.nowDate].loc[ui.DS.df['activity']==activity]['points'].values
        if not np.any(updated_pts): # if empty pass
            pass
        else:
            self.plainTextEdit_daymark.setPlainText(_translate("Dialog", str(updated_pts[0])))

class ControlButtonsAndPoints():
    def __init__(self,*args,**kwargs): 
        self.x,self.y=args
        _translate = QtCore.QCoreApplication.translate
        
        self.dateEdit = QtWidgets.QDateEdit(Dialog)
        self.dateEdit.setGeometry(QtCore.QRect(self.x, self.y, 110, 22))
        self.today = QDate.currentDate()
        qnowDate = QDate.fromString( ui.DS.checkDays[0].strftime('%d/%m/%Y') , "dd/MM/yyyy" )
        self.dateEdit.setDate(qnowDate)
         
        self.SaveButton = QtWidgets.QPushButton(Dialog)
        self.SaveButton.setGeometry(QtCore.QRect(self.x+10, self.y+30, 91, 23))
        self.SaveButton.clicked.connect(self.UpdatePts(Dialog))
        self.SaveButton.setText(_translate("Dialog", "Save Changes"))


        self.StartNewDay = QtWidgets.QPushButton(Dialog)
        self.StartNewDay.setGeometry(QtCore.QRect(self.x+10, self.y+60, 91, 23))
        self.StartNewDay.setObjectName("StartNewDay")
        self.StartNewDay.clicked.connect(self.StartNewDayAction(self.StartNewDay))
        self.StartNewDay.clicked.connect(self.UpdatePts(Dialog)) 
        self.StartNewDay.setText(_translate("Dialog", "Start New Day"))

        self.plainTextEdit_PtsDay = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEdit_PtsDay.setGeometry(QtCore.QRect(self.x, self.y+120, 121, 31))
        self.plainTextEdit_PtsDay.setPlainText(_translate("Dialog", str(ui.DS.checkScores[0])))
        
        self.plainTextEdit_PtsWeek = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEdit_PtsWeek.setGeometry(QtCore.QRect(self.x, self.y+190, 121, 31))
        self.plainTextEdit_PtsWeek.setPlainText(_translate("Dialog", str(ui.DS.checkScores[1])))
        
        self.plainTextEdit_PtsMonth = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEdit_PtsMonth.setGeometry(QtCore.QRect(self.x, self.y+250, 121, 31))
        self.plainTextEdit_PtsMonth.setPlainText(_translate("Dialog", str(ui.DS.checkScores[2])))
        
        self.label_dayscore = QtWidgets.QLabel(Dialog)
        self.label_dayscore.setGeometry(QtCore.QRect(self.x+30, self.y+100, 70, 20))
        self.label_dayscore.setText(_translate("Dialog", "Day Score"))
        
        self.label_weekscore = QtWidgets.QLabel(Dialog)
        self.label_weekscore.setGeometry(QtCore.QRect(self.x+30, self.y+170, 70, 20))
        self.label_weekscore.setText(_translate("Dialog", "Week Score"))
        
        self.label_monthscore = QtWidgets.QLabel(Dialog)
        self.label_monthscore.setGeometry(QtCore.QRect(self.x+30, self.y+230, 70, 20))
        self.label_monthscore.setText(_translate("Dialog", "Month Score"))

    def StartNewDayAction(self, txtname):
        def SND():
            update_csv()
            ## increment date
            newdate = self.dateEdit.date().addDays(1)
            self.dateEdit.setDate(newdate)
            ## zeroing daymarks
            _translate = QtCore.QCoreApplication.translate
            for i in range(len(ui.AEs)):
                ui.AEs[i].plainTextEdit_daymark.setPlainText(_translate("Dialog","0"))
                ui.AEs[i].stopwatch.set_counter(ui.DS.activityCrono[i])
        return SND

    def UpdatePts(self, Dialog):
       def UP() :  ## if dont use this syntax it complains that couldnt initialize what the function is calling.     
            update_csv()
            ui.DS=DataAndSettings() ## needs to regenerate other attributes
            _translate = QtCore.QCoreApplication.translate
            self.plainTextEdit_PtsDay.setPlainText(_translate("Dialog", str(ui.DS.checkScores[0])))
            self.plainTextEdit_PtsWeek.setPlainText(_translate("Dialog", str(ui.DS.checkScores[1])))
            self.plainTextEdit_PtsMonth.setPlainText(_translate("Dialog", str(ui.DS.checkScores[2])))
            ## update textbox
            user_text = ui.plainTextEdit_box.toPlainText()
            with open('texto.txt', 'w') as textfile:
                textfile.write(user_text)
       return UP            


class AnotherWindow(QtWidgets.QWidget):
    def __init__(self,obj):
        super().__init__()
        self.i=obj.i
        self.float_sw=stopwatch(-20,0,ui.DS.activityCrono[self.i],self.i,Dialog=self)
        self.float_sw.start_pause()
        # enable custom window hint
#        .setWindowFlags(self.windowFlags() | QtCore.Qt.CustomizeWindowHint)

        # disable (but not hide) close button
 #       self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowCloseButtonHint)
        #layout = QtWidgets.QVBoxLayout()
        #self.label = QtWidgets.QLabel("Another Window")
        #layout.addWidget(self.label)
        #self.setLayout(layout)

class Ui_Dialog(object):
    def setupUi(self, Dialog, *args, **kwargs):
        Dialog.setObjectName("Dialog")
        Dialog.resize(1129, 615)
        
        self.DS = DataAndSettings()
        self.buttonBox = QtWidgets.QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QtCore.QRect(340, 560, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
                
        self.plainTextEdit_box = QtWidgets.QPlainTextEdit(Dialog)
        self.plainTextEdit_box.setGeometry(QtCore.QRect(620, 10, 400, 400))
        self.plainTextEdit_box.setObjectName("plainTextEdit_box")
        font = self.plainTextEdit_box.font()      # lineedit current font
        font.setPointSize(12)               # change it's size
        self.plainTextEdit_box.setFont(font)      # set font
        self.font = QtGui.QFont("Arial")
        self.font.setPointSize(14)
        self.plainTextEdit_box.setFont(self.font) 

        ### read text from file
        text=open('texto.txt').read()
        ui.plainTextEdit_box.setPlainText(text);
        
        self.ControlBaP = ControlButtonsAndPoints(440,40)
        
        self.AEs=[]
        for i in range(len(self.DS.settings_activities)):
            self.AEs.append(ActivityEntry(20,20+30*i,i))

        self.graphicsView = QtWidgets.QWidget(Dialog)
        self.graphicsView.setGeometry(QtCore.QRect(20, 330, 600, 235))
        self.graphicsView.setObjectName("graphicsView") 
#        self.main_widget = QtWidgets.QWidget(Dialog)
        l= QtWidgets.QVBoxLayout(self.graphicsView)
       # sc = MyStaticMplCanvas(self.main_widget, width=5, height=4, dpi=100)
        dc = MyDynamicMplCanvas(self.graphicsView)
       # l.addWidget(sc)
        l.addWidget(dc)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def show_new_window(self,checked,obj):
        self.w = AnotherWindow(obj)
        self.w.show()
        #self.w.exit.triggered.connect(printme)


if __name__ == "__main__":
    ## function to read the activities and their respective activityWeight in inner variables
    app = QtWidgets.QApplication(sys.argv)
    Dialog = QtWidgets.QDialog()
    ui = Ui_Dialog()
    ui.setupUi(Dialog)
    
    
    Dialog.show()
    sys.exit(app.exec_()) 
