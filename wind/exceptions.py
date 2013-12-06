# -*- coding:utf-8 -*-
"""

    wind.exceptions
    ~~~~~~~~~~~~~~~

    Exceptions

"""


class WindException(Exception):
    """Base exception class for ``wind``"""
    pass


class ServerException(WindException):
    """Server exception occured"""
    pass


class SocketException(ServerException):
    """Socket exception occured"""
    pass
