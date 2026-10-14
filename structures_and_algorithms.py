"""ParkFlow data structures and algorithms module.
Core OOP entities belong in core.py; this module operates on objects/dicts.
Run smoke tests: python structures_and_algorithms.py
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Generic, Iterable, Optional, TypeVar
T = TypeVar('T'); K = TypeVar('K'); V = TypeVar('V')

@dataclass
class AlgorithmStats:
    comparisons: int = 0
    swaps: int = 0
    recursive_calls: int = 0
    steps: int = 0
    def reset(self): self.comparisons = self.swaps = self.recursive_calls = self.steps = 0
    def as_dict(self): return {'comparisons': self.comparisons, 'swaps': self.swaps, 'recursive_calls': self.recursive_calls, 'steps': self.steps}

@dataclass
class _StackEntry:
    value: Any
    undo_callback: Optional[Callable[[], Any]] = None

class Stack:
    """LIFO stack; optional callbacks let callers reverse real actions."""
    def __init__(self): self._items: list[_StackEntry] = []
    def push(self, value, undo_callback=None): self._items.append(_StackEntry(value, undo_callback))
    def pop(self):
        if not self._items: raise IndexError('Cannot pop from an empty stack.')
        return self._items.pop().value
    def peek(self):
        if not self._items: raise IndexError('Cannot peek at an empty stack.')
        return self._items[-1].value
    def undo_last(self):
        if not self._items: return None
        entry = self._items.pop()
        return entry.undo_callback() if entry.undo_callback else entry.value
    def is_empty(self): return not self._items
    def size(self): return len(self._items)
    def clear(self): self._items.clear()
    def __len__(self): return len(self._items)

class Queue(Generic[T]):
    """FIFO queue with amortized O(1) enqueue/dequeue."""
    def __init__(self): self._items: list[T] = []; self._front = 0
    def enqueue(self, item: T): self._items.append(item)
    def dequeue(self) -> T:
        if self.is_empty(): raise IndexError('Cannot dequeue from an empty queue.')
        item = self._items[self._front]; self._front += 1
        if self._front >= 32 and self._front * 2 >= len(self._items):
            self._items = self._items[self._front:]; self._front = 0
        return item
    def peek(self) -> T:
        if self.is_empty(): raise IndexError('Cannot peek at an empty queue.')
        return self._items[self._front]
    def is_empty(self): return self._front >= len(self._items)
    def size(self): return len(self._items) - self._front
    def to_list(self): return self._items[self._front:].copy()
    def __len__(self): return self.size()

class HashTable(Generic[K, V]):
    """Custom hash table using open addressing + linear probing."""
    _EMPTY = object(); _DELETED = object()
    def __init__(self, capacity=8):
        self._capacity = max(4, capacity); self._keys = [self._EMPTY] * self._capacity
        self._values = [None] * self._capacity; self._size = 0; self.stats = AlgorithmStats()
    def _find_slot(self, key, for_insert=False):
        index = hash(key) % self._capacity; first_deleted = -1
        for _ in range(self._capacity):
            self.stats.steps += 1; current = self._keys[index]
            if current is self._EMPTY:
                return first_deleted if for_insert and first_deleted != -1 else (index if for_insert else -1)
            if current is self._DELETED:
                if first_deleted == -1: first_deleted = index
            else:
                self.stats.comparisons += 1
                if current == key: return index
            index = (index + 1) % self._capacity
        return first_deleted if for_insert else -1
    def _resize(self, capacity):
        pairs = self.items(); self._capacity = max(4, capacity)
        self._keys = [self._EMPTY] * self._capacity; self._values = [None] * self._capacity; self._size = 0
        for key, value in pairs: self[key] = value
    def __setitem__(self, key: K, value: V):
        if (self._size + 1) / self._capacity >= .70: self._resize(self._capacity * 2)
        index = self._find_slot(key, True)
        if index == -1:
            self._resize(self._capacity * 2); index = self._find_slot(key, True)
        if self._keys[index] is self._EMPTY or self._keys[index] is self._DELETED: self._size += 1
        self._keys[index] = key; self._values[index] = value
    def __getitem__(self, key):
        i = self._find_slot(key)
        if i == -1: raise KeyError(key)
        return self._values[i]
    def get(self, key, default=None):
        i = self._find_slot(key); return default if i == -1 else self._values[i]
    def __contains__(self, key): return self._find_slot(key) != -1
    def delete(self, key):
        i = self._find_slot(key)
        if i == -1: return False
        self._keys[i] = self._DELETED; self._values[i] = None; self._size -= 1; return True
    def keys(self): return [k for k in self._keys if k is not self._EMPTY and k is not self._DELETED]
    def values(self): return [v for i, k in enumerate(self._keys) if k is not self._EMPTY and k is not self._DELETED for v in [self._values[i]]]
    def items(self): return [(k, self._values[i]) for i, k in enumerate(self._keys) if k is not self._EMPTY and k is not self._DELETED]
    def __len__(self): return self._size

def _field(item, *names, default=None):
    for name in names:
        if isinstance(item, dict) and name in item: return item[name]
        if hasattr(item, name): return getattr(item, name)
    return default

def linear_search(items: Iterable[T], target: Any, key: Callable[[T], Any] = lambda x: x, stats: Optional[AlgorithmStats] = None) -> int:
    """Search unsorted data; return first index or -1."""
    stats = stats or AlgorithmStats()
    for i, item in enumerate(items):
        stats.comparisons += 1; stats.steps += 1
        if key(item) == target: return i
    return -1

def binary_search(sorted_items: list[T], target: Any, key: Callable[[T], Any] = lambda x: x, stats: Optional[AlgorithmStats] = None) -> int:
    """Binary search; input MUST be sorted ascending by key(item)."""
    stats = stats or AlgorithmStats(); left, right = 0, len(sorted_items) - 1
    while left <= right:
        stats.steps += 1; mid = (left + right) // 2; current = key(sorted_items[mid]); stats.comparisons += 1
        if current == target: return mid
        if current < target: left = mid + 1
        else: right = mid - 1
    return -1

def merge_sort(items: Iterable[T], key: Callable[[T], Any] = lambda x: x, stats: Optional[AlgorithmStats] = None) -> list[T]:
    """Stable manual Merge Sort: O(n log n) time."""
    stats = stats or AlgorithmStats(); data = list(items)
    def merge(left, right):
        result = []; i = j = 0
        while i < len(left) and j < len(right):
            stats.comparisons += 1; stats.steps += 1
            if key(left[i]) <= key(right[j]): result.append(left[i]); i += 1
            else: result.append(right[j]); j += 1
        result.extend(left[i:]); result.extend(right[j:]); return result
    def sort(part):
        stats.recursive_calls += 1
        if len(part) <= 1: return part
        mid = len(part) // 2
        return merge(sort(part[:mid]), sort(part[mid:]))
    return sort(data)

def _normalise_size(value):
    return None if value is None else str(value).strip().lower().replace('_', ' ').replace('-', ' ')

def _fits(vehicle, spot):
    v = _normalise_size(_field(vehicle, 'size', 'vehicle_size', 'vehicle_type'))
    s = _normalise_size(_field(spot, 'size', 'spot_size', 'vehicle_size'))
    if not v or not s: return True
    ranks = {'motorcycle': 0, 'bike': 0, 'small': 1, 'compact': 1, 'car': 2, 'sedan': 2, 'medium': 2, 'suv': 3, 'large': 3, 'van': 3, 'truck': 4, 'oversized': 4, 'heavy': 4}
    return True if v not in ranks or s not in ranks else ranks[v] <= ranks[s]

def greedy_allocate_spot(vehicle: Any, spots: Iterable[T], strategy='cheapest', stats: Optional[AlgorithmStats] = None) -> Optional[T]:
    """Pick cheapest compatible free spot; returns it but does not occupy it."""
    stats = stats or AlgorithmStats(); candidates = []
    for spot in spots:
        stats.steps += 1; stats.comparisons += 1
        available = _field(spot, 'is_available', 'available', default=None)
        occupied = _field(spot, 'is_occupied', 'occupied', default=False)
        is_free = bool(available) if available is not None else not bool(occupied)
        if is_free and _fits(vehicle, spot): candidates.append(spot)
    if not candidates: return None
    if strategy == 'cheapest':
        best = candidates[0]
        for spot in candidates[1:]:
            stats.comparisons += 1
            if _field(spot, 'hourly_rate', 'rate', default=float('inf')) < _field(best, 'hourly_rate', 'rate', default=float('inf')): best = spot
        return best
    if strategy == 'lowest_floor':
        return min(candidates, key=lambda x: _field(x, 'floor', 'floor_number', default=float('inf')))
    raise ValueError("strategy must be 'cheapest' or 'lowest_floor'")

def index_by(items: Iterable[T], key: Callable[[T], K]) -> HashTable[K, list[T]]:
    """Build a custom hash-table index; repeated keys map to lists."""
    result: HashTable[K, list[T]] = HashTable()
    for item in items:
        k = key(item); existing = result.get(k)
        if existing is None: result[k] = [item]
        else: existing.append(item)
    return result

def compare_search_methods(items: list[T], target: Any, key: Callable[[T], Any] = lambda x: x) -> dict[str, Any]:
    """Return results and counters for linear search, Merge Sort, and binary search."""
    ls = AlgorithmStats(); li = linear_search(items, target, key, ls)
    ms = AlgorithmStats(); ordered = merge_sort(items, key, ms)
    bs = AlgorithmStats(); bi = binary_search(ordered, target, key, bs)
    return {'linear_index': li, 'linear_stats': ls.as_dict(), 'sorted_items': ordered,
            'merge_sort_stats': ms.as_dict(), 'binary_index_in_sorted_items': bi, 'binary_stats': bs.as_dict()}

__all__ = ['AlgorithmStats', 'Stack', 'Queue', 'HashTable', 'linear_search', 'binary_search', 'merge_sort', 'greedy_allocate_spot', 'index_by', 'compare_search_methods']

if __name__ == '__main__':
    s = Stack(); s.push('action', lambda: 'undone'); assert s.undo_last() == 'undone' and s.is_empty()
    q = Queue(); q.enqueue(1); q.enqueue(2); assert q.dequeue() == 1 and q.dequeue() == 2 and q.is_empty()
    h = HashTable(); h['A'] = 1; h['B'] = 2; assert h['A'] == 1 and h.delete('A') and 'A' not in h
    values = [7, 2, 9, 1, 5]; assert merge_sort(values) == [1, 2, 5, 7, 9]
    assert linear_search(values, 9) == 2 and binary_search([1, 2, 5, 7, 9], 5) == 2
    print('All structures_and_algorithms.py smoke tests passed.')
