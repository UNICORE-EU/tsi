#
# Initialise connection to UNICORE/X
#  - waits for a connection
#  - validates that it is from UNICORE/X
#  - if validated, command and data connections are opened
#    via callback to UNICORE/X
#  - a child process is forked which further communicates
#    with UNICORE/Xvia the command/data sockets

import errno
import os
import signal
import socket
import sys
import time
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
            (pid,_,_) = os.wait3(os.WNOHANG)
            if pid == 0:
                break
    except:
        pass


def verify_ip(configuration, unicorex_host, LOG):
    if 'tsi.allowed_ips' not in configuration:
        LOG.warning('No list of allowed IPs set. Not production ready')
        return True

    allowed_ips = configuration['tsi.allowed_ips']
    for ip in allowed_ips:
        if unicorex_host == ip:
            return True
    raise EnvironmentError("Connecting IP not in list of allowed IPs")

def close_quietly(closeable):
    try:
        closeable.close()
    except:
        pass

def connect(configuration, LOG):
    """
    Accept connection from UNICORE/X.

    Return a pair (command,data) of sockets for communicating
    with UNICORE/X.

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
            (unicorex, (unicorex_host, _)) = server.accept()
        except EnvironmentError as e:
            if e.errno != errno.EINTR:
                LOG.info("Error waiting for new connection: " + str(e))
            continue

        if ssl_mode:
            try:
                verify_peer(configuration, unicorex, LOG)
            except EnvironmentError as e:
                LOG.info("Error verifying connection from %s : %s" % (
                    unicorex_host, str(e)))
                close_quietly(unicorex)
                continue

        try:
            verify_ip(configuration, unicorex_host, LOG)
        except EnvironmentError as e:
            LOG.info("Error verifying connection from %s : %s" % (
                unicorex_host, str(e)))
            close_quietly(unicorex)
            continue

        configure_socket(unicorex, LOG)
        try:
            msg = unicorex.recv(buffer_size)
            msg = str(msg, "UTF-8").strip()
            LOG.info("message : %s" % msg)
        except EnvironmentError as e:
            LOG.info("Error reading from UNICORE/X: %s " % str(e))
            close_quietly(unicorex)
            continue
        
        try:
            cmd, params = msg.split(" ",1)
        except:
            cmd = ""

        if cmd == "shutdown":
            LOG.info("Received shutdown message, exiting.")
            server.close()
            exit(0)
        elif cmd == "newtsiprocess":
            pass
        else:
            LOG.info("Command from UNICORE/X not understood: %s " % msg)
            close_quietly(unicorex)
            continue
        LOG.info("Accepted connection from %s" % unicorex_host)
        try:
            # write to UNICORE/X to tell it everything is OK
            unicorex.sendall(b'OK\n')
            # callback to UNICORE/X
            unicorex_port = get_unicorex_port(configuration, params, LOG)
            if unicorex_port is None:
                raise EnvironmentError("Received invalid message")
            address = (unicorex_host, unicorex_port)
            LOG.info("Contacting UNICORE/X on %s port %s" % address)
            # allow some time for U/X to start listening
            time.sleep(1)
            command = socket.create_connection(address, 10)
            data = socket.create_connection(address, 10)
        except EnvironmentError as e:
            LOG.info("Error communicating with UNICORE/X : %s" % str(e))
            close_quietly(unicorex)
            continue

        if ssl_mode:
            try:
                command = setup_ssl(configuration, command, LOG)
                data = setup_ssl(configuration, data, LOG)
            except EnvironmentError as e:
                LOG.info("Error setting up SSL connections to UNICORE/X: %s" % str(e))
                close_quietly(unicorex)
                continue

        LOG.info("Connection to UNICORE/X at %s:%s established." % address)
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


def get_unicorex_port(configuration, params, LOG):
    """ Get the UNICORE/X port. If not set in config, extract it
        from the params sent by UNICORE/X
    """
    port = configuration.get('tsi.unicorex_port', None)
    if port is None:
        port = configuration.get('tsi.njs_port', None)
    if port is None:
        try:
            port = params
        except:
            pass
    return port
