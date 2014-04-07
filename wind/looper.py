# -*- coding:utf-8 -*-
"""

    wind.looper
    ~~~~~~~~~~~

    Handles io loop for serving client request.

"""

import errno
import select
import threading

from wind.driver import pick, Select
from wind.exceptions import LooperError


class PollLooper(object):
    """Event looper powering io multiplexing.

    Methods for the caller.

    - __init__(self, driver=None)
    - instance()
    - attach_handler()
    - update_handler()
    - remove_handler()
    - attach_callback()
    - run(poll_timeout=500)
    - stop()

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
        self._callback.append(callback)

    def _run_callback(self):
        try:
            for callback in self._callbacks:
                callback()
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
