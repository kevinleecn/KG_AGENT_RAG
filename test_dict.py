#!/usr/bin/env python3
"""Test dictionary with $contains key."""

# Test 1: Direct dictionary creation
print("Test 1: Direct dictionary creation")
d1 = {"$contains": "John"}
print(f"d1: {d1}")
print(f"d1 keys: {list(d1.keys())}")
print(f"d1 repr: {repr(d1)}")

# Test 2: Via variable
print("\nTest 2: Via variable")
key = "$contains"
value = "John"
d2 = {key: value}
print(f"d2: {d2}")
print(f"d2 keys: {list(d2.keys())}")

# Test 3: Nested in another dict
print("\nTest 3: Nested in another dict")
filters = {"name": {"$contains": "John"}}
print(f"filters: {filters}")
print(f"filters repr: {repr(filters)}")

# Test 4: Check the actual key
print("\nTest 4: Check actual key")
inner_dict = filters["name"]
for k, v in inner_dict.items():
    print(f"Key: '{k}' (length: {len(k)}), Value: '{v}'")
    print(f"Key chars: {[ord(c) for c in k]}")

# Test 5: Raw string
print("\nTest 5: Raw string")
raw_key = r"$contains"
d5 = {raw_key: "John"}
print(f"d5: {d5}")

# Test 6: Unicode
print("\nTest 6: Check if $ is special")
print(f"Char $: ord('$') = {ord('$')}")
print(f"String '$contains': {repr('$contains')}")