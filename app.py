"""
Delivery-Route-Optimizer -- Flask app + JSON API.

The Store class owns every DSA structure from dsa/ and is the single source of
state. All input is validated; errors come back as {"error": "..."} with a
proper 4xx code. dict/list literals are used ONLY to shape JSON responses.
"""

from flask import Flask, jsonify, render_template, request

import time
import random

from dsa.linear import DynStack, MinHeapPQ, CircularQueue, SortedListPQ