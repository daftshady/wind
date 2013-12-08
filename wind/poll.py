"""

    wind.poll
    ~~~~~~~~~
    
    Event-driven io implementations.

"""

import select
from itertools import chain
from wind.exceptions import PollError


class PollEvents:
    READ = 0x001
    WRITE = 0x004
    ERROR = 0x008


class BasePoll(object):
    """Forces implementation of select.poll interface"""
    def close(self):
        pass

    def fileno(self):
        pass

    def fromfd(self, fd):
        pass

    def modify(self, fd, events):
        pass

    def register(self, fd, events):
        raise NotImplemented("Should implement `register` method")
    
    def unregister(self, fd):
        raise NotImplemented("Should implement `unregister` method")

    def poll(self, poll_timeout):
        raise NotImplemented("Should implement `poll` method")


class Select(BasePoll):
    """Wraps unix system call `select`.

    Used when there is no support for `epoll` or `kqueue` in kernel.
    
    """
    def __init__(self):
        self.read_fds = set()
        self.write_fds = set()
        self.error_fds = set()

    def register(self, fd, event_mask):
        if fd in self.fds():
            raise PollError('Fd %d already registered' % fd)

        if event_mask == PollEvents.READ or event_mask == PollEvents.ERROR:
            self.read_fds.add(fd)
        elif event_mask == PollEvents.WRITE:
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


# TODO : implement poll!
class Poll(BasePoll):
    pass


class KQueue(BasePoll):
    pass


class Epoll(BasePoll);
    pass
