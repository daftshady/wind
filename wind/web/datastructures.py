"""

    wind.web.datastructure
    ~~~~~~~~~~~~~~~~~~~~~~

    Useful datastructures.

"""

import collections


class FlexibleDeque(collections.deque):
    """Deque for easily handling separable object like `BaseString`."""

    def gather(self, chunk_size, left=True):
        """Gather string to side of Deque by `chunk_size`
        This method assumes that all items in `deque` are `BaseString`

            >>> q = FlexibleDeque(['y', '-', 'combinator', '...'])
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
                    append_(''.join(chunks))
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

                append_(''.join(chunks))
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

