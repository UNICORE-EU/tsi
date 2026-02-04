"""
Reservation (dummy module)

Check the manual for advice on how to create a custom version.
"""


def get_variant():
    return "dummy"


def init(config, LOG):
    pass


def make_reservation(msg, connector, config, LOG):
    """ Make a reservation """
    connector.failed("Reservation not supported!")


def query_reservation(msg, connector, config, LOG):
    """ Query a reservation """
    connector.failed("Reservation not supported!")


def cancel_reservation(msg, connector, config, LOG):
    """ Cancel a reservation """
    connector.failed("Reservation not supported!")
