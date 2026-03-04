"""
Runs one processing event, reading from stdin and writing to stdout.
Binary data is encoded and transferred via the text streams.
"""

from TSI import assert_version, finish_setup, MY_VERSION, REQUIRED_VERSION, process, get_default_config
from Log import Logger
import BecomeUser, BSS, Connector
import sys

def main():
    """
    Runs one-shot processing. Reads config, reads message and
    and launches the processing.
    """
    if not assert_version():
        raise RuntimeError("Unsupported version of Python! "
                           "Must be %s or later." % str(REQUIRED_VERSION))
    LOG = Logger("UNICORE-TSI-run", False, False, True)
    config = get_default_config()
    config['tsi.switch_uid'] = False
    config['tsi.open_user_sessions'] = False
    finish_setup(config, LOG)
    bss = BSS.BSS()
    LOG.info("Starting TSI %s for %s" % (MY_VERSION, bss.get_variant()))
    BecomeUser.initialize(config, LOG)
    bss.init(config, LOG)
    config['tsi.bss'] = bss
    connector = Connector.StreamConnector(sys.stdin, sys.stdout, LOG)
    process(connector, config, LOG, one_shot=True)
    return 0


# application entry point
if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)