"""

    wind.socketserver
    ~~~~~~~~~~~~~~~~~

    Base socket server and TCP, UDP implementations.

"""


import socket
from wind.reactor import Reactor
from wind.driver import PollEvents
from wind.concurrency import start_workers
from wind.exceptions import ServerError, SocketError, EWOULDBLOCK


class BaseServer(object):
    """Base implementation for server classes.
    Features in this `BaseServer` are implemented for Event-driven IO.
    So, you should pass event observer when initializing this.

    Methods for the caller:

    - __init__(reactor=None)
    - bind(address, port)
    - listen(address, port)
    - attach_sockets(sockets)
    - run_simple(address, port=9000)

    Methods that may be overrided:

    - bind(address, port)
    - listen(address, port)
    - _attach_accept_handler
    - _event_handler(conn, address)

    """
    def __init__(self, reactor=None):
        """Initialize BaseServer.

        @param reactor: Event reactor.
        """
        self.reactor = reactor
        self._sockets = []

    def bind(self, address, port):
        """Makes this server to be bound to address in specific port.
        This method create sockets and calls `bind` method in `socket` api.

        """
        raise NotImplementedError

    def listen(self, address, port):
        """Makes sockets to be bound to address in specific port
        and attachs accept handler to event observer(`reactor`).

        """
        raise NotImplementedError

    def attach_sockets(self, sockets):
        """Attach extra sockets to tcp server instance"""
        if not isinstance(sockets, list):
            raise SocketError('`attach_sockets` can only accept `list`')
        self._bind_to_reactor(sockets=sockets)

    def run(self, address, port, num_workers=None):
        """This method can start tcp server with multi-process features.
        By default, if `num_workers` is None, N(number of cpu cores) processes
        will be spawned from this method.
        NOTE that this method starts N independent `Reactor`.
        If you already started `Reactor` from main process and attached sockets
        to it, whole server system will be broken if you spawn processes after
        that. Because each child process should have its own `Reactor` instance
        by calling `instance` method in reactor.

        @param num_workers(optional):
            If None, this method will start automatically detected number of
            processes. (which may be number of cpu cores).

        """
        if Reactor.exist():
            raise ServerError('`Reactor` is already started on main process.')

        self.bind(address, port)

        start_workers(num_workers=num_workers)

        self.reactor = Reactor.instance()
        self._bind_to_reactor()
        self.reactor.run()

    def run_simple(self, address, port=9000):
        """Simply run server with single-process"""
        self.reactor = Reactor.instance()
        self.listen(address, port)
        self.reactor.run()

    def _create_socket(self, family, socket_type):
        try:
            socket_ = socket.socket(family, socket_type)
            return socket_
        except socket.error:
            raise SocketError('Socket creation failed')

    def _bind_to_reactor(self, sockets=None):
        """Bind sockets to reactor.
        This must be called before actual run of server
        because initialized sockets must be registered to reactor.

        @param sockets:
            Extra `list` of sockets to be bound on this server.
            Note that if `sockets` is not None, this method attaches handler to
            objects in `sockets` only.

        """
        if sockets is not None:
            self._sockets.extend(sockets)
        for socket_ in self._sockets if sockets is None else sockets:
            self._attach_accept_handler(socket_, self._event_handler)

    def _attach_accept_handler(self, socket_, callback):
        """Attach `_accept_handler` to socket"""
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

                callback(conn, address)

        if hasattr(self.reactor, 'attach_handler'):
            self.reactor.attach_handler(
                socket_.fileno(), PollEvents.READ, _accept_handler)
        else:
            raise ServerError('`reactor` has no attribute `attach_handler`')

    def _event_handler(self, conn, address):
        """This method will be registered in event observer(`reactor`)
        with sockets already bound to address.
        When `READ` is catched by observer, this method will serve connection.

        """

        raise NotImplementedError


class TCPServer(BaseServer):
    """Non-blocking, single-threaded TCP Server implementation.

    Methods for the caller:

    - __init__(reactor=None)
    - bind(address, port)
    - listen(address, port)
    - attach_sockets(sockets)
    - run_simple(address, port=9000)

    Methods that should be overrided

    - _event_handler(conn, address)

    """

    # It will consume kernel resource
    backlog_size = 128

    def __init__(self, reactor=None):
        """Initialize tcp server.

        """
        super(TCPServer, self).__init__(reactor=reactor)

    def bind(self, address, port):
        """Binds socket on specified address, port"""
        self._sockets.append(self._bind_socket(address, port))

    def _bind_socket(self, address, port):
        """Creates listening non-blocking socket bound to given address

        TODO:
        Sockets should be bound all ip address if `address` is
        a hostname.
        """
        socket_ = self._create_socket()
        socket_.bind((address, port))
        socket_.listen(self.backlog_size)
        return socket_

    def _create_socket(self):
        """Create new stream non-blocking socket and returns it."""
        socket_ = super(TCPServer, self). \
            _create_socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_.setblocking(0)
        return socket_

    def listen(self, address, port):
        """Binds socket and actually attach this server on reactor"""
        self.bind(address, port)
        self._bind_to_reactor()

    def _event_handler(self, conn, address):
        raise NotImplementedError


class UDPServer(BaseServer):
    # TODO : Planned to be implemented later.
    pass
