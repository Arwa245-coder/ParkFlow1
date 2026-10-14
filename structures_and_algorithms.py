class Stack:
    def __init__(self):
        self.items = []

    def push(self, item):
        # TODO
        pass

    def pop(self):
        # TODO: Return None if empty
        pass

    def peek(self):
        # TODO: Return None if empty
        pass

    def is_empty(self):
        # TODO
        pass


class Queue:
    def __init__(self):
        self.items = []

    def enqueue(self, item):
        # TODO
        pass

    def dequeue(self):
        # TODO: Return None if empty
        pass

    def peek(self):
        # TODO: Return None if empty
        pass

    def is_empty(self):
        # TODO
        pass


class HashTable:
    def __init__(self, capacity=101):
        self.capacity = capacity
        self.table = [[] for _ in range(capacity)]

    def insert(self, key, value):
        # TODO: Implement hashing, collisions, and insertion/update
        pass

    def search(self, key):
        # TODO: Return value or None
        pass

    def delete(self, key):
        # TODO: Remove key if present
        pass


def linear_search(data, target, key=None):
    # TODO: Return matching item or None
    pass


def binary_search(sorted_data, target, key=None):
    # TODO: Search correctly sorted data using the same key
    pass


def merge_sort(data, key=None):
    # TODO: Implement Merge Sort manually; return a new list
    pass


def greedy_slot_allocation(available_slots, vehicle):
    # TODO: Select a suitable available slot using an explicit rule
    pass
