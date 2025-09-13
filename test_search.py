#!/usr/bin/env python3
"""
Test script for the search logic in the teacher shopping app
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import find_product_url, scrape_biolink_products

def test_search_logic():
    """Test the search logic with various product names"""
    
    test_products = [
        "Red Bull Energy Drink",
        "Erlenmeyer Flask 250ml", 
        "Beaker 500ml",
        "Test Tube Rack",
        "Petri Dish",
        "Microscope Slide",
        "Pipette",
        "Graduated Cylinder"
    ]
    
    print("🧪 Testing Search Logic")
    print("=" * 50)
    
    for product in test_products:
        print(f"\n🔍 Testing: '{product}'")
        url = find_product_url(product)
        if url:
            print(f"✅ Found URL: {url}")
        else:
            print("❌ No URL found")
    
    print("\n" + "=" * 50)
    print("🌐 Testing Bio-Link Depot Scraping")
    
    products = scrape_biolink_products()
    print(f"📦 Found {len(products)} products")
    
    for i, product in enumerate(products[:5]):  # Show first 5
        print(f"  {i+1}. {product['name']} - {product['price']}")

if __name__ == "__main__":
    test_search_logic()
