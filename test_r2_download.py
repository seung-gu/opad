#!/usr/bin/env python3
"""Test R2 download to verify file exists"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.cloudflare import download_from_cloud, file_exists_in_cloud

# Check if file exists
print("Checking if file exists in R2...")
exists = file_exists_in_cloud('public/adapted_reading_material.md')
print(f"File exists: {exists}")

if exists:
    print("\nDownloading file from R2...")
    content = download_from_cloud('public/adapted_reading_material.md')
    if content:
        print(f"✅ Successfully downloaded {len(content)} bytes")
        print(f"First 200 chars: {content[:200]}")
    else:
        print("❌ Download failed")
else:
    print("❌ File does not exist in R2")

