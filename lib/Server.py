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


def verify_ip(config, unicorex_host, LOG):
    if 'tsi.allowed_ips' not in config:
        LOG.warning('No list of allowed IPs set. Not production ready')
        return True

    allowed_ips = config['tsi.allowed_ips']
    for ip in allowed_ips:
        if unicorex_host == ip:
            return True
    raise EnvironmentError("Connecting IP not in list of allowed IPs")


def close_quietly(closeable):
    try:
        closeable.close()
    except:
        pass


def connect(config, LOG):
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

    # handle clean up of finished worker TSIs
    signal.signal(signal.SIGCHLD, worker_completed)

    host = config['tsi.my_addr']
    port = int(config['tsi.my_port'])
    ssl_mode = config.get('tsi.keystore') is not None
    if ssl_mode:
        try:
            from SSL import setup_ssl, verify_peer
        except ImportError as e:
            LOG.error("SSL module could not be imported!")
            raise e
    server = create_server(host, port, config)
    fam = "IPv6/IPv4" if server.family==socket.AF_INET6 else "IPv4"
    if port==0:
        port = server.getsockname()[1]
        config["tsi.my_port"] = port
    if ssl_mode:
        server = setup_ssl(config, server, LOG, server_mode=True)
    LOG.info("Listening (%s) on %s:%s" % (fam, host, port))
    LOG.info("SSL enabled: %s" % ssl_mode)
    server.listen(2)

    while True:
        try:
            (unicorex, peer_info) = server.accept()
            unicorex_host = peer_info[0]
        except EnvironmentError as e:
            if e.errno != errno.EINTR:
                LOG.info("Error waiting for new connection: " + str(e))
            return

        if ssl_mode:
            try:
                verify_peer(config, unicorex, LOG)
            except EnvironmentError as e:
                LOG.info("Error verifying connection from %s : %s" % (
                    unicorex_host, str(e)))
                close_quietly(unicorex)
                continue

        try:
            verify_ip(config, unicorex_host, LOG)
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
        elif cmd == "set":
            settings = config.get("settings", {})
            key, value = params.split(" ",1)
            settings[key] = value
            config['settings'] = settings
            close_quietly(unicorex)
            LOG.info("SET: %s=%s"%(key,value))
            continue
        else:
            LOG.info("Command from UNICORE/X not understood: %s " % msg)
            close_quietly(unicorex)
            continue
        LOG.info("Accepted connection from %s" % unicorex_host)
        try:
            # write to UNICORE/X to tell it everything is OK
            unicorex.sendall(b'OK\n')
            # callback to UNICORE/X
            unicorex_port = get_unicorex_port(config, params)
            if unicorex_port is None:
                raise EnvironmentError("Received invalid message")
            address = (unicorex_host, unicorex_port)
            LOG.info("Contacting UNICORE/X on %s port %s" % address)
            # allow some time for U/X to start listening
            time.sleep(1)
            xnjs_sockets = []
            for _ in range(0, num_conns):
                new_socket = open_connection(address, 10, config)
                if ssl_mode:
                    new_socket = setup_ssl(config, new_socket, LOG, server_mode=False)
                configure_socket(new_socket)
                xnjs_sockets.append(new_socket)
        except EnvironmentError as e:
            LOG.info("Error creating connections to UNICORE/X : %s" % str(e))
            close_quietly(unicorex)
            continue
        close_quietly(unicorex)
        LOG.info("Connection to UNICORE/X at %s:%s established." % address)
        worker_id = config.get('tsi.worker.id', 1)
        LOG.info("Starting tsi-worker-%d" % worker_id)

        # fork, cleanup and return sockets to the caller (main loop)
        pid = os.fork()
        if pid == 0:
            # child
            server.close()
            # reset signal handler
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            if cmd == "newtsiprocess":
                command = xnjs_sockets[0]
                data = xnjs_sockets[1]
                return command, data, None
            else:
                _, service_spec, user_spec = params.split(" ", 2)
                msg = ("#TSI_FORWARDING_CONNECT_TO %s\n"
                       "#TSI_IDENTITY %s\n"
                ) % (service_spec, user_spec)
                return xnjs_sockets[0], None, msg
        else:
            # parent
            for i in range(0, num_conns):
                xnjs_sockets[i].close()
            config['tsi.worker.id'] = worker_id + 1


def open_connection(address, timeout, config):
    """ Connect to the given address """
    port_range = config['tsi.local_portrange']
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
                config['tsi.local_portrange']=(local_port, _lower, _upper)
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

def create_server(host: str, port: int, config: dict)->socket.socket:
    if _check_ipv6_support(host, port, config):
        return socket.create_server((host, port), family=socket.AF_INET6, dualstack_ipv6=True, reuse_port=True)
    else:
        return socket.create_server((host, port), reuse_port=True)

def _check_ipv6_support(host: str, port: int, config: dict) -> bool:
    if config.get('tsi.disable_ipv6', False):
        return False
    if len(host)==0 or host=="*":
        return True
    for addrinfo in socket.getaddrinfo(host, port):
        if addrinfo[0]==socket.AF_INET6:
            return True
    return False
