"""

    wind.exceptions
    ~~~~~~~~~~~~~~~

    Exceptions

"""


import errno

# Defines frequently used collections of socket.error
EWOULDBLOCK = (errno.EWOULDBLOCK, errno.EAGAIN)
ECONNRESET = (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE)


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


class StreamError(WindException):
    """Stream error occured"""
    pass


class ApplicationError(WindException):
    """Application error occured"""
    pass


class HTTPError(WindException):
    """Error for HTTP abnormal status handling"""
    pass


class LoggerError(WindException):
    """Logger error occured"""
    pass


class CodecError(WindException):
    """Codec error occured"""
    pass
