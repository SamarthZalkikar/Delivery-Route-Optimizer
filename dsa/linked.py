"""
dsa/linked.py -- Unit-I linked structures, hand-rolled on plain nodes.

Used BY the app for:
  * SinglyLinkedList      -> buckets of the chained hash table
  * HeaderLinkedList       -> sparse road-distance matrix (one SLL header per row)
  * CircularLinkedList     -> the "delivery loop" (stops joined into a ring)
  * DoublyLinkedList       -> order history
  * Polynomial             -> transport-cost model cost(d) = a*d^2 + b*d + c
"""
