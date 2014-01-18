"""

    wind.web.stream
    ~~~~~~~~~~~~~~~

    Provides models for handling socket io stream.

"""

import socket
import errno
from collections import deque
from wind.exceptions import StreamError
from wind.web.datastructures import FlexibleDeque


class BaseStream(object):
    """Base class for io stream classes.
    Provide methods to read from and write to file or socket.

    Methods for the caller:

    - __init__(chunk_size=4096)
    - open()
    - close()
    - read()
    - read_bytes(num_bytes)
    - read_until(delimiter)
    
    Methods should be overrided

    - _read_from_fd()
    - _write_to_fd()


    """

    def __init__(self, chunk_size=4096):
        """Initialize and open base stream.
        
        @param chunk_size : chunk size for read.

        """
        self._read_buffer = FlexibleDeque()
        self._write_buffer = FlexibleDeque()
        self._chunk_size = chunk_size
        self._read_buffer_bytes = 0
        self._is_opened = False 
        self.open()
    
    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False
    
    @property
    def opened(self):
        return self._is_opened
    
    @property
    def closed(self):
        return not self._is_opened

    def read(self):
        self._process_read()

    def read_bytes(self, bytes_to_read):
        """Read `bytes_to_read` bytes from file"""
        if not isinstance(bytes_to_read, int):
            raise StreamError('`read_bytes` can only accept `int` param')
        return self._process_read(bytes_to_read=bytes_to_read)
    
    def read_until(self, delimiter):
        """Read until first occurrence of `delimiter`.
        Returned chunk that contains `delimiter`
        
        """
        if not isinstance(delimiter, basestring):
            raise StreamError('`read_until` can only accept `str` param')
        return self._process_read(delimiter=delimiter)

    def _process_read(self, bytes_to_read=None, delimiter=None):
        """fd -> read buffer -> memory"""
        while self.opened:
            if self._to_read_buffer() == 0:
                # End of read
                break
        return self._read(bytes_to_read=bytes_to_read, delimiter=delimiter)

    def _to_read_buffer(self):
        """Read chunk from socket or file and returns number of bytes read.
        
        """
        try:
            chunk = self._read_from_fd()
            if not chunk or chunk is None:
                return 0
        except socket.error as e:
            self.close()

        # No buffer size limit yet.
        self._read_buffer.append(chunk)
        self._read_buffer_bytes += len(chunk)
        return len(chunk)

    def _read(self, bytes_to_read=None, delimiter=None):
        """Read chunk from `_read_buffer` and Returns chunk.

        """
        # XXX: handle delimenter
        read_bytes = 0
        if bytes_to_read is not None:
            read_bytes = min(bytes_to_read, self._read_buffer_bytes)
            return self._pop_chunk(read_bytes)
        
        if delimiter is not None:
            while True:
                pos = self._read_buffer[0].find(delimiter)
                if pos != -1:
                    # Found delimiter
                    return self._pop_chunk(pos + len(delimiter))
                
                if len(self_read_buffer) == 1:
                    # No delimiter found in whole read buffer.
                    break

                # No delimiter found in first chunk.
                self._read_buffer.gather(
                    len(self._read_buffer[0] + self._read_buffer[1]))

        return self._pop_chunk(self._read_buffer_bytes)
    
    def _pop_chunk(self, read_bytes):
        """Pop chunk from `_read_buffer` and Returns chunk."""
        self._read_buffer_bytes -= read_bytes
        self._read_buffer.gather(read_bytes)
        return self._read_buffer.popleft()

    def _read_from_fd(self):
        raise NotImplementedError()

    def _write_to_fd(self):
        raise NotImplementedError()


class SocketStream(BaseStream):
    def __init__(self, socket, *args, **kwargs):
        if not isinstance(socket, socket.socket):
            raise StreamError(
                'SocketStream can only be initialized with `socket.socket`')
        self.socket = socket
        super(SocketStream, self).__init__(*args, **kwargs)

    def _read_from_fd(self):
        try:
            chunk = self.socket.recv(self._chunk_size)
            if not chunk:
                # Should close stream here because nothing is left to be read.
                self.close()
                return None
            return chunk
        except socket.error as e:
            if e.args[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
                raise
            return None

    def _write_to_fd(self):
        pass


class FileStream(BaseStream):
    def __init__(self, file_, *args, **kwargs):
        if not isinstance(file_, file):
            raise StreamError(
                'FileStream can only be initialized with `file`')
        self.file_ = file_
        super(FileStream, self).__init__(*args, **kwargs)

    def _read_from_fd(self):
        return self.file_.read(self._chunk_size)
            
    def _write_to_fd(self):
        pass

