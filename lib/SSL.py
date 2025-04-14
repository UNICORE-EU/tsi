#
# SSL-related functions
#

import ssl
import Utils

def setup_ssl(config, socket, LOG, server_mode=False):
    """ Wraps the given socket with an SSL context """
    keystore = config.get('tsi.keystore')
    keypass = config.get('tsi.keypass', None)
    cert = config.get('tsi.certificate')
    truststore = config.get('tsi.truststore', None)
    protocol = ssl.PROTOCOL_TLS_SERVER if server_mode else ssl.PROTOCOL_TLS_CLIENT
    context = ssl.SSLContext(protocol)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = False
    context.load_cert_chain(certfile=cert, keyfile=keystore,
                            password=keypass)
    if truststore:
        context.load_verify_locations(cafile=truststore)
    else:
        context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
    return context.wrap_socket(socket, server_side=server_mode)


def verify_peer(config, socket, LOG):
    """ check that the peer is OK by comparing the DN to our ACL """
    acl = config.get('tsi.allowed_dns', [])
    subject = socket.getpeercert()['subject']
    LOG.debug("Verify UNICORE/X certificate with subject %s" % str(subject))
    if not Utils.check_access(subject, acl):
        raise EnvironmentError("Connection not allowed by ACL")
