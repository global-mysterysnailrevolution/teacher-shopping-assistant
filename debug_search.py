#!/usr/bin/env python3
"""
Debug script to see what Bio-Link Depot search results actually look like
"""

import requests
from bs4 import BeautifulSoup

def debug_search_results():
    """Debug what the search results actually contain"""
    
    search_url = "https://www.shopbiolinkdepot.org/search?q=red"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    print(f"🔍 Debugging search URL: {search_url}")
    
    try:
        response = requests.get(search_url, headers=headers, timeout=10)
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find ALL links
            all_links = soup.find_all('a', href=True)
            print(f"🔗 Found {len(all_links)} total links")
            
            # Show first 20 links
            for i, link in enumerate(all_links[:20]):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f"  {i+1}. '{text}' -> '{href}'")
            
            # Look specifically for product links
            product_links = soup.find_all('a', href=lambda x: x and '/products/' in x)
            print(f"\n📦 Found {len(product_links)} links with /products/")
            
            for i, link in enumerate(product_links):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                print(f"  {i+1}. '{text}' -> '{href}'")
            
            # Look for any links that might be products (different patterns)
            patterns = ['/product/', '/item/', '/p/', 'product']
            for pattern in patterns:
                pattern_links = soup.find_all('a', href=lambda x: x and pattern in x)
                print(f"\n🔍 Found {len(pattern_links)} links with '{pattern}'")
                for i, link in enumerate(pattern_links[:5]):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    print(f"  {i+1}. '{text}' -> '{href}'")
            
            # Save HTML for manual inspection
            with open('search_results.html', 'w', encoding='utf-8') as f:
                f.write(str(soup.prettify()))
            print(f"\n💾 Saved HTML to search_results.html for manual inspection")
            
        else:
            print(f"❌ Search failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_search_results()
