import httplib, logging, urlparse, urllib, urllib2

HTTP_METHOD_GET = 'GET'
HTTP_METHOD_POST = 'POST'

def DownloadFile(url, file):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    with open(file_name, 'wb') as f:
        meta = u.info()
        file_size = int(meta.getheaders("Content-Length")[0])
        print "Downloading: %s Bytes: %s" % (file_name, file_size)
        
        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = u.read(block_sz)
            if not buffer:
                break
        
            file_size_dl += len(buffer)
            f.write(buffer)
            status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
            status = status + chr(8) * (len(status) + 1)
            print status,

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
        
    def getFormData(self):
        return urllib.urlencode(self.fields)
        # o=[]
        # for key in self.fields:
        #    o+=['{0}={1}'.format(key,urllib2.quote(self.fields[key]))]
        # return '&'.join(o)
        
    def SaveFile(self, filename, mode='wb'):
        with open(filename, mode) as f:
            f.write(self.GetString())
    
    def GetString(self):
        formdata = self.getFormData()
        self.log.debug("GetFormData() = " + formdata);
        # if self.method == HTTP_METHOD_GET:
        #    self.url += "?" + formdata
            
        # web = urllib2.urlopen(self.url)
        uri = urlparse.urlparse(self.url)
        port = ''
        if uri.port:
            port = ':%d' % uri.port
        req = None
        if self.url.startswith('https://'):
            req = httplib.HTTPSConnection(uri.hostname + port)
        else:
            req = httplib.HTTPConnection(uri.hostname + port)
        headers = {"Accept": ','.join(self.accept)}
        if self.method != HTTP_METHOD_GET:
            headers['Content-type'] = "application/x-www-form-urlencoded"
        headers['User-Agent'] = "pybuildtools/0.1"
        if self.url != self.referer:
            headers['Referer'] = self.referer
        
        req.request(self.method, uri.path, formdata, headers)
        response = req.getresponse()

        # form.CookieContainer = new CookieContainer();
        # form.CookieContainer.Add(Cookies);

        # form.Timeout = this.Timeout;
        # form.KeepAlive = false;//KeepAlive;
        # form.Pipelined = false;
        # form.Connection = null;
        # form.AllowAutoRedirect = AutoFollowRedirects;
        # System.Net.ServicePointManager.Expect100Continue = false;
        # Log.Debug("Request data set");

        # tmpPath = path+".tmp"
        # if path.endswith(".tmp"):
        #    tmpPath = path

        self.log.debug("Downloading data from " + self.url + " to memory...")
        # if self.method != HTTP_METHOD_GET:
        self.log.debug("HTTP %d: %s (%s)", response.status, response.reason, self.url);
        if response.status == 302 or response.status == 301:
            # Location: http...
            newurl = response.getheader("Location", '???')
            self.log.warning("Received %d redirect from %s to %s!", response.status, self.url, newurl)
            if self.follow_redirects:
                self.url = newurl
                return self.GetString()
            # self.status=response.status
            # return None
        
        self.status = response.status 
        # Just in case we don't succeed...
        self.log.debug("Content-Length: %s bytes", response.getheader('Content-Length', '???'));
        # expectedContentSize = response.info().getheader('Content-Length');
        
        return response.read()  # Not too complex. 

        """
            Cookies = httpWebResponse.Cookies;
            StringBuilder sb = new StringBuilder();
            //Task.Factory.StartNew(() =>
            //{
            dlThread = new Thread(new ThreadStart(() =>
            {
                Log.Debug("Starting DL thread.");
                bool download = true;
                // If temporary file, or the file exists and we're not supposed to download in that case,
                if (DoneIfFileExists)
                {
                    if (!path.EndsWith(".tmp") && File.Exists(path))
                    {
                        download = false;
                        Log.Debug("File exists, skipping.");
                    }
                }

                bytesDownloaded = 0;
                if (download)
                {
                    byte[] buffer = new byte[1024];
                    Stopwatch watch = Stopwatch.StartNew();
                    try
                    {
                        using (responseStream)
                        {
                            using (FileStream outFile = new FileStream(tmpPath, FileMode.OpenOrCreate))
                            {
                                if (StartingRange > 0)
                                    outFile.Seek(StartingRange, SeekOrigin.Begin);
                                int bytesRead;
                                while ((bytesRead = responseStream.Read(buffer, 0, buffer.Length)) != 0)
                                {
                                    bytesDownloaded += bytesRead;
                                    if (DownloadProgress != null)
                                    {
                                        double seconds = watch.ElapsedMilliseconds / 1000d;
                                        double kbsec = (bytesDownloaded / 1024d) / seconds;
                                        DownloadProgress(bytesDownloaded + StartingRange, httpWebResponse.ContentLength, path, kbsec);
                                    }
                                    outFile.Write(buffer, 0, bytesRead);
                                    //Application.DoEvents();
                                }
                            }
                        }
                    }
                    catch (Exception e)
                    {
                        Log.Error(e.ToString());
                    }
                }
                httpWebResponse.Close();
                if (bytesDownloaded + StartingRange != expectedContentSize)
                {
                    if (retry)
                    {
                        Log.Warning(string.Format("Only downloaded {0}/{1} bytes;  Restarting after 5 seconds!", StartingRange + bytesDownloaded, expectedContentSize));
                        for (int i = 0; i < 5; i++)
                        {
                            Program.CurrentStatus = PatchStatus.WaitingForServer;
                            frmProgress.Instance.StatusText = string.Format("Restarting download in {0} seconds...", 5 - i);
                            Thread.Sleep(new TimeSpan(0, 0, 1)); // 5 seconds
                        }
                        Log.Debug("Ending DL thread (retrying elsewhere!)");
                        if (DownloadComplete != null)
                        {
                            Log.Debug("Sending DownloadIncomplete signal.");
                            DownloadComplete(new DownloadIncompleteException(StartingRange + bytesDownloaded,retry), path);
                        }
                    }
                    else
                    {
                        Log.Debug("Ending DL thread");
                        if (DownloadComplete != null)
                        {
                            Log.Debug("Sending DownloadIncomplete signal.");
                            DownloadComplete(new DownloadIncompleteException(StartingRange + bytesDownloaded,retry), path);
                        }
                    }
                    return;
                }
                if (!path.EndsWith(".tmp"))
                {
                    Log.Debug("Moving temporary file " + tmpPath + " to " + path);
                    try
                    {
                        if (File.Exists(path))
                            File.Delete(path);
                        File.Move(tmpPath, path);
                    }
                    catch (IOException e)
                    {
                        string err = string.Format("File.Move from {0} to {1} failed:\n{2}", tmpPath, path, e);
                        Program.SetError(err);
                        return;
                    }
                }
                if (DownloadComplete != null)
                {
                    DownloadComplete(null, path);
                }
                Log.General("Downloaded " + path + "");
            }));
            dlThread.Name = "Download Thread";
            dlThread.Start();
            """
