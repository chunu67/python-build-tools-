'''
HTTP stuff.

Copyright (c) 2015 - 2017 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''
import logging
import urllib.request

from buildtools.bt_logging import log

HTTP_METHOD_GET = 'GET'
HTTP_METHOD_POST = 'POST'


def DownloadFile(url, filename):
    u = urllib.request.urlopen(url)
    with open(filename, 'wb') as f:
        meta = u.info()
        file_size = int(meta["Content-Length"])
        print("Downloading: %s Bytes: %s" % (filename, file_size))

        file_size_dl = 0
        block_sz = 8192
        while True:
            buf = u.read(block_sz)
            if not buf or file_size == file_size_dl:
                break

            file_size_dl += len(buf)
            f.write(buf)
            status = r"%10d/%10d  [%3.2f%%]" % (file_size_dl, file_size, file_size_dl * 100. / file_size)
            status = status + chr(8) * (len(status) + 1)
            print(status,end='\r')
        log.info('Downloaded {} to {} ({}B)'.format(url, filename, file_size_dl))

''' Use requests.
class HTTPFetcher(object):

    def __init__(self, url):
        self.url = url
        self.fields = {}
        self.method = HTTP_METHOD_GET
        self.referer = ''
        self.log = logging.getLogger(__name__)
        self.startingrange = 0
        self.status = -1  # HTTP status code (e.g. 200 for OK)
        self.follow_redirects = False
        self.accept = ['text/plain', 'text/html', 'text/css']
        self.useragent = "pybuildtools/0.1"
        self.debug = False

    def getFormData(self):
        return urllib.parse.urlencode(self.fields)
        # o=[]
        # for key in self.fields:
        #    o+=['{0}={1}'.format(key,urllib2.quote(self.fields[key]))]
        # return '&'.join(o)

    def SaveFile(self, filename, mode='wb'):
        with open(filename, mode) as f:
            f.write(self.GetString())

    def GetString(self):
        formdata = self.getFormData()
        self.log.debug("GetFormData() = " + formdata)
        # if self.method == HTTP_METHOD_GET:
        #    self.url += "?" + formdata

        # web = urllib2.urlopen(self.url)
        uri = urllib.parse.urlparse(self.url)
        port = ''
        if uri.port:
            port = ':%d' % uri.port
        req = None
        if self.url.startswith('https://'):
            req = http.client.HTTPSConnection(uri.hostname + port)
        else:
            req = http.client.HTTPConnection(uri.hostname + port)
        req.debuglevel = 1 if self.debug else 0
        headers = {"Accept": ','.join(self.accept)}
        if self.method != HTTP_METHOD_GET:
            headers['Content-type'] = "application/x-www-form-urlencoded"
        headers['User-Agent'] = self.useragent
        if self.url != self.referer:
            headers['Referer'] = self.referer

        req.request(self.method, uri.path, formdata, headers)
        response = req.getresponse()

        self.log.debug("Downloading data from " + self.url + " to memory...")
        # if self.method != HTTP_METHOD_GET:
        self.log.debug("HTTP %d: %s (%s)", response.status, response.reason, self.url)
        if response.status == 302 or response.status == 301:
            # Location: http...
            newurl = response.getheader("Location", '???')
            self.log.warning(
                "Received %d redirect from %s to %s!", response.status, self.url, newurl)
            if self.follow_redirects:
                self.url = newurl
                return self.GetString()
            # self.status=response.status
            # return None

        self.status = response.status
        # Just in case we don't succeed...
        self.log.debug(
            "Content-Length: %s bytes", response.getheader('Content-Length', '???'))
        # expectedContentSize = response.info().getheader('Content-Length');

        return response.read()  # Not too complex.
'''
