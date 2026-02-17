#!/usr/bin/env python3
"""Simple test without problematic imports"""

import os
import sys

print("Testing basic Python functionality...")

# Test basic imports
try:
    import os
    print("✅ os import successful")
except Exception as e:
    print(f"❌ os import failed: {e}")

try:
    import sys
    print("✅ sys import successful")
except Exception as e:
    print(f"❌ sys import failed: {e}")

print("\n🎯 Basic Python test complete!")
