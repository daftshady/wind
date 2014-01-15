"""

    wind.web.stream
    ~~~~~~~~~~~~~~~

    Provides models for handling socket io stream.

"""

from collections import deque



class BaseStream(object):
    """Base class for io stream classes.
    Provide methods to read from and write to file or socket.

    Method for the caller:

    - __init__(chunk_size=4096)
    - read_bytes(num_bytes)
    
    Method should be overrided

    - _read_from_fd()
    - _write_to_fd()


    """

    def __init__(self, chunk_size=4096):
        self._read_buffer = deque()
        self._write_buffer = deque()
        self._chunk_size = chunk_size
    
    def read_bytes(self, num_bytes):
        pass

    def _process_read(self, bytes_to_read=0):
        pass

    def _to_read_buffer(self, bytes_to_read=0):
        pass

    def _read_from_fd(self):
        raise NotImplementedError()

    def _write_to_fd(self):
        raise NotImplementedError()


class SocketStream(BaseStream):
    def __init__(self, socket):
        self._socket = socket

    def _read_from_fd(self):
        pass

    def _write_to_fd(self):
        pass

