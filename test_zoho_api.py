#!/usr/bin/env python3
"""
Test Zoho Commerce API integration
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_zoho_commerce_api():
    """Test the Zoho Commerce API"""
    
    # Get credentials
    client_id = os.getenv('ZOHO_CLIENT_ID')
    client_secret = os.getenv('ZOHO_CLIENT_SECRET')
    access_token = os.getenv('ZOHO_ACCESS_TOKEN')
    
    print("🔑 Zoho Commerce API Test")
    print("=" * 40)
    print(f"Client ID: {'✅ Set' if client_id else '❌ Missing'}")
    print(f"Client Secret: {'✅ Set' if client_secret else '❌ Missing'}")
    print(f"Access Token: {'✅ Set' if access_token else '❌ Missing'}")
    
    if not all([client_id, client_secret, access_token]):
        print("\n❌ Missing credentials - cannot test API")
        return
    
    # Test API endpoint
    api_url = "https://commerce.zoho.com/api/v1/products"
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    print(f"\n🌐 Testing API endpoint: {api_url}")
    
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        print(f"📡 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Success!")
            print(f"📦 Found {len(data.get('products', []))} products")
            
            # Show first few products
            products = data.get('products', [])
            for i, product in enumerate(products[:5]):
                print(f"  {i+1}. {product.get('name', 'Unknown')} - ${product.get('price', 0)}")
            
            # Look for Red Bull specifically
            red_bull_products = [p for p in products if 'red bull' in p.get('name', '').lower()]
            if red_bull_products:
                print(f"\n🎯 Found {len(red_bull_products)} Red Bull products:")
                for product in red_bull_products:
                    print(f"  - {product.get('name')} - ${product.get('price')}")
                    print(f"    URL: {product.get('url', 'No URL')}")
            else:
                print("\n⚠️ No Red Bull products found")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_zoho_commerce_api()
