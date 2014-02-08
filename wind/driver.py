"""

    wind.driver
    ~~~~~~~~~~~
    
    Drivers for io multiplexing. 

"""

import select
from itertools import chain
from wind.exceptions import PollError, WindException


def pick():
    """Pick best event driver depending on OS.
    `Select`, `Poll` are available in most OS.
    `Epoll` is available on Linux 2.5.44 and newer.
    `KQueue` is available on most BSD.
    
    """
    try:
        candidates = ['select', 'poll', 'epoll']
        driver = filter(lambda x : hasattr(select, x), candidates)[-1]
        return eval(driver.title())().instance
    except (IndexError, NameError) as e:
        raise WindException('No available event driver')


class PollEvents:
    READ = 0x001
    WRITE = 0x004
    ERROR = 0x008


class BaseDriver(object):
    """Forces implementation of select.epoll interface"""
    def __init__(self):
        self._driver = None

    def close(self):
        pass

    def fileno(self):
        pass

    def fromfd(self, fd):
        pass

    def modify(self, fd, event_mask):
        pass

    def register(self, fd, event_mask):
        raise NotImplemented("Should implement `register` method")
    
    def unregister(self, fd):
        raise NotImplemented("Should implement `unregister` method")

    def poll(self, poll_timeout):
        raise NotImplemented("Should implement `poll` method")
    
    @property
    def instance(self):
        return self._driver


class Select(BaseDriver):
    """Wraps unix system call `select`.

    Used when there is no support for `epoll` or `kqueue` in kernel.
    
    """
    def __init__(self):
        self.read_fds = set()
        self.write_fds = set()
        self.error_fds = set()
        self._driver = self

    def register(self, fd, event_mask):
        if fd in self.fds():
            raise PollError('Fd %d already registered' % fd)

        if event_mask & PollEvents.READ or event_mask & PollEvents.ERROR:
            self.read_fds.add(fd)
        elif event_mask & PollEvents.WRITE:
            self.write_fds.add(fd)
        else:
            raise PollError('Cannot register undefined event')

    def unregister(self, fd):
        self.read_fds.discard(fd)
        self.write_fds.discard(fd)
        self.error_fds.discard(fd)
    
    def modify(self, fd, event_mask):
        self.unregister(fd)
        try:
            self.register(fd, event_mask)
        except PollError as e:
            e.args[0] = 'Cannot modify undefined event'
            raise
    
    def poll(self, poll_timeout):
        """Returns `List` of (fd, event) pair

        :param poll_timeout: Value for select timeout.(sec)
        If timeout is `0`, it specifies a poll and never blocks.
        """
        read, write, error = select.select(
            self.read_fds, self.write_fds, self.error_fds, poll_timeout)
        
        events = {}
        for fd in read:
            events[fd] = events.get(fd, 0) | PollEvents.READ
        for fd in write:
            events[fd] = events.get(fd, 0) | PollEvents.WRITE
        for fd in error:
            events[fd] = events.get(fd, 0) | PollEvents.ERROR
        return events.items()

    def fds(self):
        """Returns all fds saved in this object"""
        return set(chain(self.read_fds, self.write_fds, self.error_fds))


class Poll(BaseDriver):
    def __init__(self):
        self._driver = select.poll()


class Epoll(BaseDriver):
    def __init__(self):
        self._driver = select.epoll()


# TODO: implement Kqueue!
