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

from buildtools.bt_logging import log
from buildtools.utils import is_python_3

if is_python_3():
    from urllib.request import urlopen
else:
    from urllib import urlopen  # ??

HTTP_METHOD_GET = 'GET'
HTTP_METHOD_POST = 'POST'


def DownloadFile(url, filename, log_after=True, print_status=True, log_before=True):
    u = urlopen(url)
    with open(filename, 'wb') as f:
        meta = u.info()
        file_size = int(meta["Content-Length"])
        if log_before:
            log.info("Downloading: %s Bytes: %s" % (filename, file_size))

        file_size_dl = 0
        block_sz = 8192
        while True:
            buf = u.read(block_sz)
            if not buf or file_size == file_size_dl:
                break

            file_size_dl += len(buf)
            f.write(buf)
            if print_status:
                status = r"%10d/%10d  [%3.2f%%]" % (file_size_dl, file_size, file_size_dl * 100. / file_size)
                status = status + chr(8) * (len(status) + 1)
                print(status, end='\r')
        if log_after:
            log.info('Downloaded {} to {} ({}B)'.format(url, filename, file_size_dl))
