"""

    wind.socketserver
    ~~~~~~~~~~~~~~~~~

    Base server and TCP implementations.

"""


import socket
import errno
from wind.looper import Looper
from wind.poll import PollEvents
from wind.exceptions import SocketError, ServerError


# Defines frequently used collection of socket.error
# XXX: Should this tuples be here?
EWOULDBLOCK = (errno.EWOULDBLOCK, errno.EAGAIN)
ECONNRESET = (errno.ECONNRESET, errno.ECONNABORTED, errno.EPIPE)


class BaseServer(object):
    """Base implementation for server classes"""
    pass


class TCPServer(BaseServer):
    """Non-blocking, single-threaded TCP Server implementation.

    Methods for the caller:

    - __init__(looper=None)
    - bind(address, port)
    - listen(address, port)
    - attach_sockets(sockets=[])
    - run_simple(address, port)  
    
    Methdos should be overrided

    - _connection_handler(conn, address)
    

    """
    # It will consume kernel resource
    backlog_size = 128

    def __init__(self, looper=None):
        """Initialize tcp server.

        :param looper: `Looper` for simply running this server
        """
        self.looper = looper or Looper.instance()
        self._sockets = []
    
    def bind(self, address, port):
        """Binds socket on specified address, port"""
        self._sockets.append(self._bind_socket(address, port))

    def _bind_socket(
        self, address, port, family=socket.AF_INET, 
        socket_type=socket.SOCK_STREAM):
        """Creates listening non-blocking socket bound to given address
        
        TODO: 
        Sockets should be bound all ip address if `address` is 
        a hostname.
        """
        if self._sockets:
            raise SocketException('Socket is already bound')
        
        try:
            socket_ = socket.socket(family, socket_type)
        except socket.error as e:
            raise SocketException('Socket creation failed')
        
        socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_.setblocking(0)
        socket_.bind((address, port))
        socket_.listen(self.backlog_size)
        return socket_
   
    def listen(self, address, port):
        """Binds socket and actually attach this server on looper"""
        self.bind(address, port)
        self._bind_to_looper()

    def run_simple(self, address, port):
        """Simply run tcp server with single-process"""
        self.listen(address, port)
        self.looper.run()

    def attach_sockets(self, sockets=[]):
        """Attach extra sockets to tcp server instance"""
        self._bind_to_looper(sockets=sockets)
   
    def _bind_to_looper(self, sockets=[]):
        """Bind sockets to looper.
        This must be called before actual running of server
        because initialized sockets must be bound to looper
        
        @param sockets: Extra sockets to be bound on this server.
        """
        self._sockets.extend(sockets)
        for socket_ in self._sockets:
            self._attach_accept_handler(socket_, self._connection_handler)
                
    def _attach_accept_handler(self, socket_, callback):
        """Attach `_event_handler` to socket"""
        def _accept_handler(fd, event_mask):
            """Handle socket accept and execute callback"""
            while True:
                try:
                    conn, address = socket_.accept()
                    conn.setblocking(0)
                except socket.error as e:
                    if e.args[0] in EWOULDBLOCK:
                        return
                    raise
            
                try:
                    callback(conn, address)
                except TypeError:
                    #raise ServerError('Accept handler callback is not vaild form')
                    raise

        self.looper.attach_handler(
            socket_.fileno(), PollEvents.READ, _accept_handler)
    
    def _connection_handler(self, conn, address):
        raise NotImplementedError


class UDPServer(BaseServer):
    # TODO : Planned to be implemented later.
    pass


