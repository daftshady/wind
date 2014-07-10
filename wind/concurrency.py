"""

    wind.concurrency
    ~~~~~~~~~~~~~~~~

    Provides concurrency to wind.

"""

import os
import sys
import signal
import itertools
from multiprocessing import cpu_count
from wind.exceptions import ConcurrencyError


class Process(object):
    """Provides multiprocessing features to wind.
    This class is inspired from `multiprocessing.forking` module.
    NOTE that this class only works in `Unix` based system  because there is
    no way to directly call fork in `Windows`.
    (There's a way to imitate it, but we don't.)

    """
    def __init__(self, name=None):
        self._counter = itertools.count(1)
        self._identity = next(_current_process.counter)
        self._parent_pid = os.getpid()
        self._pid = None
        self._name = name or type(self).__name__ + str(self._identity)

    @property
    def pid(self):
        return self._pid

    @property
    def counter(self):
        return self._counter

    def running(self):
        return self._pid is not None

    def start(self):
        """Spawn child process by calling `os.fork`
        This method returns `pid of child` if it's on main process and returns
        `None` otherwise.

        """
        if self.running():
            raise ConcurrencyError(
                'Cannot call `start` to already running process')

        global _current_process
        pid = os.fork()
        if pid == 0:
            self._pid = os.getpid()
            _current_process = self
            return None
        else:
            self._pid = pid
            return self._pid

    def terminate(self):
        os.kill(self._pid, signal.SIGTERM)

    def stop(self, code):
        os._exit(code)


class MainProcess(Process):
    def __init__(self):
        self._counter = itertools.count(0)
        self._identity = next(self._counter)
        self._pid = os.getpid()
        self._name = 'MainProcess'
        self._children = {}

    @property
    def children(self):
        return self._children

    def wait(self):
        while self._children:
            pid, status = os.wait()
            self._children.pop(pid)
        sys.exit(0)


def current_process():
    return _current_process


def start_workers(num_workers=None):
    """Provides multiple workers to wind.
    `Wind` generally do not use multi-thread to boost request handling because
    io stream and handler do not guarantee full thread-safety.
    (it also is a typical weakness of single-threaded event driven model.)
    Instead, `Wind` uses multi-processing to benefits multi cpu cores.
    This method will start workers which is a new process.
    NOTE that this method should be called on main process.

    @param num_workers:
        If `num_workers` is not provided, this method will automatically start
        N(number of cpu cores) processes. If not, this method will start
        N(specific number in num_workers) processes.

    """
    main_process = _current_process
    if num_workers is None:
        num_workers = cpu_count()

    # TODO: Should implement graceful shutdown
    for i in range(num_workers):
        worker = Process()
        pid = worker.start()
        if pid is None:
            # Child process should do the server work.
            return
        main_process.children[pid] = worker
    main_process.wait()


_current_process = MainProcess()
del MainProcess
