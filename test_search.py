#!/usr/bin/env python3
"""
Test script for the new intelligent search logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import break_down_product_name, search_biolink_depot, analyze_products_with_ai

def test_search_logic():
    """Test the new search logic with various product names"""
    
    test_products = [
        "Red Bull Sugarfree Energy Drink",
        "Erlenmeyer Flask 250ml", 
        "Beaker 500ml",
        "Test Tube Rack",
        "Petri Dish",
        "Microscope Slide",
        "Pipette",
        "Graduated Cylinder"
    ]
    
    print("🧪 Testing New Intelligent Search Logic")
    print("=" * 60)
    
    for product in test_products:
        print(f"\n🔍 Testing: '{product}'")
        
        # Test 1: Break down product name
        search_terms = break_down_product_name(product)
        print(f"   📝 Search terms: {search_terms}")
        
        # Test 2: Search Bio-Link Depot (without AI analysis)
        if search_terms:
            first_term = search_terms[0]
            print(f"   🌐 Searching Bio-Link Depot for: '{first_term}'")
            
            try:
                product_links = search_biolink_depot(first_term)
                print(f"   📦 Found {len(product_links)} product links")
                
                if product_links:
                    print(f"   🔗 First few links:")
                    for i, link in enumerate(product_links[:3]):
                        print(f"      {i+1}. {link['text'][:50]}... -> {link['url']}")
                else:
                    print(f"   ⚠️ No products found for '{first_term}'")
                    
            except Exception as e:
                print(f"   ❌ Error searching: {e}")
        else:
            print(f"   ⚠️ No search terms extracted")
    
    print("\n" + "=" * 60)
    print("✅ Search logic test completed!")
    print("\nNote: AI analysis requires OPENAI_API_KEY environment variable")

if __name__ == "__main__":
    test_search_logic()
