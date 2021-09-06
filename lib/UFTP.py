"""
    UFTP file transfer functionality and helper functions
"""

from ftplib import FTP
from os import environ
import sys

from Utils import expand_variables, extract_parameter, run_command

def open_session(host, port, secret):
    ''' open an FTP session at the given UFTP server 
        and return the session object '''
    ftp = FTP()
    ftp.connect(host, port)
    print(ftp.getwelcome())
    print(ftp.login("anonymous", secret))
    return ftp

def uftp(message, connector, config, LOG):
    """
    (TBD: Launches a child process that) reads/writes a file via UFTP
    
    The message sent by the XNJS is scanned for:
        TSI_UFTP_HOST     - UFTP server to connect to
        TSI_UFTP_PORT     - UFTP listen port
        TSI_UFTP_SECRET   - one-time password to use for logging in
        TSI_UFTP_MODE     - GET, PUT
        TSI_UFTP_REMOTE_FILE     - remote file to read from / write to
        TSI_UFTP_LOCAL_FILE          - local file to read from / write to   
        TSI_START         - start byte (defaults to '0')
        TSI_LENGTH        - how many bytes to transfer (defaults to -1 i.e. the whole file)
    """

    host = extract_parameter(message, 'UFTP_HOST')
    port = int(extract_parameter(message, 'UFTP_PORT'))
    secret = extract_parameter(message, 'UFTP_SECRET')
    mode = extract_parameter(message, 'UFTP_MODE')
    remote_path = expand_variables(extract_parameter(message, 'UFTP_REMOTE_FILE'))
    local_path = expand_variables(extract_parameter(message, 'UFTP_LOCAL_FILE'))
    start = int(extract_parameter(message, 'START', "0"))
    length = int(extract_parameter(message, 'LENGTH', "-1"))
    
    uspace_dir = extract_parameter(message, "USPACE_DIR")
    stdout = extract_parameter(message, "STDOUT", "stdout")
    pid_file = extract_parameter(message, "PID_FILE", "UNICORE_SCRIPT_PID")
    exit_code_file = extract_parameter(message, "EXIT_CODE_FILE", "UNICORE_SCRIPT_EXIT_CODE")

    uftp_client = __file__
    
    cmds = [message,
            "export UFTP_HOST=%s" % host,
            "export UFTP_PORT=%s" % port,
            "export UFTP_SECRET=%s" % secret,
            "export UFTP_MODE=%s" % mode,
            "export UFTP_REMOTE_FILE=%s" % remote_path,
            "export UFTP_LOCAL_FILE=%s" % local_path,
            "export PYTHONPATH=%s" % environ["PYTHONPATH"],
            "cd %s" % uspace_dir,
            "{ python3 %s > %s 2>&1 ; echo $? > %s ; } & echo $! > %s " % (uftp_client, stdout, exit_code_file, pid_file)
            ]
    
    cmd = ""
    for c in cmds:
        cmd += c + u"\n"
    
    children = config.get('tsi.NOBATCH.children', None)
    (success, reply) = run_command(cmd, True, children)
    


def main(argv=None):
    """
    run UFTP client code
    """
    
    host = environ['UFTP_HOST']
    port = int(environ['UFTP_PORT'])
    secret = environ['UFTP_SECRET']
    remote_path = environ['UFTP_REMOTE_FILE']
    local_path = environ['UFTP_LOCAL_FILE']
    mode = environ['UFTP_MODE']
    
    print("Connecting to UFTPD %s:%s" % (host, port))
    
    ftp = open_session(host, port, secret)
    
    if "GET"==mode:
        print("GET %s -> %s" % (remote_path, local_path))
        with open(local_path, 'wb') as fp:
            reply = ftp.retrbinary('RETR %s' % remote_path, fp.write)
            print(reply)
            try:
                ftp.quit()
            except:
                pass
    else:
        print("PUT %s -> %s" % (local_path, remote_path))
        with open(local_path, 'rb') as fp:
            reply = ftp.storbinary('STOR %s' % remote_path, fp)
            print(reply)
            try:
                ftp.quit()
            except:
                pass
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
    