#
# Initialise connection to UNICORE/X
#  - waits for a connection
#  - validates that it is from UNICORE/X
#  - if validated, command and data connections are opened
#    via callback to UNICORE/X
#  - a child process is forked which further communicates
#    with UNICORE/X via the command/data sockets

import errno
import os
import signal
import socket
import sys
import time
from SSL import setup_ssl, verify_peer

def configure_socket(sock):
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
    Accept connection from UNICORE/X and handle the control command

    'newtsiprocess <ux-port>'
        Callback to UNICORE/X and open a pair (command,data) of sockets
        for communicating with UNICORE/X, fork a new process,
        and return the socket pair to the main loop for user command processing
    
    'start-forwarding <ux-port> <servicehost:serviceport> <user> <group>'
        Connect to the given service, callback to U/X to open a socket,
        fork a new process, and return both sockets to the main loop.
        This then starts bi-directional TCP forwarding.
        The forwarding process will be owned by the given user/group.

    'shutdown'
        Stop the TSI server and exit

    Parameters: dictionary of config settings, logger
    """

    # register a handler to clean up finished worker TSIs
    signal.signal(signal.SIGCHLD, worker_completed)

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
            return

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

        configure_socket(unicorex)
        try:
            msg = unicorex.recv(1024)
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
        elif cmd == "start-forwarding":
            num_conns = 1
        elif cmd == "newtsiprocess":
            num_conns = 2
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
            unicorex_port = get_unicorex_port(configuration, params)
            if unicorex_port is None:
                raise EnvironmentError("Received invalid message")
            address = (unicorex_host, unicorex_port)
            LOG.info("Contacting UNICORE/X on %s port %s" % address)
            # allow some time for U/X to start listening
            time.sleep(1)
            xnjs_sockets = []
            for _ in range(0, num_conns):
                new_socket = open_connection(address, 10, configuration)
                if ssl_mode:
                    new_socket = setup_ssl(configuration, new_socket, LOG)
                configure_socket(new_socket)
                xnjs_sockets.append(new_socket)
        except EnvironmentError as e:
            LOG.info("Error creating connections to UNICORE/X : %s" % str(e))
            close_quietly(unicorex)
            continue
        close_quietly(unicorex)
        LOG.info("Connection to UNICORE/X at %s:%s established." % address)
        worker_id = configuration.get('tsi.worker.id', 1)
        LOG.info("Starting tsi-worker-%d" % worker_id)

        # fork, cleanup and return sockets to the caller (main loop)
        pid = os.fork()
        if pid == 0:
            # child: close unneeded server socket and
            # return command/data sockets to caller
            server.close()
            if cmd == "newtsiprocess":
                command = xnjs_sockets[0]
                data = xnjs_sockets[1]
                return command, data, None
            else:
                _, service_spec, user_spec = params.split(" ", 2)
                service_host, service_port = service_spec.split(":")
                LOG.info("Connecting to %s:%s" % (service_host, service_port))
                service_connection = open_connection((service_host, service_port), 10, configuration)
                configure_socket(service_connection)
                return service_connection, xnjs_sockets[0], "#TSI_IDENTITY %s\n" % user_spec
        else:
            # parent, close unneeded command/data sockets and
            # continue with accept loop
            for i in range(0, num_conns):
                xnjs_sockets[i].close()
            configuration['tsi.worker.id'] = worker_id + 1


def open_connection(address, timeout, configuration):
    """ Connect to the given address """
    port_range = configuration.get("tsi.local_portrange", (0,-1,-1))
    local_port = port_range[0]
    _lower = port_range[1]
    _upper = port_range[2]
    use_port_range = local_port > 0
    if use_port_range:
        max_attempts = _upper-_lower+1
    else:
        max_attempts = 1
    attempts = 0
    while attempts<max_attempts:
        try:
            sock = socket.create_connection(address, timeout, ('', local_port))
            if use_port_range:
                local_port+=1
                if local_port>_upper:
                    local_port = _lower
                configuration["tsi.local_portrange"]=(local_port, _lower, _upper)
            return sock
        except OSError as e:
            attempts+=1
            if use_port_range and e.errno==errno.EADDRINUSE:
                local_port+=1
                if local_port>_upper:
                    local_port = _lower
            else:
                raise e
    raise Exception("Cannot connect - no free local ports in configured range %s:%s" % (_lower, _upper))


def get_unicorex_port(configuration, params):
    """ Get the UNICORE/X port. If not set in config, extract it
        from the params sent by UNICORE/X
    """
    port = configuration.get('tsi.unicorex_port', None)
    if port is None:
        try:
            if " " in params:
                port, _ = params.split(" ", 1)
            else:
                port = params
        except:
            pass
    return port
