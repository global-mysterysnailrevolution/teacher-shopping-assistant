"""
Teacher Shopping App - Bio-Link Depot Integration
Allows teachers to take pictures of lab items and find them on the Bio-Link Depot store
"""

import os
import base64
import requests
import json
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for
# OpenAI will be imported dynamically in get_openai_client()
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def get_zoho_commerce_products():
    """
    Get products from Zoho Commerce API
    """
    try:
        import requests
        
        # Zoho Commerce API credentials (you'll need to set these)
        client_id = os.getenv('ZOHO_CLIENT_ID')
        client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        access_token = os.getenv('ZOHO_ACCESS_TOKEN')

        if not all([client_id, client_secret, access_token]):
            logger.warning("⚠️ Zoho Commerce credentials not configured")
            return []

        # Zoho Commerce API endpoint
        api_url = "https://commerce.zoho.com/api/v1/products"

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            products = []

            for product in data.get('products', []):
                products.append({
                    "name": product.get('name', ''),
                    "id": product.get('id', ''),
                    "price": f"${product.get('price', 0)}",
                    "description": product.get('description', ''),
                    "status": product.get('status', '')
                })

            logger.info(f"🔍 Retrieved {len(products)} products from Zoho Commerce")
            return products

        else:
            logger.error(f"❌ Zoho Commerce API error: {response.status_code} - {response.text}")
            return []

    except Exception as e:
        logger.error(f"❌ Error getting Zoho Commerce products: {e}")
        return []

def scrape_biolink_products():
    """
    Scrape products from Bio-Link Depot website
    """
    try:
        from bs4 import BeautifulSoup
        
        # Scrape the main products page
        url = "https://www.shopbiolinkdepot.org/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = []

            # Debug: Log the HTML structure to understand the site
            logger.info("🔍 Analyzing Bio-Link Depot HTML structure...")

            # Try multiple approaches to find products
            # Look for any elements that might contain product names
            potential_selectors = [
                'div.product',
                'div.item',
                'article.product',
                'div[class*="product"]',
                'div[class*="item"]',
                'h1', 'h2', 'h3', 'h4',
                'span[class*="name"]',
                'span[class*="title"]',
                'div[class*="name"]',
                'div[class*="title"]'
            ]

            for selector in potential_selectors:
                elements = soup.select(selector)
                logger.info(f"🔍 Selector '{selector}' found {len(elements)} elements")

                for element in elements:
                    text = element.get_text(strip=True)
                    if text and len(text) > 3 and len(text) < 200:  # Reasonable product name length  
                        # Check if it looks like a product name
                        if any(keyword in text.lower() for keyword in ['flask', 'bottle', 'tube', 'plate', 'filter', 'red bull', 'redbull']):                                                               
                            logger.info(f"🎯 Found potential product: {text}")

                            # Try to find price nearby
                            price = "Price not found"
                            parent = element.parent
                            if parent:
                                price_elem = parent.find(['span', 'div'], string=lambda x: x and '$' in str(x))                                                                                             
                                if price_elem:
                                    price = price_elem.get_text(strip=True)

                            # Generate ID
                            product_id = text.lower().replace(' ', '-').replace(',', '').replace('"', '').replace('²', '2')

                            products.append({
                                "name": text,
                                "id": product_id,
                                "price": price
                            })

            # Remove duplicates
            seen = set()
            unique_products = []
            for product in products:
                if product['name'] not in seen:
                    seen.add(product['name'])
                    unique_products.append(product)

            logger.info(f"🔍 Scraped {len(unique_products)} unique products from Bio-Link Depot")   
            for product in unique_products[:5]:  # Log first 5 for debugging
                logger.info(f"  - {product['name']} ({product['price']})")

            return unique_products

    except Exception as e:
        logger.error(f"❌ Error scraping Bio-Link Depot: {e}")
        return []

# No static list - everything is dynamic!

def get_biolink_products():
    """
    Get Bio-Link Depot products (Zoho Commerce API -> Web scraping)
    """
    # Priority 1: Try Zoho Commerce API
    zoho_products = get_zoho_commerce_products()
    if zoho_products:
        logger.info("✅ Using Zoho Commerce API products")
        return zoho_products

    # Priority 2: Try web scraping
    scraped_products = scrape_biolink_products()
    if scraped_products:
        logger.info("✅ Using scraped products")
        return scraped_products

    # No fallback - return empty list
    logger.warning("⚠️ No products found from any source")
    return []

