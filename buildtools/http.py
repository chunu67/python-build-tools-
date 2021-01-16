'''
HTTP stuff.

Copyright (c) 2015 - 2021 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
from __future__ import print_function
from tqdm import tqdm

import logging

from buildtools.bt_logging import log

import requests

HTTP_METHOD_GET = 'GET'
HTTP_METHOD_POST = 'POST'


def DownloadFile(url, filename, log_after=True, print_status=True, log_before=True, **kwargs):
    '''
    Download a file from url to filename.

    :param url:
        HTTP URL to download. (SSL/TLS will also work, assuming the cert isn't broken.)
    :param filename:
        Path of the file to download to.
    :param log_after:
        Produce a log statement after the download completes (includes URL).
    :param log_before:
        Produce a log statement before the download starts.
    :param print_status:
        Prints live-updated status of the download progress. (May not work very well for piped or redirected output.)
    :param session:
        Requests session.
    '''
    #kwargs['headers'] = dict(DEFAULT_HEADERS, **kwargs.get('headers', {}))
    r = None
    session = kwargs.pop('session', requests)
    try:
        r = session.get(url, stream=True, **kwargs)
    except requests.exceptions.ConnectionError as e:
        logging.warning(e)
        return False
    except UnicodeEncodeError as e:
        logging.warning(e)
        return False

    if (r.status_code == 404):
        logging.warn('404 - Not Found: %s', url)
        return False
    elif(r.status_code != 200):
        logging.warn("Error code: {0}".format(r.status_code))
        return False
    with open(filename, 'wb') as f:
        file_size = int(r.headers.get('Content-Length', '-1'))
        if file_size < 0:
            if 'Content-Length' not in r.headers:
                log.warn('Content-Length header was not received, expect progress bar weirdness.')
            else:
                log.warn('Content-Length header has invalid value: %r', r.headers['Content-Length'])
        if log_before:
            log.info("Downloading: %s Bytes: %s" % (filename, file_size if file_size > -1 else 'UNKNOWN'))

        file_size_dl = 0
        block_sz = 8192

        progress = tqdm(total=file_size, unit_scale=True, unit_divisor=1024, unit='B', leave=False) if print_status else None
        for buf in r.iter_content(block_sz):
            if not buf or file_size == file_size_dl:
                break

            buf_len = len(buf)
            file_size_dl += buf_len
            f.write(buf)
            if print_status:
                #status = r"%10d/%10d  [%3.2f%%]" % (file_size_dl, file_size, file_size_dl * 100. / file_size)
                progress.update(buf_len)
                #status = status + chr(8) * (len(status) + 1)  - pre-2.6 method
                #print(status, end='\r')
        if progress is not None:
            progress.close()
    if log_after:
        log.info('Downloaded %s to %s (%dB)', url, filename, file_size_dl)
