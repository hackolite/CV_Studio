#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Replay buffer for online knowledge distillation.

Kept in its own module so it can be imported without pulling in the heavy
``cv2`` / ``onnxruntime`` dependencies of ``student_trainer``.
"""

import random
from typing import List, Tuple


class ReservoirBuffer:
    """Diverse replay buffer using reservoir sampling + hard-example mining.

    Unlike a FIFO :class:`collections.deque` (which always evicts the oldest
    frame), reservoir sampling gives every observed frame an equal probability
    of remaining in the buffer at any point in time.  This prevents the buffer
    from being monopolised by the most recent scene and produces a much more
    diverse training set for the replay steps.

    Each entry is tagged with the distillation loss observed at insertion time.
    :meth:`sample` can exploit these tags to bias replay toward the frames
    where the student is still struggling (hard-example mining / curriculum
    learning) while retaining statistical diversity through the reservoir
    design.
    """

    def __init__(self, maxsize: int) -> None:
        self.maxsize = int(maxsize)
        self._items: List[Tuple] = []   # [(payload, loss), …]
        self._n_seen: int = 0

    def add(self, payload, loss: float = 0.0) -> None:
        """Add *payload* with reservoir sampling.

        On overflow a uniformly random existing entry is replaced with
        probability ``maxsize / n_seen``, preserving a uniform sample of all
        frames seen so far.
        """
        self._n_seen += 1
        if len(self._items) < self.maxsize:
            self._items.append((payload, loss))
        else:
            idx = random.randint(0, self._n_seen - 1)
            if idx < self.maxsize:
                self._items[idx] = (payload, loss)

    def sample(self, n: int, hard_mining_ratio: float = 0.7) -> List:
        """Return up to *n* payloads.

        ``hard_mining_ratio`` fraction of the sample is drawn from the
        top-50 % highest-loss frames (hard examples); the rest is drawn
        uniformly at random.  This curriculum bias drives replay toward frames
        where the student is still struggling while preserving diversity.
        """
        k = min(n, len(self._items))
        if k == 0:
            return []
        sorted_items = sorted(self._items, key=lambda x: x[1], reverse=True)
        mid = max(1, len(sorted_items) // 2)
        hard_pool = sorted_items[:mid]
        easy_pool = sorted_items[mid:]
        n_hard = min(int(k * hard_mining_ratio), len(hard_pool))
        n_easy = k - n_hard
        selected = random.sample(hard_pool, n_hard)
        if n_easy > 0 and easy_pool:
            selected += random.sample(easy_pool, min(n_easy, len(easy_pool)))
        return [item[0] for item in selected]

    def clear(self) -> None:
        """Reset the buffer and seen-frame counter."""
        self._items.clear()
        self._n_seen = 0

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(payload for payload, _loss in self._items)
