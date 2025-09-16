#!/usr/bin/env python3
"""
Debug script to understand Bio-Link Depot website structure
"""

import requests
from bs4 import BeautifulSoup

def debug_website_structure():
    """Debug the actual website structure"""
    
    # Test search URL
    search_url = "https://www.shopbiolinkdepot.org/search?q=pipette"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"🔍 Fetching: {search_url}")
        response = requests.get(search_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            print(f"✅ Successfully fetched page")
            print(f"📄 Page title: {soup.title.string if soup.title else 'No title'}")
            
            # Find all links
            all_links = soup.find_all('a', href=True)
            print(f"🔗 Total links found: {len(all_links)}")
            
            # Show first 10 links
            print("\n📋 First 10 links:")
            for i, link in enumerate(all_links[:10]):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f"  {i+1}. {text[:50]}... -> {href}")
            
            # Look for any links that might be products
            product_like_links = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check if it looks like a product link
                if any(keyword in href.lower() for keyword in ['product', 'item', 'p/', '/p/']):
                    product_like_links.append((text, href))
                elif any(keyword in text.lower() for keyword in ['pipette', 'tip', 'lab', 'beaker', 'flask']):
                    product_like_links.append((text, href))
            
            print(f"\n🎯 Product-like links found: {len(product_like_links)}")
            for text, href in product_like_links[:5]:
                print(f"  - {text[:50]}... -> {href}")
            
            # Check page structure
            print(f"\n🏗️ Page structure analysis:")
            
            # Look for common product container classes
            containers = soup.find_all(['div', 'section', 'article'], class_=True)
            container_classes = set()
            for container in containers:
                classes = container.get('class', [])
                container_classes.update(classes)
            
            print(f"📦 Container classes found: {list(container_classes)[:10]}")
            
            # Look for any elements with "product" in class name
            product_elements = soup.find_all(class_=lambda x: x and 'product' in ' '.join(x).lower())
            print(f"🛍️ Elements with 'product' in class: {len(product_elements)}")
            
            # Check if there's a "no results" message
            no_results = soup.find_all(text=lambda text: text and 'no results' in text.lower())
            if no_results:
                print(f"❌ 'No results' message found: {no_results[0].strip()}")
            
        else:
            print(f"❌ Failed to fetch page: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_website_structure()
