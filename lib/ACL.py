""" ACL operations module

 This module allows for performing file ACL operations: getting
 file ACL, setting them and checking if ACL are supported for the FS.
 The supported ACL implementation is:
  - POSIX 1003.2c draft 17 (via popular getfacl and setfacl UNIX commands)
    in the Linux version. Currently few features of the Linux implementation
    are used: it is assumed that getfacl returns also the default ACL entries,
    it is assumed that setfacl automatically creates the mandatory default ACL
    entries when needed, -R option is used to achieve recursive behavior.

 The process_acl function expects the following arguments
 in the UNICORE/X message:
 #TSI_ACL_OPERATION <CHECK_SUPPORT|GETFACL|SETFACL>
 #TSI_ACL_PATH /some/path
 #TSI_ACL_COMMAND <RM_ALL|MODIFY|RM> [RECURSIVE]
 #TSI_ACL_COMMAND_SPEC [D]<U|G> <subject> <permissions in rwx format>

 Operations supported are 'CHECK_SUPPORT', 'GETFACL' and 'SETFACL' for
 ACL support check on the path, ACL get request and ACL set request respectively.
 TSI_ACL_COMMAND is reguired only for SETFACL
 TSI_ACL_COMMAND_SPEC is only required for SETFACL, with command MODIFY or RM.

 the COMMAND and COMMAND_SPEC are required only for SETFACL operation.
 In the COMMAND_SPEC D is used to modify/remove default directory ACL. Subject
 can be empty
 - then the standard group/owner ACL is modified (as with chmod).


   The following output is generated for operations:

    - 'CHECK_SUPPORT': either 'true' or 'false'
    - 'GETFACL': lines in getfacl format, only containing
      user or group entries, e.g.:

           user::rwx
           group::rw-
           user:nobody:r--
           group:wheel:rwx
      Note that this form of output may be a result of translation done
      by TSI; it is not necessarly the exact output of the command run.

    - 'SETFACL': nothing if operation was succesful or error report if not.

    - any other: 'UNSUPPORTED_OPERATION' string is returned.

     Every line is terminated by \n
"""

import os
import re

from Utils import run_command, extract_parameter


def check_support(path, acl):
    """ Checks if a directory is on a FS configured with ACL support.
        Returns: "POSIX" or "NFS", or "NONE" if no ACL support
    """
    # FIXIT: something is wrong here
    abs_path = os.path.abspath(path)
    best_match = 0
    for key in acl:
        m = re.match(r"^" + key, path)
        if m:
            size = len(m.group(0))
            if size > best_match:
                best_match = size
                best_result = acl[key]

    if best_match > 0:
        return best_result
    else:
        return "NONE"


def getfacl_nfs(path, connector, config, LOG):
    pass


def setfacl_nfs(path, command, command_spec, connector, config, LOG):
    pass


def unset_posix():
    if 'POSIXLY_CORRECT' in os.environ:
        del os.environ['POSIXLY_CORRECT']


def getfacl_posix(path, connector, config, LOG):
    unset_posix()
    getfacl_cmd = config.get('tsi.getfacl', '/bin/false')
    command = "%s %s" % (getfacl_cmd, path)
    LOG.debug(command)
    (success, result) = run_command(command, login_shell=config['tsi.use_login_shell'])
    if not success:
        connector.failed(result)
    else:
        patterns = ["user", "group", "default:user", "default:group"]
        connector.ok()
        for line in result.splitlines():
            if True in [line.startswith(p) for p in patterns]:
                connector.write_message(line)


def prepare_posix_arg(val, remove):
    ret = ""
    oargs = val.split(" ")
    if re.match(r"[D]?U", oargs[0]) is not None:
        ret = "user:" + oargs[1]
    elif re.match(r"[D]?G", oargs[0]) is not None:
        ret = "group:" + oargs[1]
    if not remove:
        ret = ret + ":"+ oargs[2]
    return ret


def setfacl_posix(path, op, val, connector, config, LOG):
    unset_posix()
    setfacl_cmd = config.get('tsi.setfacl', '/bin/false')

    if "RECURSIVE" in op:
        recursive = "-R "
    else:
        recursive = ""

    if "RM_ALL" in op:
        command = "%s -b %s'%s'" % (setfacl_cmd, recursive, path)
    else:
        base_arg = ""
        remove = False
        if val.startswith("D"):
            base_arg = "-d "
        if "MODIFY" in op:
            base_arg += "-m"
        elif "RM" in op:
            base_arg += "-x"
            remove = True
        else:
            connector.failed("WRONG SETFACL SYNTAX")
            return
        arg = prepare_posix_arg(val, remove)
        command = "%s %s %s %s '%s'" % (
            setfacl_cmd, recursive, base_arg, arg, path)

    LOG.debug(command)
    (success, result) = run_command(command, login_shell=config['tsi.use_login_shell'])
    if not success:
        connector.failed(result)
    else:
        connector.ok()


def process_acl(message, connector, config, LOG):
    operation = extract_parameter(message, "ACL_OPERATION")
    path = extract_parameter(message, "ACL_PATH")
    acl = config.get('tsi.acl', {})
    if operation == "CHECK_SUPPORT":
        support = check_support(path, acl)
        if support == "NONE":
            connector.ok("false")
        else:
            connector.ok("true")
    elif operation == "GETFACL":
        support = check_support(path, acl)
        if support == "POSIX":
            getfacl_posix(path, connector, config, LOG)
        elif support == "NFS":
            getfacl_nfs(path, connector, config, LOG)
        else:
            connector.failed(
                "ERROR: Getting ACL on this file system is unsupported.")
    elif operation == "SETFACL":
        support = check_support(path, acl)
        command = extract_parameter(message, "ACL_COMMAND")
        command_spec = extract_parameter(message, "ACL_COMMAND_SPEC")
        if command_spec is None:
            connector.failed("Missing parameter TSI_ACL_COMMAND_SPEC")
        if command is None:
            connector.failed("Missing parameter TSI_ACL_COMMAND")
        if support == "POSIX":
            setfacl_posix(path, command, command_spec, connector, config, LOG)
        elif support == "NFS":
            setfacl_nfs(path, command, command_spec, connector, config, LOG)
        else:
            connector.failed(
                "ERROR: Setting ACL on this file system is unsupported.")
    else:
        connector.failed("UNSUPPORTED_OPERATION: '%s'" % operation)
