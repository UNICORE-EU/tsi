"""
Interface to PAM functions via ctypes
"""
import ctypes
import os
import sys

LIBC = "libc.so.6"
LIBPAM = "libpam.so.0"

# refers to settings in /etc/pam.d/
PAM_MODULE = "unicore-tsi"

PAM_ESTABLISH_CRED = 0x1
PAM_SUCCESS = 0
PAM_ERROR_MSG = 3
PAM_TEXT_INFO = 4

class pam_message(ctypes.Structure):
    _fields_ = [("msg_style", ctypes.c_int), ("msg", ctypes.c_char_p)]

class pam_response(ctypes.Structure):
    _fields_ = [("resp", ctypes.c_char_p), ("resp_retcode", ctypes.c_int)]

pam_conv_conv_fct = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.POINTER(pam_message)),
                                     ctypes.POINTER(ctypes.POINTER(pam_response)),
                                     ctypes.c_void_p)

class pam_conv(ctypes.Structure):
    _fields_ = [("conv", pam_conv_conv_fct), ("appdata_ptr", ctypes.c_void_p)]

class PAM(object):
    def __init__(self, LOG, module_name=PAM_MODULE):
        self.LOG = LOG
        self.MODULE = ctypes.c_char_p(bytes(module_name, encoding="ascii"))
        libc = ctypes.CDLL(LIBC)
        libc.malloc.restype  = ctypes.c_void_p
        libc.malloc.argtypes = [ctypes.c_size_t]
        libc.memset.restype  = ctypes.c_void_p
        libc.memset.argtypes = [ctypes.c_void_p, ctypes.c_char, ctypes.c_size_t]
        libc.memcpy.restype  = ctypes.c_void_p
        libc.memcpy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
        libc.strdup.restype  = ctypes.c_void_p  # On purpose
        libc.strdup.argtypes = [ctypes.c_char_p]
        libpam = ctypes.CDLL(LIBPAM, mode = ctypes.RTLD_GLOBAL)
        libpam.pam_strerror.restype = ctypes.c_char_p

        def convcb(num_msg, msg, resp, appdata_ptr):
            n = num_msg*ctypes.sizeof(pam_response)
            x = libc.memset(libc.malloc(n), ctypes.c_char('0'), n)
            resp[0] = ctypes.cast(x, ctypes.POINTER(pam_response))
            for i in range(num_msg):
                if PAM_ERROR_MSG == msg[0][i].msg_style:
                    self.LOG.error("%s %s %s" % (i, msg[0][i], "PAM_ERROR_MSG"))
                if PAM_TEXT_INFO == msg[0][i].msg_style:
                    self.LOG.debug("%s %s %s" % (i, msg[0][i], "PAM_TEXT_INFO"))
            return PAM_SUCCESS

        self.conv = pam_conv()
        self.conv.conv = pam_conv_conv_fct(convcb)
        self.libpam = libpam
        self.pamh = ctypes.c_void_p()

    def check_pam_error(self, method, err, msg):
        if PAM_SUCCESS != err:
            self.LOG.debug("Error %d invoking '%s': %s" % (err, method, msg))

    def open_session(self, username):
        USER = ctypes.c_char_p(bytes(username, encoding="ascii"))
        err = self.libpam.pam_start(self.MODULE, USER, ctypes.byref(self.conv), ctypes.byref(self.pamh))
        self.check_pam_error("pam_start", err, self.libpam.pam_strerror(self.pamh, err))
        err = self.libpam.pam_open_session(self.pamh, 0)
        self.check_pam_error("pam_open_session", err, self.libpam.pam_strerror(self.pamh, err))

    def close_session(self):
        err = self.libpam.pam_close_session(self.pamh, 0)
        self.check_pam_error("pam_close_session", err, self.libpam.pam_strerror(self.pamh, err))
        err = self.libpam.pam_end(self.pamh, 0)
        self.check_pam_error("pam_end", err, self.libpam.pam_strerror(self.pamh, err))

#
# Test & demonstration code
#
# To launch a task ('sleep 120')
# in a PAM session for the user:
#
# $> export PYTHONPATH=lib
# $> sudo python3 lib/PAM.py <userid>
#
if __name__ == "__main__":
    USER = "schuller1"

    config = {"tsi.enforce_os_gids": False,
              "tsi.use_id_to_resolve_gids": True,
              "tsi.fail_on_invalid_gids": True }
    import BecomeUser, PAM, Log

    argv = sys.argv
    if len(argv)>1:
        USER = argv[1]

    LOG = Log.Logger(verbose=True, use_syslog=False)
    LOG.info("Starting test - lauch task for %s" % USER)
    BecomeUser.initialize(config, LOG)

    pam = PAM.PAM(LOG)

    # must fork to avoid the main process
    # getting put into the user slice
    pid = os.fork()
    if pid != 0:
        # wait for the child process to
        # launch the user task
        os.waitpid(pid, 0)
    else:
        # child process - open session and then switch UID
        pam.open_session(USER)
        BecomeUser.become_user(USER, ["NONE"], config, LOG)
        # launch task in the background
        Utils.run_command("sleep 120", discard=True)
        LOG.info("Successfully launched 'sleep 120' for user %s" % USER)
        # switch back to privileged
        BecomeUser.restore_id(config)
        # close session
        pam.close_session()
        os._exit(0)
