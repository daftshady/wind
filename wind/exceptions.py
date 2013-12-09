# -*- coding:utf-8 -*-
"""

    wind.exceptions
    ~~~~~~~~~~~~~~~

    Exceptions

"""


class WindException(Exception):
    """Base exception class for ``wind``"""
    pass


class ServerError(WindException):
    """Server error occured"""
    pass


class SocketError(ServerError):
    """Socket error occured"""
    pass


class PollError(WindException):
    """Poll error occured"""
    pass


class LooperError(WindException):
    """Looper error occured"""
    pass
