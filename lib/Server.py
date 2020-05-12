#
# Initialise connection to the XNJS
#  - waits for a connection
#  - validates that it is from the XNJS
#  - if validated, command and data connections are opened
#    via callback to the XNJS
#  - a child process is forked which further communicates
#    with the XNJS via the command/data sockets

import errno
import os
import re
import signal
import socket
import sys
import time
import Utils
from SSL import setup_ssl, verify_peer


def configure_socket(sock, LOG):
    """
    Setup socket options (keepalive).
    """
    after_idle = 5
    interval = 1
    max_fails = 3
    sock.settimeout(None)
    if not sys.platform.startswith("win"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if sys.platform.startswith("darwin"):
        TCP_KEEPALIVE = 0x10
        sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, interval)
    if sys.platform.startswith("linux"):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


def worker_completed(signal, frame):
    try:
        while True:
            (pid,state,ru) = os.wait3(os.WNOHANG)
            if pid == 0:
                break
    except:
        pass


def verify_ip(configuration, xnjs_host, LOG):
    if 'tsi.allowed_ips' not in configuration:
        LOG.warning('No list of allowed IPs set. Not production ready')
        return True

    allowed_ips = configuration['tsi.allowed_ips']
    for ip in allowed_ips:
        if xnjs_host == ip:
            return True
    raise EnvironmentError("Connecting IP not in list of allowed IPs")

def close_quietly(closeable):
    try:
        closeable.close()
    except:
        pass

def connect(configuration, LOG):
    """
    Accept connection from the XNJS.

    Return a pair (command,data) of sockets for communicating
    with the XNJS.

    Parameters: dictionary of config settings, logger
    """

    # register a handler to clean up finished worker TSIs
    signal.signal(signal.SIGCHLD, worker_completed)

    buffer_size = 1024
    host = configuration['tsi.my_addr']
    port = int(configuration['tsi.my_port'])
    ssl_mode = configuration.get('tsi.keystore') is not None

    LOG.info("Listening on %s:%s" % (host, port))
    LOG.info("SSL enabled: %s" % ssl_mode)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    if ssl_mode:
        server = setup_ssl(configuration, server, LOG, True)

    server.listen(2)

    while True:
        try:
            (xnjs, (xnjs_host, _)) = server.accept()
        except EnvironmentError as e:
            if e.errno != errno.EINTR:
                LOG.info("Error waiting for new connection: " + str(e))
            continue

        if ssl_mode:
            try:
                verify_peer(configuration, xnjs, LOG)
            except EnvironmentError as e:
                LOG.info("Error verifying connection from %s : %s" % (
                    xnjs_host, str(e)))
                close_quietly(xnjs)
                continue

        try:
            verify_ip(configuration, xnjs_host, LOG)
        except EnvironmentError as e:
            LOG.info("Error verifying connection from %s : %s" % (
                xnjs_host, str(e)))
            close_quietly(xnjs)
            continue

        configure_socket(xnjs, LOG)
        try:
            msg = xnjs.recv(buffer_size)
        except EnvironmentError as e:
            LOG.info("Error reading from XNJS: %s " % str(e))
            close_quietly(xnjs)
            continue
        
        LOG.info("message : %s" % msg)
        if msg == "shutdown\n":
            LOG.info("Received shutdown message, exiting.")
            server.close()
            exit(0)

        LOG.info("Accepted connection from %s" % xnjs_host)
        try:
            # write to the XNJS to tell it everything is OK
            xnjs.sendall(b'OK\n')
            # callback to the XNJS
            xnjs_port = get_xnjs_port(configuration, Utils.decode(msg), LOG)
            if xnjs_port is None:
                raise EnvironmentError("Received invalid message")
            address = (xnjs_host, xnjs_port)
            LOG.info("Contacting XNJS on %s port %s" % address)
            # allow some time for XNJS to start listening
            time.sleep(1)
            command = socket.create_connection(address, 10)
            data = socket.create_connection(address, 10)
        except EnvironmentError as e:
            LOG.info("Error communicating with XNJS : %s" % str(e))
            close_quietly(xnjs)
            continue

        if ssl_mode:
            try:
                command = setup_ssl(configuration, command, LOG)
                data = setup_ssl(configuration, data, LOG)
            except EnvironmentError as e:
                LOG.info("Error setting up SSL connections to XNJS : %s" % str(e))
                close_quietly(xnjs)
                continue

        LOG.info("Connection to XNJS at %s:%s established." % address)
        worker_id = configuration.get('tsi.worker.id', 1)
        LOG.info("Starting tsi-worker-%d" % worker_id)
        # fork, cleanup and return sockets to the caller (main loop)
        pid = os.fork()
        if pid == 0:
            # child: close unneeded server socket and
            # return command/data sockets to caller
            server.close()
            configure_socket(command, LOG)
            configure_socket(data, LOG)
            return command, data
        else:
            # parent, close unneeded command/data sockets and
            # continue with accept loop
            # TODO check if SSL session is OK with this!
            command.close()
            data.close()
            configuration['tsi.worker.id'] = worker_id + 1


def setup_streams(command, data):
    """ return control_in/out text streams"""
    control_in = command.makefile("r")
    control_out = command.makefile("wb")
    data_in = data.makefile("rb")
    data_out = data.makefile("wb")
    return control_in, control_out, data_in, data_out


def get_xnjs_port(configuration, message, LOG):
    """ Get the XNJS port. If not set in config, extract it
        from the message sent by the XNJS
    """
    port = configuration.get('tsi.njs_port', None)
    if port is None:
        try:
            port = re.match(r"\w+ (\w+)", message).group(1)
        except:
            pass
    return port
