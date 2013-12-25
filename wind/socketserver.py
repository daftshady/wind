# -*- coding:utf-8 -*-
"""

    wind.server
    ~~~~~~~~~~~

    Base server and TCP implementations.

"""


import socket
import errno
from wind.exceptions import SocketException
from wind.looper import PollLooper


class BaseServer(object):
    """Base implementation for server classes"""
    pass


class TCPServer(BaseServer):
    """Non-blocking, single-threaded TCP Server"""
    # It will consume kernel resource
    backlog_size = 128

    def __init__(self, looper=None):
        """Initialize tcp server.

        :param looper: io looper for simply running this server
        """
        self.looper = looper or PollLooper.instance()
        self.socket = None
    
    def _bind_socket(
        self, address, port, family=socket.AF_INET, 
        socket_type=socket.SOCK_STREAM):
        """Creates listening non-blocking socket bound to given address
        
        TODO: 
        Sockets should be bound all ip address if `address` is 
        a hostname.
        """
        if self.socket is not None:
            raise SocketException('Socket is already bound')
        
        try:
            socket_ = socket.socket(family, socket_type)
        except socket.error as e:
            if e.args[0] == errno.EAFNOSUPPORT:
                continue
            raise SocketException('Socket creation failed')
        
        socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_.setblocking(0)
        socket_.bind((address, port))
        socket_.listen(self.backlog_size)
        return socket_
    
    def bind(self, address, port):
        """Binds socket"""
        self.socket = self._bind_socket(address, port)
    
    def listen(self, address, port):
        """Binds socket and actually run looper"""
        self.bind(address, port)

    def run_simple(self, address, port, single_handler):
        """Simply run tcp server with single-process"""
        pass


class UDPServer(BaseServer):
    # TODO : Planned to be implemented later.
    pass
