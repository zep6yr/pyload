#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import tempfile
from time import time
from time import sleep

from Plugin import Plugin

class NetloadIn(Plugin):

    def __init__(self, parent):
        Plugin.__init__(self, parent)
        props = {}
        props['name'] = "NetloadIn"
        props['type'] = "hoster"
        props['pattern'] = r"http://.*netload\.in/"
        props['version'] = "0.1"
        props['description'] = """Netload.in Download Plugin"""
        props['author_name'] = ("spoob", "RaNaN")
        props['author_mail'] = ("spoob@pyload.org")
        self.props = props
        self.parent = parent
        self.html = [None, None, None]
        self.want_reconnect = False
        self.multi_dl = False
        self.init_ocr()

    def prepare(self, thread):
        pyfile = self.parent

        self.want_reconnect = False

        tries = 0

        while not pyfile.status.url:

            self.req.clear_cookies()
            self.download_html()

            pyfile.status.exists = self.file_exists()

            if not pyfile.status.exists:
                raise Exception, "The file was not found on the server."

            pyfile.status.filename = self.get_file_name()

            self.download_html2()

            self.get_wait_time()

            pyfile.status.waituntil = self.time_plus_wait
            pyfile.status.want_reconnect = self.want_reconnect

            thread.wait(self.parent)

            pyfile.status.url = self.get_file_url()

            tries += 1
            if tries > 3:
                raise Exception, "Error while preparing DL, HTML dump: %s %s" % (self.html[0], self.html[1])

        return True


    def download_html(self):
        url = self.parent.url
        self.html[0] = self.req.load(url, cookies=True)

    def download_html2(self):
        
        url_captcha_html = "http://netload.in/" + re.search('(index.php\?id=10&amp;.*&amp;captcha=1)', self.html[0]).group(1).replace("amp;", "")

        for i in range(6):
            self.html[1] = self.req.load(url_captcha_html, cookies=True)

            try:
                captcha_url = "http://netload.in/" + re.search('(share/includes/captcha.php\?t=\d*)', self.html[1]).group(1)
            except:
                url_captcha_html = "http://netload.in/" + re.search('(index.php\?id=10&amp;.*&amp;captcha=1)', self.html[1]).group(1).replace("amp;", "")
                self.html[1] = self.req.load(url_captcha_html, cookies=True)
                captcha_url = "http://netload.in/" + re.search('(share/includes/captcha.php\?t=\d*)', self.html[1]).group(1)
           
            file_id = re.search('<input name="file_id" type="hidden" value="(.*)" />', self.html[1]).group(1)

            captcha_image = tempfile.NamedTemporaryFile(suffix=".png").name
            
            self.req.download(captcha_url, captcha_image, cookies=True)
            captcha = self.ocr.get_captcha(captcha_image)
            self.logger.debug("Captcha %s: %s" % (i, captcha))
            sleep(5)
            self.html[2] = self.req.load("http://netload.in/index.php?id=10", post={"file_id": file_id, "captcha_check": captcha}, cookies=True)

            os.remove(captcha_image)

            if re.search(r"(We will prepare your download..|We had a reqeust with the IP)", self.html[2]) != None:
                return True
    
        raise Exception, "Captcha reading failed"

    def get_file_url(self):
        """ returns the absolute downloadable filepath
        """
        try:
            file_url_pattern = r"<a class=\"Orange_Link\" href=\"(http://.+)\" >Click here"
            search = re.search(file_url_pattern, self.html[2])
            return search.group(1)
        except:
            return None

    def get_wait_time(self):
        wait = int(re.search(r"countdown\((.+),'change\(\)'\)", self.html[2]).group(1))
        self.time_plus_wait = time() + wait / 100

        if re.search(r"We had a reqeust with the IP", self.html[2]):
            self.want_reconnect = True
        
    def get_file_name(self):
        try:
            file_name_pattern = '\t\t\t(.+)<span style="color: #8d8d8d;">'
            return re.search(file_name_pattern, self.html[0]).group(1)
        except:
            return self.parent.url

    def file_exists(self):
        """ returns True or False
        """
        if re.search(r"The file has been deleted", self.html[0]) != None:
            return False
        else:
            return True

    def proceed(self, url, location):

        self.req.download(url, location, cookies=True)
