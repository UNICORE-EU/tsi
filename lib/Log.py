#
# Simple logger writing to syslog (or console)
#
from os import getpid
from sys import stdout
from syslog import closelog, openlog, syslog, LOG_DEBUG, LOG_ERR, LOG_INFO, LOG_WARNING

class Logger(object):

    def __init__(self, name="TSI", verbose=False, use_syslog=True):
        self.verbose = verbose
        self.use_syslog = use_syslog
        self.name = name
        if use_syslog:
            try:
                openlog(name)
            except:
                self.use_syslog = False

    def out(self, level, message):
        print ("[%s][%s][%s] %s" % (level, self.name, getpid(), message))
        stdout.flush()

    def reinit(self, name="TSI-worker", verbose=False, use_syslog=True):
        self.verbose = verbose
        self.use_syslog = use_syslog
        self.name = name
        if self.use_syslog:
            closelog()
            try:
                openlog(name)
            except:
                self.use_syslog = False

    def error(self, message):
        if self.use_syslog:
            syslog(LOG_ERR, str(message))
        else:
            self.out("ERROR", str(message))

    def warning(self, message):
        if self.use_syslog:
            syslog(LOG_WARNING, str(message))
        else:
            self.out("WARN", str(message))

    def info(self, message):
        if self.use_syslog:
            syslog(LOG_INFO, str(message))
        else:
            self.out("INFO", str(message))

    def debug(self, message):
        if not self.verbose:
            return
        if self.use_syslog:
            syslog(LOG_DEBUG, str(message))
        else:
            self.out("DEBUG", str(message))
