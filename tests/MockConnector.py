""" Unit testing version of Connector.py """

import io
import time


class MockConnector(object):
    def encode(self, message):
        if type(message) is type(u" "):
            return message
        else:
            return message.decode("UTF-8")

    def __init__(self, control_in, control_out, data_in, data_out, LOG):
        self.control_in = control_in
        self.data_in = data_in

        if control_out is None:
            control_out = io.StringIO()
        if data_out is None:
            data_out = io.BytesIO()
        self.control_out = control_out
        self.data_out = data_out
        self.LOG = LOG
        self.buf_size = 32768

    def read_message(self):
        """ Read message terminated by ENDOFMESSAGE from control channel """
        message = ''
        while True:
            line = self.control_in.readline()
            if len(line) == 0:
                time.sleep(1)
                continue
            self.LOG.debug(line)
            if line == 'ENDOFMESSAGE\n':
                break
            message += line
        return message

    def write_message(self, message):
        """ Write message to control channel """
        if message is not None:
            self.control_out.write(self.encode(message))
            self.control_out.write(u"\n")
            self.control_out.flush()

    def failed(self, message):
        """
        Write single line of TSI_FAILED and error message to control channel
        """
        self.write_message("TSI_FAILED: " + message.replace("\n", ":") + "\n")
        self.control_out.flush()

    def ok(self, message=None):
        """ Write TSI_OK line and any message to control channel """
        self.control_out.write(u"TSI_OK\n")
        if message is not None:
            self.write_message(message)

    def read_data(self, maxlen):
        limit = min(maxlen, self.buf_size)
        return self.data_in.read(limit)

    def write_data(self, data):
        written = self.data_out.write(data)
        if written is None:
            written = len(data)
        return written