def get_openai_client():
    """Get the OpenAI client instance"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Use the older openai module approach for better compatibility
    import openai
    openai.api_key = api_key
    return openai

def identify_lab_item(image_data):
    """
    Use OpenAI GPT-4o to identify the lab item in the image
    """
    try:
        logger.info("🔍 Starting GPT-4o analysis...")

        # Get OpenAI client
        client = get_openai_client()

        # Create the vision message with structured prompt
        logger.info("📤 Sending image to GPT-4o...")

        response = client.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            Analyze this image and identify the item.

                            Return your response in this exact JSON format:
                            {{
                                "identified_item": "Specific product name (e.g., 'Red Bull Energy Drink', 'Erlenmeyer Flask 250ml', 'Beaker 500ml'), or 'Not Found' if unclear",
                                "confidence": "High/Medium/Low",
                                "item_type": "General category (e.g., Beverage, Flask, Bottle, Filter, etc.)",
                                "key_features": ["feature1", "feature2", "feature3"],
                                "notes": "Any additional observations"
                            }}

                            Be specific and descriptive with the product name. Identify ANY item that could be sold in a store.
                            """
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500,
            temperature=0.1
        )

        logger.info("📥 Received response from GPT-4o")
        response_content = response.choices[0].message.content
        logger.info(f"Raw GPT response: {response_content}")

        # Parse the response to extract structured data
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                logger.info("✅ Successfully parsed JSON from GPT response")
                return result
            else:
                logger.warning("⚠️ No JSON found in GPT response")
                return {
                    "identified_item": "Not Found",
                    "confidence": "Low",
                    "item_type": "Unknown",
                    "key_features": [],
                    "notes": "Could not parse AI response"
                }
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
            return {
                "identified_item": "Not Found",
                "confidence": "Low",
                "item_type": "Unknown",
                "key_features": [],
                "notes": f"Error: {str(e)}"
            }

    except Exception as e:
        logger.error(f"❌ Error in identify_lab_item: {e}")
        return {
            "identified_item": "Not Found",
            "confidence": "Low",
            "item_type": "Unknown",
            "key_features": [],
            "notes": f"Error: {str(e)}"
        }

def find_product_url(product_name):
    """
    Find the product URL in Bio-Link Depot using multiple search strategies
    """
    if product_name == "Not Found":
        return None
    
    try:
        # Extract key terms from the product name
        terms = product_name.lower().split()
        
        # Remove common words that might not be in product names
        stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        key_terms = [term for term in terms if term not in stop_words and len(term) > 2]
        
        # Create multiple search strategies
        search_strategies = []
        
        # Strategy 1: Full product name
        search_strategies.append(product_name.replace(' ', '+'))
        
        # Strategy 2: Key terms only
        if key_terms:
            search_strategies.append('+'.join(key_terms))
        
        # Strategy 3: Individual key terms (most important first)
        for term in key_terms[:3]:  # Limit to first 3 terms
            search_strategies.append(term)
        
        # Strategy 4: Brand name + main product (if we can identify them)
        if len(key_terms) >= 2:
            # Assume first term is brand, rest is product
            brand = key_terms[0]
            product = '+'.join(key_terms[1:])
            search_strategies.append(f"{brand}+{product}")
        
        # Remove duplicates while preserving order
        unique_strategies = []
        seen = set()
        for strategy in search_strategies:
            if strategy not in seen:
                unique_strategies.append(strategy)
                seen.add(strategy)
        
        # For now, return the first (most specific) search URL
        # In the future, we could try multiple searches and return the best match
        best_search = unique_strategies[0]
        search_url = f"https://www.shopbiolinkdepot.org/search?q={best_search}"
        
        logger.info(f"🔍 Searching for '{product_name}' using strategy: '{best_search}'")
        logger.info(f"🔍 Available strategies: {unique_strategies}")
        
        return search_url
        
    except Exception as e:
        logger.error(f"❌ Error finding product URL: {e}")
        return None

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """Handle image upload and identification"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400

        # Read and encode the image
        image_data = file.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')

        # Identify the lab item
        identification_result = identify_lab_item(base64_image)

        # Find product URL if item was identified
        product_url = None
        if identification_result["identified_item"] != "Not Found":
            product_url = find_product_url(identification_result["identified_item"])

        # Return results
        result = {
            "success": True,
            "identification": identification_result,
            "product_url": product_url,
            "image_data": f"data:image/jpeg;base64,{base64_image}"
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': 'Failed to process image'}), 500

if __name__ == '__main__':
    app.run(debug=True)
