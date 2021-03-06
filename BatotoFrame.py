#!/usr/bin/python2.7 -tt

from __future__ import unicode_literals
import sys
if sys.version_info < (2, 7):
	print "Must use python 2.7 or greater\n"
	sys.exit()

try:
	import wx
except ImportError:
	print "You do not appear to have wxpython installed.\n"
	print "Without wxpython, this program cannot run.\n"
	print "You can download wxpython at: http://www.wxpython.org/download.php#stable \n"
	sys.exit()
from URLParser import URLParser
import os
from os.path import expanduser, isfile, join
from threading import Thread

FILE_IMPORT = 650
FILE_EXPORT = 651
FILE_SAVE = 661
FILE_CLOSE = 666

FILE_PARSE_FIRST = 662
FILE_PARSE_LAST = 663
FILE_PARSE_ALL = 664

FILE_CLEAR_FIRST = 668
FILE_CLEAR_LAST = 669
FILE_CLEAR_ALL = 670

SETTING_ORDER = 680
SETTING_ORDER_MENU = 681

HOME_DIR = expanduser("~")
if os.name == 'nt':
	HOME_DIR = join(HOME_DIR, "Documents")
SAVE_FILE = join(HOME_DIR, "batotolist.txt")

WIDTH_MIN = 500
WIDTH_INITIAL = 500
HEIGHT_MIN = 400
HEIGHT_INITIAL = 400

class BatotoThread(Thread):
	
	def __init__(self, pType, lines, frame, order=True):
		Thread.__init__(self)
		self.pType = pType
		self.lines = lines
		self.parser = URLParser()
		self.frame = frame
		self.order = order
		self.start() #start automatically
	
	def run(self):
		wx.CallAfter(self.frame.SetLocked, True)
		if self.pType == 0:
			for line in self.lines:
				if self.parser.cancel:
					break
				elif self.order:
					self.ParseFirstThread(line)
				else:
					self.ParseLastThread(line)
		elif self.pType == 1:
			self.ParseLastThread(self.lines)
		else:
			self.ParseFirstThread(self.lines)
		wx.CallAfter(self.frame.SetLocked, False)
		if self.parser.cancel:
			wx.CallAfter(self.frame.UiPrint, '')

	def ParseFirstThread(self, line):
		self.ParseLine(line)
		if not self.parser.cancel:
			wx.CallAfter(self.frame.UiClear, self.order)

	def ParseLastThread(self, line):
		self.ParseLine(line)
		if not self.parser.cancel:
			wx.CallAfter(self.frame.UiClear, self.order)

	def ParseLine(self, line):
		if self.parser.testURL(line):
			global HOME_DIR
			self.parser.downloadFromURL(line, HOME_DIR, self.frame)

