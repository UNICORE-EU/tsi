"""
 helper functions
"""


import re
import os
import string
import subprocess

from random import choice

def encode(message):
    if type(message) is not type(u" "):
        message = str(message, "utf-8")
    return message


def extract_parameter(message: str, parameter: str, default_value:str = None) -> str:
    """
    Extracts a value that is given in the form '#TSI_<parameter> <value>\n'
    from the message. Returns the value or None if it is not present or empty.
    """
    result = re.search(r".*^#TSI_%s (.*)\n.*" % parameter, message, re.M)
    if result is None or result.group(1)=='':
        value = default_value
    else:
        value = result.group(1)
    return value


def extract_number(message: str, parameter: str) -> int:
    """
    Extracts a value that is given in the form '#TSI_<parameter> <value>\n'
    from the message. Returns the value as an integer, or -1 if 
    it is not given or not an integer.
    """
    result = extract_parameter(message, parameter)
    try:
        value = int(float(result))
    except:
        value = -1
    return value


def expand_variables(message: str) -> str:
    """
    Expands $HOME and $USER into the values from the current environment
    """
    message = message.replace("$HOME", os.environ.get('HOME', ""))
    message = message.replace("$LOGNAME", os.environ.get('LOGNAME', ""))
    return message.replace("$USER", os.environ.get('USER', ""))


def addperms(path: str, mode: int):
    """
    Adds the mode permissions to those which are already set for the file.
    """
    curmode = os.stat(path)[0]
    mode = curmode | mode
    os.chmod(path, mode)


def run_command(cmd: str, discard=False, child_pids=None, login_shell=True):
    """
    Runs command, capturing the output if the discard flag is True.
    Returns a success flag and the output.
    If the command returns a non-zero exit code, the success flag is
    set to False and the error message is returned.
    The output is returned as a string (UTF-8 encoded)
    """
    output = ""
    try:
        cmds = ["/bin/bash", "-l", "-c", cmd]
        if not login_shell:
            cmds.pop(1)
        if not discard:
            raw_output = subprocess.check_output(cmds, bufsize=4096, stderr=subprocess.STDOUT)
            output = raw_output.decode("UTF-8")
        else:
            # run the command in the background
            child = subprocess.Popen(cmds, start_new_session=True)
            # remember child to be able to clean up processes later
            if child_pids is not None:
                child_pids.append(child.pid)
        success = True
    except subprocess.CalledProcessError as cpe:
        output = "Command '%s' failed with code %s: %s" % (
            cmd, cpe.returncode, cpe.output.decode("UTF-8"))
        success = False
    return success, output


def run_and_report(cmd, connector, login_shell=True):
    """
    Runs the command and report success/failure with output
    """
    (success, output) = run_command(cmd, login_shell=login_shell)
    if not success:
        connector.failed(output)
    else:
        connector.ok(output)


rdn_map = {"C": "countryName",
           "CN": "commonName",
           "O": "organizationName",
           "OU": "organizationalUnitName",
           "L": "localityName",
           "ST": "stateOrProvinceName",
           "DC": "domainComponent",
           }


def convert_rdn(rdn: str):
    split = rdn.split("=")
    translated = rdn_map.get(split[0])
    if translated is None:
        return None
    val = split[1]
    return translated, val


def convert_dn(dn: str):
    """ Convert X500 DN in RFC format to a tuple """
    converted = []
    # split dn and strip leading/trailing whitespace
    elements = [x.strip() for x in re.split(r"[,]", dn)]
    for element in elements:
        if element != '':
            rdn = convert_rdn(element)
            if rdn is None:
                pass
            converted.append(rdn)
    return converted


def match_rdn(rdn, subject):
    for x in subject:
        for y in x:
            if str(y[0]) == str(rdn[0]) and str(y[1]) == str(rdn[1]):
                return True
    return False


def check_access(subject, acl):
    """ matches the given cert subject to the ACL. The subject must be
        in the format as returned by ssl.getpeercert()['subject']
    """
    for dn in acl:
        accept = True
        # every RDN of the ACL entry has to be in the subject
        for rdn in dn:
            accept = accept and match_rdn(rdn, subject)
            if not accept:
                break
        if accept:
            return True
    return False

def random_string(size=6, chars=string.ascii_uppercase + string.digits):
    """ returns a random string """
    return ''.join(choice(chars) for _ in range(size))