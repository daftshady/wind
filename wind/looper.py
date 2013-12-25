# -*- coding:utf-8 -*-
"""

    wind.looper
    ~~~~~~~~~~~

    Handles io loop for serving client request.

"""

import errno
import threading

from wind.exceptions import LooperError
from wind.poll import PollEvents, Select

# XXX : Remove deep interaction of `looper` with `server`

# Taken from `SocketServer.py` temporarily
def _eintr_retry(func, *args):
    """restart a system call interrupted by EINTR"""
    while True:
        try:
            return func(*args)
        except (OSError, select.error) as e:
            if e.args[0] != errno.EINTR:
                raise


class PollLooper(object):
    
    _DEFAULT_POLL_TIMEOUT = 1000

    _singleton_lock = threading.Lock()

    def __init__(self, driver):
        """Event driven io loop using `poll`

        :param driver: Actual unix system call implementing io multiplexing
        """
        super(PollLooper, self).__init__()
        self._running = False
        self._handlers = {}
        self._events = {}
        self._driver = driver

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
                    # Temporarily, we will use `select` for test.
                    PollLooper._instance = PollLooper(Select())
        return PollLooper._instance

    def attach_handler(self, fd, handler, event_mask):
        self._handlers[fd] = handler
        self._driver.register(fd, event_mask)
    
    def update_handler(self, fd, event_mask):
        self._driver.modify(fd, event_mask)

    def remove_handler(self, fd):
        self._driver.unregister(fd)
        self._handlers.pop(fd, None)

    def run(self, poll_timeout=_DEFAULT_POLL_TIMEOUT):
        self._running = True
        while True:
            if not self._running:
                break
            
            # Poll returns `List` of (fd, event) tuple
            events = _eintr_retry(self._driver.poll, poll_timeout)
            self._events.update(events)

            while self._events:
                fd, event_mask = self._events.popitem()
                handler = self._handlers.get(fd, None)
                if handler is None:
                    # XXX : should be handled properly
                    pass
                try:
                    handler(fd, event_mask)
                except TypeError:
                    # XXX : should be handled properly
                    pass

    def stop(self):
        self._running = False

Looper = PollLooper