class BatotoFrame(wx.Frame):

	def __init__(self, *args, **kwargs):
		super(BatotoFrame, self).__init__(*args, **kwargs)

		self.Bind(wx.EVT_CLOSE, self.Exit)
		self.SetTitle("Batoto Downloader")
		self.SetIcon(wx.Icon('jr.png', wx.BITMAP_TYPE_PNG))
		self.SetSize((WIDTH_INITIAL,HEIGHT_INITIAL))
		self.SetMinSize((WIDTH_MIN,HEIGHT_MIN))
		self.InitUI()
		self.thread = None

	def InitUI(self):

		self.ConstructMenu()

		panel = wx.Panel(self)
		hbox = wx.BoxSizer(wx.HORIZONTAL)
		fgs = wx.FlexGridSizer(2, 2, 9, 25)

		title = wx.StaticText(panel, label="URL:")

		self.inputText = wx.TextCtrl(panel)
		self.URLList = wx.TextCtrl(panel, style=wx.TE_MULTILINE|wx.TE_DONTWRAP)
		self.URLList.SetEditable(False)
		self.btnBox = self.ConstructButtons(panel)

		fgs.AddMany([(title), (self.inputText, 1, wx.EXPAND), self.btnBox, (self.URLList, 2, wx.EXPAND)])

		fgs.AddGrowableRow(1, 1)
		fgs.AddGrowableCol(1, 1)

		hbox.Add(fgs, proportion=1, flag=wx.ALL|wx.EXPAND, border=5)
		panel.SetSizer(hbox)

		self.LoadListFromFile()
		self.Show(True)

	def ConstructMenu(self):

		menubar = wx.MenuBar()
		menuFile = wx.Menu()
		menuParse = wx.Menu()
		menuClear = wx.Menu()
		menuSettings = wx.Menu()

		menuItemImport = wx.MenuItem(menuFile, FILE_IMPORT, '&Import\tCtrl+I')
		menuItemExport = wx.MenuItem(menuFile, FILE_EXPORT, '&Export\tCtrl+E')
		menuItemSave = wx.MenuItem(menuFile, FILE_SAVE, '&Save\tCtrl+S')
		menuItemQuit = wx.MenuItem(menuFile, FILE_CLOSE, '&Quit\tStrl+Q')

		menuItemParseFirst = wx.MenuItem(menuParse, FILE_PARSE_FIRST, 'Parse &First')
		menuItemParseLast = wx.MenuItem(menuParse, FILE_PARSE_LAST, 'Parse &Last')
		menuItemParseAll = wx.MenuItem(menuParse, FILE_PARSE_ALL, 'Parse &All')

		menuItemClearFirst = wx.MenuItem(menuClear, FILE_CLEAR_FIRST, 'Clear &First')
		menuItemClearLast = wx.MenuItem(menuClear, FILE_CLEAR_LAST, 'Clear &Last')
		menuItemClearAll = wx.MenuItem(menuClear, FILE_CLEAR_ALL, 'Clear &All')
		
		menuSettingsOrder = wx.Menu()
		self.menuItemSettingsOrderNew = menuSettingsOrder.AppendRadioItem(SETTING_ORDER, 'Newest First')
		self.menuItemSettingsOrderOld = menuSettingsOrder.AppendRadioItem(SETTING_ORDER, 'Oldest First')
		
		menuSettingsOrder.Check(self.menuItemSettingsOrderNew.GetId(), True)

		#menuItemOpen.SetBitmap(wx.Bitmap('file.png'))

		menuFile.AppendItem(menuItemImport)
		menuFile.AppendItem(menuItemExport)
		menuFile.AppendSeparator()
		menuFile.AppendItem(menuItemSave)
		menuFile.AppendSeparator()
		menuFile.AppendItem(menuItemQuit)

		menuParse.AppendItem(menuItemParseFirst)
		menuParse.AppendItem(menuItemParseLast)
		menuParse.AppendItem(menuItemParseAll)

		menuClear.AppendItem(menuItemClearFirst)
		menuClear.AppendItem(menuItemClearLast)
		menuClear.AppendItem(menuItemClearAll)
		
		menuSettings.AppendMenu(SETTING_ORDER_MENU, '&Parse All Order', menuSettingsOrder)

		menubar.Append(menuFile, '&File')
		menubar.Append(menuParse, '&Parse')
		menubar.Append(menuClear, '&Clear')
		menubar.Append(menuSettings, '&Settings')

		self.Bind(wx.EVT_MENU, self.Import, id=FILE_IMPORT)
		self.Bind(wx.EVT_MENU, self.Export, id=FILE_EXPORT)
		self.Bind(wx.EVT_MENU, self.Save, id=FILE_SAVE)
		self.Bind(wx.EVT_MENU, self.Exit, id=FILE_CLOSE)

		self.Bind(wx.EVT_MENU, self.ParseFirst, id=FILE_PARSE_FIRST)
		self.Bind(wx.EVT_MENU, self.ParseLast, id=FILE_PARSE_LAST)
		self.Bind(wx.EVT_MENU, self.ParseAll, id=FILE_PARSE_ALL)

		self.Bind(wx.EVT_MENU, self.ClearFirst, id=FILE_CLEAR_FIRST)
		self.Bind(wx.EVT_MENU, self.ClearLast, id=FILE_CLEAR_LAST)
		self.Bind(wx.EVT_MENU, self.ClearAll, id=FILE_CLEAR_ALL)

		self.statusbar = self.CreateStatusBar()
		self.SetMenuBar(menubar)

	def ConstructButtons(self, panel):
		btnBox = wx.BoxSizer(wx.VERTICAL)
		self.btn1 = wx.Button(panel, label='Add URL')
		self.btn2 = wx.Button(panel, label='Parse First')
		self.btn3 = wx.Button(panel, label='Parse Last')
		self.btn4 = wx.Button(panel, label='Parse All')
		self.btn5 = wx.Button(panel, label='Clear First')
		self.btn6 = wx.Button(panel, label='Clear Last')
		self.btn7 = wx.Button(panel, label='Clear All')
		self.btn8 = wx.Button(panel, label='Cancel')
		self.btn1.Bind(wx.EVT_BUTTON, self.AddURL)
		self.btn2.Bind(wx.EVT_BUTTON, self.ParseFirst)
		self.btn3.Bind(wx.EVT_BUTTON, self.ParseLast)
		self.btn4.Bind(wx.EVT_BUTTON, self.ParseAll)
		self.btn5.Bind(wx.EVT_BUTTON, self.ClearFirst)
		self.btn6.Bind(wx.EVT_BUTTON, self.ClearLast)
		self.btn7.Bind(wx.EVT_BUTTON, self.ClearAll)
		self.btn8.Bind(wx.EVT_BUTTON, self.Cancel)
		self.btn8.Disable()
		btnBox.AddMany([(self.btn1, 1, wx.EXPAND), (self.btn2, 1, wx.EXPAND), (self.btn3, 1, wx.EXPAND), (self.btn4, 1, wx.EXPAND), (self.btn5, 1, wx.EXPAND), (self.btn6, 1, wx.EXPAND), (self.btn7, 1, wx.EXPAND), (self.btn8, 1, wx.EXPAND)])
		return btnBox

	def Import(self, e):
		openFileDialog = wx.FileDialog(self, "Open Text file", "", "", "Text files (*.txt)|*.txt", wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
		
		if (openFileDialog.ShowModal() == wx.ID_CANCEL):
			return
		self.URLList.LoadFile(openFileDialog.GetPath())

	def Export(self, e):
		saveFileDialog = wx.FileDialog(self, "Save Text file", "", "", "Text file (*.txt)|*.txt", wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
		
		if (saveFileDialog.ShowModal() == wx.ID_CANCEL):
			return
		try:
			self.URLList.SaveFile(saveFileDialog.GetPath())
		except Exception, e:
			wx.MessageDialog(None, 'Error saving file', 'Error', wx.OK | wx.ICON_ERROR).ShowModal()

	def Save(self, e):
		self.URLList.SaveFile(SAVE_FILE)

	def Exit(self, e):
		wx.Exit()

	def AddURL(self, e):
		line = self.inputText.GetLineText(0)
		if (line[:4] == "http" or line[:4] == "www."):
			self.inputText.Clear()
			self.DirectlyAddURL(line)
			self.Save(e)

	def DirectlyAddURL(self, line):
		if (len(self.URLList.GetLineText(0)) > 0):
			self.URLList.AppendText("\n")
		self.URLList.AppendText(line)
	
	def ParseFirst(self, e):
		totalLines = self.UiGetNumberOfLines()
		if (totalLines > 0):
			line = self.URLList.GetLineText(0)
			self.thread = BatotoThread(2, line, self)

	def ParseLast(self, e):
		totalLines = self.UiGetNumberOfLines()
		if totalLines > 0:
			line = self.URLList.GetLineText(totalLines - 1)
			self.thread = BatotoThread(1, line, self)

	def ParseAll(self, e):
		totalLines = self.UiGetNumberOfLines()
		if (totalLines > 0):
			lines = []
			oldOrder = self.menuItemSettingsOrderOld.IsChecked()
			if oldOrder:
				count = 0
				while count < totalLines:
					lines.append(self.URLList.GetLineText(count))
					count += 1
			else:
				count = totalLines - 1
				while count >= 0:
					lines.append(self.URLList.GetLineText(count))
					count -= 1
			print lines
			self.thread = BatotoThread(0, lines, self, not oldOrder)

	def Cancel(self, e):
		if self.thread != None:
			self.thread.parser.Cancel(True)
			self.btn8.Disable()
	
	def EnableCancel(self, enable):
		if enable:
			self.btn8.Enable()
		else:
			self.btn8.Disable()

	def ClearFirst(self, e):
		end = self.URLList.GetLineLength(0) + 1
		self.URLList.Remove(0,end)
		self.Save(e)

	def ClearLast(self, e):
		totalLines = self.UiGetNumberOfLines()
		if totalLines < 2:
			self.ClearAll(e)
		else:
			length = self.URLList.GetLineLength(totalLines - 1) + 1
			end = self.URLList.GetLastPosition()
			start = end - length
			self.URLList.Remove(start,end)
			self.Save(e)

	def ClearAll(self, e):
		self.URLList.Clear()
		self.Save(e)

	def LoadListFromFile(self):
		if isfile(SAVE_FILE):
			self.URLList.LoadFile(SAVE_FILE)

	def SetLocked(self, lock):
		if lock:
			self.btn1.Disable()
			self.btn2.Disable()
			self.btn3.Disable()
			self.btn4.Disable()
			self.btn5.Disable()
			self.btn6.Disable()
			self.btn7.Disable()
			self.btn8.Enable()
		else:
			self.btn1.Enable()
			self.btn2.Enable()
			self.btn3.Enable()
			self.btn4.Enable()
			self.btn5.Enable()
			self.btn6.Enable()
			self.btn7.Enable()
			self.btn8.Disable()
			self.thread.parser.Cancel(False)
	
	def UiPrint(self, text):
		self.statusbar.SetStatusText(text)
	
	def UiClear(self, last):
		if last:
			self.ClearLast(None)
		else:
			self.ClearFirst(None)

	def UiGetLine(self, lineNum):
		return self.URLList.GetLineText(lineNum)

	def UiGetNumberOfLines(self):
		if self.URLList.GetValue() == '':
			return 0
		else:
			return self.URLList.GetNumberOfLines()
