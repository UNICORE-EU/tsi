""" Wrapper class around common I/O operations """

import Utils


class Connector(object):
    def __init__(self, command, data, LOG):
        self.data = data
        self.command = command
        self.control_in = command.makefile("r")
        self.control_out = command.makefile("w")
        self.data_in = data.makefile("rb")
        self.data_out = data.makefile("wb")
        self.LOG = LOG
        self.buf_size = 32768

    def failed(self, message):
        """ Write single line of TSI_FAILED and error message to control
        channel
        """
        msg = "TSI_FAILED: "
        if message is not None:
            msg += message.replace("\n", ":")
        self.write_message(msg)

    def ok(self, message=None):
        """ Write TSI_OK line and any message to control channel """
        msg = "TSI_OK"
        if message is not None:
            msg += "\n"
            msg += message
        self.write_message(msg)

    def read_message(self):
        """Read message terminated by ENDOFMESSAGE from control channel
           Returns unicode
        """
        message = ''
        while True:
            line = self.control_in.readline()
            if len(line) == 0:
                raise IOError("Socket closed")
            self.LOG.debug(line)
            if line == 'ENDOFMESSAGE\n':
                break
            message += line
        return Utils.encode(message)

    def write_message(self, message):
        """ Write message to control channel and add newline """
        if message is not None:
            self.control_out.write(Utils.encode(message))
            self.control_out.write(u"\n")
            self.control_out.flush()

    def read_data(self, maxlen):
        limit = min(maxlen, self.buf_size)
        return self.data_in.read(limit)

    def write_data(self, data):
        written = self.data_out.write(data)
        self.data_out.flush()
        if written is None:
            written = len(data)
        return written

    def close(self):
        try:
            self.command.close()
        except:
            pass
        try:
            self.data.close()
        except:
            pass
