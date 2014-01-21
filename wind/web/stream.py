"""

    wind.web.stream
    ~~~~~~~~~~~~~~~

    Provides models for handling socket io stream.

"""

import errno
import socket
from wind.poll import PollEvents
from wind.exceptions import StreamError
from wind.web.datastructures import FlexibleDeque
from wind.socketserver import EWOULDBLOCK, ECONNRESET


class StreamBuffer(FlexibleDeque):
    """Buffer for stream read and write."""

    def __init__(self, *args, **kwargs):
        """Initialize `_frozen` to False. 
        `_frozen` is flag used to check whether current buffer 
        is available for reading from or writing to.

        """
        self._frozen = False

    @property
    def frozen(self):
        return self._frozen

    @frozen.setter
    def frozen(self, value):
        self._frozen = value


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
    - write(chunk)
    
    Methods should be overrided

    - _read_from_fd()
    - _write_to_fd()


    """

    def __init__(self, chunk_size=4096):
        """Initialize and open base stream.
        
        @param chunk_size : chunk size for read.

        """
        self._read_buffer = StreamBuffer() 
        self._write_buffer = StreamBuffer() 
        self._read_chunk_size = chunk_size
        self._write_chunk_size = 128 * 1024
        self._read_buffer_bytes = 0
        self._is_opened = False 

        # Stream should save this flags because read, write should be started
        # with last states when read, write was excuted by event handler.
        self._bytes_to_read = None
        self._delimiter = None

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
        self._bytes_to_read = bytes_to_read
        return self._process_read()
    
    def read_until(self, delimiter):
        """Read until first occurrence of `delimiter`.
        Returned chunk that contains `delimiter`
        
        """
        if not isinstance(delimiter, basestring):
            raise StreamError('`read_until` can only accept `str` param')
        self.delimiter = delimiter
        return self._process_read()

    def _process_read(self):
        """fd -> read buffer -> memory"""
        while self.opened:
            if self._to_read_buffer() == 0:
                # End of read
                break
        return self._read()

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

    def _read(self):
        """Read chunk from `_read_buffer` and Returns chunk.

        """
        # XXX: handle delimenter
        read_bytes = 0
        if self.bytes_to_read is not None:
            read_bytes = min(self.bytes_to_read, self._read_buffer_bytes)
            return self._pop_chunk(read_bytes)
        
        if self.delimiter is not None:
            while True:
                pos = self._read_buffer[0].find(self.delimiter)
                if pos != -1:
                    # Found delimiter
                    return self._pop_chunk(pos + len(self.delimiter))
                
                if len(self._read_buffer) == 1:
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
    
    def write(self, chunk):
        if not isinstance(chunk, basestring):
            raise StreamError('Can write only chunk of `bytes`')
        
        for i in range(0, len(chunk), self._write_chunk_size):
            self._write_buffer.append(chunk[0:i + self._write_chunk_size])
        
        self._process_write()
    
    def _process_write(self):
        while self._write_buffer:
            try:
                num_bytes = self._write_to_fd(self._write_buffer[0])
                if num_bytes == 0:
                    self._write_buffer.frozen = True
                    break

                self._write_buffer.frozen = False

                # Partial write is handled here.
                self._write_buffer.gather(num_bytes)
                self._write_buffer.popleft()
            except socket.error as e:
                if e.args[0] in EWOULDBLOCK:
                    # Freeze
                    self._write_buffer.frozen = True
                elif e.args[0] in ECONNRESET:
                    self.close()
                else:
                    raise StreamError(e)
                return

        # Post write process.

    def _write_to_fd(self):
        raise NotImplementedError()
    
    def _handle_write(self):
        """Handle write process when fd is available.
        This method will be passed to event handler of `looper`
        
        """
        self._process_write()

    def _handle_read(self):
        """Handle read process when fd is available.
        This method will be passed to event handler of `looper`
        
        """
        self._process_read()


class SocketStream(BaseStream):
    def __init__(self, socket, *args, **kwargs):
        if not isinstance(socket, socket.socket):
            raise StreamError(
                'SocketStream can only be initialized with `socket.socket`')
        self.socket = socket
        super(SocketStream, self).__init__(*args, **kwargs)

    def _read_from_fd(self):
        try:
            chunk = self.socket.recv(self._read_chunk_size)
            if not chunk:
                # Should close stream here because nothing is left to be read.
                self.close()
                return None
            return chunk
        except socket.error as e:
            if e.args[0] not in EWOULDBLOCK:
                raise
            return None

    def _write_to_fd(self, chunk):
        self.socket.send(chunk)


class FileStream(BaseStream):
    def __init__(self, file_, *args, **kwargs):
        if not isinstance(file_, file):
            raise StreamError(
                'FileStream can only be initialized with `file`')
        self.file_ = file_
        super(FileStream, self).__init__(*args, **kwargs)

    def _read_from_fd(self):
        return self.file_.read(self._read_chunk_size)
            
    def _write_to_fd(self, chunk):
        try:
            self.file_.write(chunk)
        except IOError as e:
            raise StreamError(e)

