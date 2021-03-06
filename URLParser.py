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

try:
	from lxml import html as hlxml
except ImportError:
	print "You do not appear to have lxml installed.\n"
	print "Without lxml, this program cannot run.\n"
	print "You can download lxml at: http://lxml.de/installation.html \n"
	sys.exit()

import urllib3
import os
from multiprocessing import Queue, current_process
if os.name == 'nt':
	from threading import Thread
else:
	from multiprocessing import Process

reload(sys)
sys.setdefaultencoding("utf-8")

class URLParser:
	work_queue = Queue()
	done_queue = Queue()
	processes = []
	workers = 4
	IOError_RepeatCount = 3
	cancel = False
	extensions = [".jpeg", ".jpg", ".png", ".gif"]
	
	proxy = None #If you want to use a HTTP proxy, the format is: http://ipaddress:port
	#eg. proxy = "http://192.168.1.112:8118"
	#This should be saved to & loaded from a config file in the future.
	if proxy != None:
		http = urllib3.ProxyManager(proxy)
	else:
		http = urllib3.PoolManager()

	def Cancel(self, state):
		self.cancel = True
	
	def ContinueDownload(self, url, workdir, frame):
		if not self.cancel:
			filep = URLParser.LastFileInPath(self, url)
			#frame.SetStatusText('Downloading: ' + filep)
			print 'Downloading: ' + filep
			repeat = True
			repeatCount = self.IOError_RepeatCount
			while repeat:
				repeat = False
				try:
					r = self.http.request('GET', url)
					with open(workdir + "/" + filep, "wb") as dlFile:
						dlFile.write(r.data)
				except IOError:
					repeat = True
					repeatCount -= 1
					if repeatCount < 0:
						raise
			return "Page downloaded"
		else:
			return "Page skipped"
	
	def worker(self, work_queue, done_queue, workdir, frame):
		for url in iter(work_queue.get, 'STOP'):
			if self.cancel:
				return False
			status_code = URLParser.ContinueDownload(self, url, workdir, frame)
			done_queue.put("%s - %s got %s." % (current_process().name, url, status_code))
		return True
	
	def arbitraryDownload(self, url, home, frame):
		if (not(url[:7] == "http://" or url[:8] == "https://")): return False
		workDir = home + "/" + URLParser.LastFolderInPath(self, url)
		if not os.path.isdir(workDir):
			os.makedirs(workDir)
		i = 1
		boolContinue = True
		while boolContinue:
			boolContinue = False
			if i < 10:
				padding = "00" + str(i)
			elif i < 100:
				padding = "0" + str(i)
			elif i < 1000:
				padding = str(i)
			else:
				return
			try:
				for ext in self.extensions:
					nUrl = url + str(i) + ext
					print "Testing URL:", nUrl
					data = self.testURL(nUrl)
					if data != False:
						print 'Downloading: ' + padding + ext
						wx.CallAfter(frame.UiPrint, 'Downloading: ' + padding + ext)
						with open(workDir + "/" + padding + ext, "wb") as dlFile:
							dlFile.write(data)
						boolContinue = True
						break
			except Exception, e:
				pass
			i += 1
	
	def downloadFullSeries(self, url, home, frame):

		if url[-1] != "/":
			url += "/"
		try:
			workDir = home + "/" + URLParser.LastFolderInPath(self, url)
		except Exception, e:
			print repr(e)
			return False
		
		if not os.path.isdir(workDir):
			os.makedirs(workDir)
		
		chapters = list(set(self.findChapters(url)))
		chapters.sort(key=LastFolderInPath)
		
		for chapter in chapters:
			if self.cancel:
				break
			print "Indexing " + chapter
			print "-----------------------"
			self.downloadFromURL(chapter, workDir, frame)
			
		print "Finished downloading series"
		print "-----------------------"
		
		return True
	
	def findChapters(self, url):
		
		r = self.http.request('GET', url)

		dom = hlxml.fromstring(r.data)
		aList = dom.xpath('//tr[@class="row lang_English chapter_row"]//a')
		chapters = []

		for a in aList:
			href = a.get('href')
			if href is not None and 'http://bato.to/read/' in href:
				if href[-1] != '/':
					href += '/'
				chapters.append(href)
		
		return chapters

	def downloadFromURL(self, url, home, frame):
		if (not(url[:14] == "http://bato.to" or url[:15] == "https://bato.to" or url[:18] == "http://www.bato.to" or url[:19] == "https://www.bato.to")):
			URLParser.arbitraryDownload(self, url, home, frame)
			return False
		if "bato.to/comic/" in url:
			return URLParser.downloadFullSeries(self, url, home, frame)
		else:
			if (not url[-1] == "/" and not url[-1] == "/1"): url += "/1"
		
		lastPath = URLParser.LastFolderInPath(self, url)
		workDir = home + "/" + lastPath
		if not os.path.isdir(workDir):
			os.makedirs(workDir)
		
		i = 1
		urls = []
		wx.CallAfter(frame.UiPrint, 'Indexing...')
		
		while not self.cancel:
			try:
				arg = URLParser.AbsoluteFolder(self, url) + str(i)
				wx.CallAfter(frame.UiPrint, 'Indexing page ' + str(i))
				print 'Indexing page ' + str(i)
				regex = URLParser.findFormat(self, arg, False)
				if regex:
					extension = os.path.splitext(regex)[1].lower()
					if extension in self.extensions:
						if URLParser.Download(self, regex, workDir, frame):
							urls.append(regex)
					else:
						break
				else:
					break
			except Exception, e:
				break
			i += 1
		
		if self.cancel:
			return False
		
		print "\n"		
		print "Downloading " + lastPath
		print "-----------------------"

		wx.CallAfter(frame.UiPrint, 'Downloading '+lastPath)
		wx.CallAfter(frame.EnableCancel, False)

		if len(urls) > 0:
			for url in urls:
				if self.cancel:
					break
				self.work_queue.put(url)
				
			for w in xrange(self.workers):
				if self.cancel:
					return False
				elif os.name == 'nt':
					p = Thread(target=self.worker, args=(self.work_queue, self.done_queue, workDir, frame))
				else:
					p = Process(target=self.worker, args=(self.work_queue, self.done_queue, workDir, frame))
				p.start()
				self.processes.append(p)
				self.work_queue.put('STOP')

			for p in self.processes:
				if self.cancel:
					return False
				p.join()

			self.done_queue.put('STOP')
			print "\n"

			for status in iter(self.done_queue.get, 'STOP'):
				print status
		else:
			print "No URLs found"
		
		wx.CallAfter(frame.UiPrint, 'Finished')
		wx.CallAfter(frame.EnableCancel, True)
		print "\n"
		print "Finished downloading chapter"
		print "\n"
		
		return not self.cancel and i != 1
	
	def findExtension(self, path, i):

		for s in self.extensions:
			if (self.testURL(path + s) != False):
				return path + s
		
		form = self.FormatNumber(i + 1, 2)
		for s in self.extensions:
			url = path + "-" + form + s
			if (self.testURL(url) != False):
				return url

		return None
	
	def testURL(self, url):
		
		r = self.http.request('GET', url)
		return r.data if r.status == 200 else False
	
	def findFormat(self, url, dire):
		
		r = self.http.request('GET', url)
		dom = hlxml.fromstring(r.data)
		img = dom.xpath(".//*[@id='comic_page']")[0]
		src = img.get('src')

		if src is not None:
			inp = "" if src[0:10] == "http://arc" else "img"
			return self.AbsoluteFolder(src) + inp if dire else src
		
		return False
	
	def Download(self, url, workDir, frame):
		if self.cancel:
			return False
		filep = URLParser.LastFileInPath(self, url)
		lFile = workDir + "/" + filep
		if os.path.isfile(lFile) and os.path.getsize(lFile) == int(http.urlopen('GET', url).headers["Content-Length"]):
			wx.CallAfter(frame.UiPrint, filep + ' already exists')
			return False
		else:
			return True

	def LastFileInPath(self, path):
		start = path.rindex('/')
		return path[start + 1:]
	
	def LastFolderInPath(self, path):
		start = path.rindex('/')
		newPath = path[:start]
		start = newPath.rindex('/')
		return newPath[start + 1:]
	
	def AbsoluteFolder(self, path):
		start = path.rindex('/')
		return path[:start + 1]
	
	def FormatNumber(self, i, places):
		strBuffer = ""
		precede = 0
		
		if (i < 10):
			precede = 1
		elif (i < 100):
			precede = 2
		elif (i < 1000):
			precede = 3
		
		a = 0
		while (a < places - precede):
			strBuffer += "0"
			a += 1
		
		strBuffer += i
		
		return strBuffer

def LastFolderInPath(path):
	start = path.rindex('/')
	newPath = path[:start]
	start = newPath.rindex('/')
	return newPath[start + 1:]
