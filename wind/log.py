"""

    wind.log
    ~~~~~~~~

    Simple logging system for wind

"""

import logging


class BaseLogger(object):
    """Wind base log class for general logging
    You should pass this object initialized to `App` to start file logging.
    By default, `stdout` logging will be attached to `App`.

    """
    def __init__(self):
        pass
