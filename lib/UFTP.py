"""
    UFTP file transfer functionality and helper functions
"""

from ftplib import FTP
from os import environ
from pathlib import Path
import sys

from Connector import Connector
from Log import Logger
from Utils import expand_variables, extract_parameter, run_command

def open_session(host, port, secret):
    ''' open an FTP session at the given UFTP server
        and return the session object '''
    ftp = FTP()
    ftp.connect(host, port)
    log_reply(ftp.getwelcome())
    log_reply(ftp.login("anonymous", secret))
    return ftp

def log_reply(reply):
    print("uftpd: %s" % reply)

def uftp(message: str, connector: Connector, config: dict, LOG: Logger):
    """
    Launches a child process that reads/writes a file via UFTP

    The message sent by the UNICORE/X is scanned for:
        TSI_UFTP_HOST        - UFTP server to connect to
        TSI_UFTP_PORT        - UFTP listen port
        TSI_UFTP_SECRET      - one-time password to use for logging in
        TSI_UFTP_OPERATION   - GET, PUT
        TSI_UFTP_WRITE_MODE  - FULL, PARTIAL
        TSI_UFTP_REMOTE_FILE - remote file to read from / write to
        TSI_UFTP_LOCAL_FILE  - local file to read from / write to
        TSI_UFTP_OFFSET      - start byte (defaults to '0')
        TSI_UFTP_LENGTH      - how many bytes to transfer (defaults to -1 i.e. the whole file)
        TSI_USPACE_DIR       - working directory for the child process
        TSI_OUTCOME_DIR      - directory for the PID, stdout, stderr, exit code
        TSI_STDOUT           - file to write standard output to
        TSI_STDERR           - file to write standard error to
    """

    host = extract_parameter(message, 'UFTP_HOST')
    port = int(extract_parameter(message, 'UFTP_PORT'))
    secret = extract_parameter(message, 'UFTP_SECRET')
    operation = extract_parameter(message, 'UFTP_OPERATION')
    write_mode = extract_parameter(message, 'UFTP_WRITE_MODE', "FULL")
    remote_path = expand_variables(extract_parameter(message, 'UFTP_REMOTE_FILE'))
    local_path = expand_variables(extract_parameter(message, 'UFTP_LOCAL_FILE'))
    offset = int(extract_parameter(message, 'UFTP_OFFSET', "0"))
    length = int(extract_parameter(message, 'UFTP_LENGTH', "-1"))

    uspace_dir = extract_parameter(message, "USPACE_DIR")
    outcome_dir = extract_parameter(message, "OUTCOME_DIR")
    stdout = outcome_dir + "/" + extract_parameter(message, "STDOUT", "stdout")
    stderr = outcome_dir + "/" + extract_parameter(message, "STDERR", "stderr")
    pid_file = outcome_dir + "/" + extract_parameter(message, "PID_FILE", "UNICORE_SCRIPT_PID")
    exit_code_file = outcome_dir + "/" + extract_parameter(message, "EXIT_CODE_FILE", "UNICORE_SCRIPT_EXIT_CODE")

    uftp_client = __file__

    cmds = [message,
            "export UFTP_HOST=%s" % host,
            "export UFTP_PORT=%s" % port,
            "export UFTP_SECRET=%s" % secret,
            "export UFTP_OPERATION=%s" % operation,
            "export UFTP_WRITE_MODE=%s" % write_mode,
            "export UFTP_OFFSET=%s" % offset,
            "export UFTP_LENGTH=%s" % length,
            "export UFTP_WRITE_MODE=%s" % write_mode,
            "export UFTP_REMOTE_FILE=%s" % remote_path,
            "export UFTP_LOCAL_FILE=%s" % local_path,
            "export PYTHONPATH=%s" % environ["PYTHONPATH"],
            "cd %s" % uspace_dir,
            "{ python3 %s >> %s 2 > %s ; echo $? > %s ; } & echo $! > %s " % (uftp_client, stdout, stderr, exit_code_file, pid_file)
            ]

    cmd = ""
    for c in cmds:
        cmd += c + u"\n"

    child_pids = config.get('tsi.child_pids', None)
    use_login_shell = config.get('tsi.use_login_shell', True)
    (success, reply) = run_command(cmd, True, child_pids, use_login_shell)
    if not success:
        connector.failed("Failed to launch uftp command: %s" % reply)



def main():
    """
    run UFTP client code
    """
    host = environ['UFTP_HOST']
    port = int(environ['UFTP_PORT'])
    secret = environ['UFTP_SECRET']
    remote_path = environ['UFTP_REMOTE_FILE']
    local_path = environ['UFTP_LOCAL_FILE']
    operation = environ['UFTP_OPERATION']
    write_mode = environ['UFTP_WRITE_MODE']
    offset = int(environ.get('UFTP_OFFSET', "0"))
    length  = int(environ.get('UFTP_LENGTH', "-1"))

    print("Connecting to UFTPD %s:%s" % (host, port))

    ftp = open_session(host, port, secret)

    partial = "PARTIAL"==write_mode

    if "GET"==operation:
        print("GET %s -> %s" % (remote_path, local_path))
        if partial:
            _mode = "r+b"
            Path(local_path).touch()
        else:
            _mode = "wb"
        with open(local_path, _mode) as fp:
            if offset>0 or length>-1:
                if partial:
                    fp.seek(offset)
                if length>-1:
                    reply = ftp.sendcmd("RANG %s %s"% (offset, length))
                    if not reply.startswith("350"):
                        raise IOError("Error setting RANG: %s" % reply)
                    log_reply(reply)
            if length>-1:
                reply = ftp.retrbinary('RETR %s' % remote_path, fp.write)
            else:
                reply = ftp.retrbinary('RETR %s' % remote_path, fp.write, rest=offset)
            log_reply(reply)
            try:
                ftp.quit()
            except:
                pass
    else:
        print("PUT %s -> %s" % (local_path, remote_path))
        with open(local_path, 'rb') as fp:
            if offset>0 or length>-1:
                fp.seek(offset)
                if not partial:
                    offset = 0
                reply = ftp.sendcmd("RANG %s %s"% (offset, length))
                if not reply.startswith("350"):
                    raise IOError("Error setting RANG: %s" % reply)
                log_reply(reply)
            reply = ftp.storbinary('STOR %s' % remote_path, fp)
            log_reply(reply)
            try:
                ftp.quit()
            except:
                pass
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)