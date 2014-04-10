# -*- coding:utf-8 -*-
"""

    wind.looper
    ~~~~~~~~~~~

    Handles io loop for serving client request.

"""

import errno
import socket
import select
import threading

from wind.driver import pick, Select, PollEvents
from wind.exceptions import LooperError, EWOULDBLOCK


class PollLooper(object):
    """Event looper powering io multiplexing.

    Methods for the caller.

    - __init__(driver=None)
    - instance()
    - attach_handler()
    - update_handler()
    - remove_handler()
    - attach_callback()
    - run(poll_timeout=500)
    - stop()

    Methods can be overrided

    - initialize()

    """
    _NO_TIMEOUT = 0.0
    _DEFAULT_POLL_TIMEOUT = 500.0
    _singleton_lock = threading.Lock()

    def __init__(self, driver=None):
        """Event driven io loop using `poll`

        :param driver: Actual unix system call implementing io multiplexing

        """
        super(PollLooper, self).__init__()
        self._running = False
        self._handlers = {}
        self._events = {}
        self._driver = driver or pick()
        self._callbacks = []
        self.initialize()

    def initialize(self):
        """Initialize hook. Can be overrided"""
        self._setup_heartbeat()

    def _setup_heartbeat(self):
        """Initialize heartbeat for looper instance and
        attach one byte handler.

        """
        self._heartbeat = Heartbeat()
        self.attach_handler(
            self._heartbeat.reader.fileno(), PollEvents.READ,
            self._heartbeat.read_handler)

    @staticmethod
    def instance():
        """Initialize singleton instance of Looper
        with double-checked locking

        Returns singleton looper in `main thread`
        """
        if not hasattr(PollLooper, '_instance'):
            with PollLooper._singleton_lock:
                if not hasattr(PollLooper, '_instance'):
                    # Choose suitable driver here.
                    PollLooper._instance = PollLooper(driver=pick())
        return PollLooper._instance

    def attach_handler(self, fd, event_mask, handler):
        """Attach event handler to given fd.
        @param fd: file descriptor to be observed.
        @param event_mask: event to be observed.
        @param handler: handler to be executed when given event happens.

        """
        self._handlers[fd] = handler
        self._driver.register(fd, event_mask)

    def update_handler(self, fd, event_mask):
        """Update event handler to given fd.
        @param fd: file descriptor to be observed.
        @param event_mask: event to be observed.

        """
        self._driver.modify(fd, event_mask)

    def remove_handler(self, fd):
        """Remove event handler to given fd.
        @param fd: file descriptor to be observed.
        @param event_mask: event to be observed.

        """
        self._driver.unregister(fd)
        self._handlers.pop(fd, None)

    def attach_callback(self, callback):
        self._callbacks.append(callback)
        if hasattr(self, '_heartbeat'):
            self._heartbeat.begin()

    def _run_callback(self):
        try:
            for callback in self._callbacks:
                callback()
            self._callbacks = []
        except Exception as e:
            # TODO: Log exception.
            # We are eatting error!
            pass

    def run(self, poll_timeout=_DEFAULT_POLL_TIMEOUT):
        self._running = True
        while True:
            if not self._running:
                break
            timeout = poll_timeout
            self._run_callback()
            if self._callbacks:
                # If another callback is attached while running callback.
                timeout = self._NO_TIMEOUT

            # Poll returns `List` of (fd, event) tuple
            try:
                events = self._driver.poll(timeout)
            except (OSError, select.error) as e:
                if e.args[0] != errno.EINTR:
                    raise

            self._events.update(events)
            while self._events:
                fd, event_mask = self._events.popitem()
                handler = self._handlers.get(fd, None)
                if handler is None:
                    # XXX: should be handled properly
                    pass
                try:
                    handler(fd, event_mask)
                except TypeError:
                    # XXX: should be handled properly
                    raise

    def stop(self):
        self._running = False

Looper = PollLooper


class Heartbeat(object):
    """Heartbeat for looper.
    if another thread tries to attach callback while `looper`
    is hanging inside the poll, we should bypass poll and rush
    into a next loop because callback may be executed in the next loop.
    We will force it by sending one byte request.

    Methods for the caller.

    - __init__()
    - begin()
    - end()
    - die()

    """
    def __init__(self):
        self._sock = None
        self._reader = None
        self._writer = None
        self._setup()

    @property
    def reader(self):
        return self._reader

    @property
    def writer(self):
        return self._writer

    @property
    def read_handler(self):
        return lambda fd, event_mask : self.end()

    def _setup(self):
        """Setup instant server for one byte communication.
        We don't care about a port number of instant server because
        it's not for accepting connection. OS will pick it up for us.

        """
        try:
            self._sock = socket.socket()
            self._sock.bind(('localhost', 0))
            self._sock.listen(1)
            self._writer = socket.socket()
            self._writer.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self._writer.connect(self._sock.getsockname())
            self._reader = self._sock.accept()[0]
            self._writer.setblocking(0)
            self._reader.setblocking(0)
            # Close instant socket because we don't need it anymore.
        except Exception as e:
            pass

    def begin(self):
        """Start new heartbeat, which will force looper to run"""
        try:
            self._writer.send(b'q')
        except socket.error as e:
            if e.args[0] in EWOULDBLOCK:
                pass
            else:
                raise e

    def end(self):
        """This method is attached to looper to finish one hearbeat cycle
        by receiving one byte from heartbeat writer.

        """
        try:
            while True:
                blood = self._reader.recv(1)
                if not blood:
                    # end of read
                    break
        except socket.error as e:
            if e.args[0] in EWOULDBLOCK:
                pass
            else:
                raise e

    def die(self):
        """Close all sockets"""
        self._sock.close()
        self._writer.close()
        self._reader.close()
