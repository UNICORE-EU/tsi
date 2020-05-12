"""File I/O functionality: get_file_chunk(), put_file_chunk()
   and helper functions
"""

import io
import grp
import pwd
import re
import os
import os.path
import stat
from Utils import expand_variables, extract_parameter, run_command


def get_file_chunk(message, connector, config, LOG):
    """Return part of a file to the XNJS via the data_out stream.
       The message sent by the XNJS is scanned for:
           TSI_FILE   - name of file to return
           TSI_START  - start byte
           TSI_LENGTH - how many bytes to return
    """
    path = extract_parameter(message, 'FILE')
    path = expand_variables(path)
    start = int(extract_parameter(message, 'START'))
    length = int(extract_parameter(message, 'LENGTH'))

    LOG.debug("Getting data from %s start at %d length %d" % (path, start,
                                                              length))

    with io.FileIO(path, "rb") as f:
        if f.seekable():
            f.seek(start)
        buf = bytearray(length)
        total_bytes_read = 0
        remaining = length

        while remaining > 0:
            read = f.readinto(buf)
            if read == 0:
                break
            total_bytes_read += read
            remaining -= read

        # reply and report total bytes read
        connector.ok("TSI_LENGTH %s\nENDOFMESSAGE" % total_bytes_read)

        # write it out, taking care to handle partial writes
        write_offset = 0
        must_write = total_bytes_read
        while must_write > 0:
            written = connector.write_data(buf[write_offset:total_bytes_read])
            if written is None:
                break
            write_offset += written
            must_write -= written


def put_file_chunk(message, connector, config, LOG):
    """Write part of a file, reading data from the XNJS via the data_in stream.
       The message sent by the XNJS is scanned for:
           TSI_FILE   - name of file to write and mode
           TSI_FILESACTION  - what to do (overwrite = 1 , append = 3)
           TSI_LENGTH - how many bytes to return
    """
    path_and_mode = extract_parameter(message, "FILE")
    mode_index = path_and_mode.rindex(" ")

    path = expand_variables(path_and_mode[:mode_index])
    mode = path_and_mode[mode_index + 1:]

    action = extract_parameter(message, "FILESACTION")
    if action is None:
        action = "1"

    length = int(extract_parameter(message, "LENGTH"))

    LOG.debug("Writing %d bytes of data to %s" % (length, path))

    if action == "3":
        open_mode = "ab"
    else:
        open_mode = "wb"

    with io.FileIO(path, open_mode) as f:
        # the next message tells the XNJS to start sending data
        connector.ok("ENDOFMESSAGE")
        remaining = length

        while remaining > 0:
            buf = connector.read_data(remaining)
            bytes_read = len(buf)
            remaining -= bytes_read

            # write it out, taking care to handle partial writes
            write_offset = 0
            must_write = bytes_read
            while must_write > 0:
                written = f.write(buf[write_offset:bytes_read])
                write_offset += written
                must_write -= written

    # change mode to requested mode
    os.chmod(path, int(mode, 8))


_mode_table = (
    (stat.S_IRUSR, "r"),
    (stat.S_IWUSR, "w"),
    (stat.S_IXUSR, "x"),
    (stat.S_IRGRP, "r"),
    (stat.S_IWGRP, "w"),
    (stat.S_IXGRP, "x"),
    (stat.S_IROTH, "r"),
    (stat.S_IWOTH, "w"),
    (stat.S_IXOTH, "x")
)


