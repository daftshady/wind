"""

    wind.datastructures
    ~~~~~~~~~~~~~~~~~~~

    Useful datastructures.

"""

import collections


class FlexibleDeque(collections.deque):
    """Deque for easily handling separable object like `bytes`."""

    def gather(self, chunk_size, left=True):
        """Gather bytes to side of Deque by `chunk_size`
        This method assumes that all items in `deque` are `bytes`

            >>> q = FlexibleDeque([b'y', b'-', b'combinator', b'...'])
            >>> q.gather(12)
            >>> q
            FlexibleDeque(['y-combinator','...'])

        """
        counted = 0
        chunks = collections.deque()

        if left:
            append_ = self.appendleft
            pop_ = self.popleft
            append_chunk_ = chunks.append
        else:
            append_ = self.append
            pop_ = self.pop
            append_chunk_ = chunks.appendleft

        while self:
            data = pop_()
            len_ = len(data)
            if counted + len_ < chunk_size:
                append_chunk_(data)
                counted += len_

                if not self:
                    append_(b''.join(chunks))
                    break
            else:
                slash = counted + len_ - chunk_size
                if left:
                    slash = len_ - slash
                    append_chunk_(data[:slash])
                    if slash < len_:
                        append_(data[slash:])
                else:
                    append_chunk_(data[slash:])
                    if slash < len_:
                        append_(data[:slash])
                append_(b''.join(chunks))
                break

    def throw(self, chunk_size, left=True):
        """Gather by `chunk_size` and pop from deque.
        If left is true, pop left. If not, pop right.

        """
        self.gather(chunk_size, left=left)
        if left:
            return self.popleft()
        else:
            return self.pop()

    def __repr__(self):
        name = self.__class__.__name__
        if not self:
            return '%s()' % (name)
        return '%s(%s)' % (name, str(list(self)))


class FlexibleDict(collections.MutableMapping):
    """Provides flexible transformations to dict `key`"""
    def __init__(self, dict_=None):
        # `_store` stores (key, value) tuple on each key.
        self._store = {}
        if dict_ is not None:
            self.update(dict_)

    def _transform(self, key):
        return key

    def __getitem__(self, key):
        key = self._transform(key)
        if self._store.get(key) is None:
            return None
        else:
            return self._store.get(key)[1]

    def __setitem__(self, key, value):
        self._store[self._transform(key)] = (key, value)

    def __delitem__(self, key):
        del self._store[self._transform(key)]

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, dict(self.items()))


class CaseInsensitiveDict(FlexibleDict):
    """Case-insensitivie `Dict`.
    Keys of this dict object will be case-insensitive.

        >>> dict_ = CaseInsensitvieDict()
        >>> dict_['club'] = 'octagon'
        >>> dict_.get('CLUB')
        octagon
        >>> dict_.get('CluB') == dict_.get('ClUb')
        True

    """
    def get(self, key, default=None):
        """Override get here to use default value params"""
        value = super(CaseInsensitiveDict, self).__getitem__(key)
        return default if value is None else value

    def _transform(self, key):
        return key.lower()

    def __iter__(self):
        return (original_key for original_key, value in self._store.values())