def get_info(path):
    """" TSI_LS listing for a single file. The format is:

      Character 0 is usually blank, except:

            If character 0 is '-', then the this line contains extra
            information about the file described in the previous line.
              If the next character is 2nd '-' then this line provides an extended
              information about file (see below). Otherwise this line is copied
              without change into the ListDirectory outcome entry for the file.

     Character 1 is 'D' if the file is a directory
     Character 2 is "R" if the file is readable by the Xlogin (effective uid/gid)
     Character 3 is "W" if the file is writable by the Xlogin (effective uid/gid)
     Character 4 is "X" if the file is executable by the Xlogin (effective uid/gid)
     Character 5 is "O" if the file is owned by the Xlogin (effective uid/gid)
     Character 6 is a space.

     Until the next space is a decimal integer which is the size of the file in bytes.

     Until the next space is a decimal integer which is the last modification
     time of the file in seconds since the Unix epoch.

     Until the end of line is the full path name of the file.

     Extended permissions specification is encoded on the next line as follows:

     --rwxrwxrwx owner owningGroup

     where letters rwx can be replaced by '-' to form standard UNIX permissions,
     'owner' is file owner uid and 'owningGroup' is file owning gid. After owning group
     space is permitted and additional text may be present. Currently it will be ignored.

     Every line is terminated by \n
    """

    statinfo = os.stat(path)
    mode = statinfo.st_mode

    is_dir = " "
    if stat.S_ISDIR(mode):
        is_dir = "D"

    is_read = " "
    if os.access(path, os.R_OK):
        is_read = "R"

    is_write = " "
    if os.access(path, os.W_OK):
        is_write = "W"

    is_exec = " "
    if os.access(path, os.X_OK):
        is_exec = "X"

    is_own = " "
    if os.geteuid() == statinfo.st_uid:
        is_own = "O"

    p = []

    for flag, char in _mode_table:
        if mode & flag:
            p.append(char)
        else:
            p.append("-")

    perms = "--" + "".join(p)

    size = str(statinfo.st_size)
    modt = str(int(statinfo.st_mtime))

    # careful with newline chars: replace by '?'
    path = re.sub(r'[\r\n]', '?', path)

    pwd_entry = pwd.getpwuid(statinfo.st_uid)
    if pwd_entry is not None:
        user = pwd_entry.pw_name
    else:
        user = str(statinfo.st_uid)

    grp_entry = grp.getgrgid(statinfo.st_gid)
    if grp_entry is not None:
        group = grp_entry.gr_name
    else:
        group = str(statinfo.st_gid)

    return " " + is_dir + is_read + is_write + is_exec + is_own + " " + size \
           + " " + modt + " " + path + "\n" + perms + " " + user + " " + group


def list_directory(connector, path, recursive):
    """ List a directory (which is supposed to exist) """
    entries = os.listdir(path)
    for entry in entries:
        full_path = os.path.join(path, entry)
        if recursive and os.path.isdir(full_path):
            list_directory(connector, full_path, recursive)
            connector.write_message("<")
        try:
            file_info = get_info(full_path)
            connector.write_message(file_info)
        except:
            pass


def ls(message, connector, config, LOG):
    """List directory or get information about a file
       The message sent by the XNJS is scanned for:
           TSI_FILE     - name of file/path to list
           TSI_LS_MODE     - "A" : just the file,
                             "R" : directory recursive
                             any other : dir non-recursive

 The TSI replies with TSI_OK and some lines of output
 The format of the output is as follows:

   Listing starts with the line:

   START_LISTING

   and ends with the line:

   END_LISTING

   The files are listed in depth-first order. Each time a sub-directory
   is found the entry for the sub-directory file is listed and then entries
   for all the file in the subdirectory are listed.

   The format for each listing line is detailed above in the get_info()
   method.

   When all files in a sub-directory have been listed and the listing is
   continuing with the parent directory, a line with a single "<" is printed.
   This is required even when the listing is non-recursive.

    """
    path = extract_parameter(message, "FILE")
    path = expand_variables(path)
    mode = extract_parameter(message, "LS_MODE")

    allowed = ["R", "A", "N"]
    if mode not in allowed:
        connector.failed("Unknown TSI_LS mode: '%s', must be one of "
                         "'R', 'A' or 'N'." % mode)
        return

    as_single_file = "A" == mode
    recurse = "R" == mode
    connector.write_message("START_LISTING")
    if os.path.exists(path):
        try:
            if os.path.isdir(path) and not as_single_file:
                list_directory(connector, path, recurse)
            else:
                info = get_info(path)
                connector.write_message(info)
        except:
            # this is somewhat wierd, but the perl TSI did it the same way
            pass
    connector.write_message("END_LISTING")


def df(message, connector, config, LOG):
    """ determines the free space on a given partition
    and reports results on stdout in the format that the XNJS expects.
    The format of the output is as follows:

    Output starts with the line:
    START_DF
    and ends with the line:
    END_DF

    The following values are reported (in bytes):
    - TOTAL: The total space on the partition
    - FREE: The free space on the partition
    - USER: The user quota (optional)
    Every line is terminated by \n
    """

    path = extract_parameter(message, "FILE")
    path = expand_variables(path)

    # TODO might want to add a cache or do not check
    # free space for certain paths

    command = "df -P -B 1 %s" % path
    (success, result) = run_command(command)
    total = free = user = '-1'

    if success:
        try:
            for line in result.splitlines():
                m = re.match(r"(\S+)\s+(\d+)\s+(\d+)\s+(\d+).+", line)
                if m is not None:
                    total = m.group(2)
                    free = m.group(4)
        except:
            connector.failed("Wrong or unexpected output from 'df' "
                             "command: %s" % result)
            return
        connector.write_message("START_DF")
        connector.write_message("TOTAL %s" % total)
        connector.write_message("FREE %s" % free)
        connector.write_message("USER %s" % user)
        connector.write_message("END_DF")
    else:
        connector.failed(result)
