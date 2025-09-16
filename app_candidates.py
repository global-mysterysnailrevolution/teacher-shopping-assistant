"""
Teacher Shopping App - Bio-Link Depot Integration with Candidate Selection
Allows teachers to take pictures of lab items and select from candidate products
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

def get_zoho_commerce_products(search_terms=None):
    """
    Get products from Zoho Commerce Storefront API (UNAUTHENTICATED)
    """
    try:
        import requests
        
        # Storefront API is UNAUTHENTICATED - only needs domain-name header
        store_domain = "www.shopbiolinkdepot.org"  # Your store's domain
        
        logger.info(f"🌐 Using Zoho Commerce Storefront API for domain: {store_domain}")

        # Build dynamic search URLs based on identified item
        api_urls = ["https://commerce.zoho.com/storefront/api/v1/products"]
        
        if search_terms:
            # Break down the identified item into individual search terms
            for term in search_terms:
                if len(term) > 2:  # Only search terms longer than 2 characters
                    api_urls.append(f"https://commerce.zoho.com/storefront/api/v1/search-products?q={term}")
                    logger.info(f"🔍 Added search term: {term}")
        
        # Always try 'all' as fallback
        api_urls.append("https://commerce.zoho.com/storefront/api/v1/search-products?q=all")

        headers = {
            'domain-name': store_domain,
            'Content-Type': 'application/json'
        }
        
        # Try each API endpoint
        for api_url in api_urls:
            logger.info(f"🌐 Trying Storefront API: {api_url}")
            try:
                response = requests.get(api_url, headers=headers, timeout=30)

                logger.info(f"📡 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"📦 Raw API response: {str(data)[:500]}...")
                    
                    # Check the actual structure of the response
                    logger.info(f"📦 Response keys: {list(data.keys())}")
                    if 'payload' in data:
                        logger.info(f"📦 Payload keys: {list(data['payload'].keys())}")
                        if 'products' in data['payload']:
                            logger.info(f"📦 Products in payload: {len(data['payload']['products'])}")
                    
                    products = []
                    # Try different ways to get products from the response
                    product_list = data.get('products', data.get('data', []))
                    if 'payload' in data and 'products' in data['payload']:
                        product_list = data['payload']['products']
                    
                    for product in product_list:
                        # Get the correct product URL
                        product_url = product.get('url', '')
                        if not product_url:
                            # Try different URL fields
                            product_url = product.get('handle', '')
                        if not product_url:
                            # Construct URL from product ID
                            product_id = product.get('product_id', product.get('id', ''))
                            product_url = f"https://www.shopbiolinkdepot.org/products/{product_id}"
                        
                        # Fix relative URLs - make them absolute
                        if product_url.startswith('/'):
                            product_url = f"https://www.shopbiolinkdepot.org{product_url}"
                        
                        logger.info(f"📦 Product: {product.get('name', '')} -> URL: {product_url}")
                        
                        products.append({
                            "name": product.get('name', ''),
                            "id": product.get('product_id', product.get('id', '')),
                            "price": f"${product.get('selling_price', product.get('price', 0))}",
                            "description": product.get('description', product.get('short_description', '')),
                            "status": "active",
                            "url": product_url
                        })

                    logger.info(f"✅ Retrieved {len(products)} products from Zoho Commerce Storefront")
                    return products
                    
                else:
                    logger.error(f"❌ Storefront API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"❌ Error with {api_url}: {e}")
                continue
        
        logger.error("❌ All Storefront API endpoints failed")
        return []

    except Exception as e:
        logger.error(f"❌ Error getting Zoho Commerce products: {e}")
        return []

def get_biolink_products(search_terms=None):
    """
    Get Bio-Link Depot products from Zoho Commerce API ONLY
    """
    # Only use Zoho Commerce API - no web scraping bullshit
    zoho_products = get_zoho_commerce_products(search_terms)
    if zoho_products:
        logger.info("✅ Using Zoho Commerce API products")
        return zoho_products

    # If API fails, return empty list
    logger.warning("⚠️ Zoho Commerce API failed - no products available")
    return []

def find_product_candidates(product_name):
    """
    Find candidate products in Bio-Link Depot and return them for teacher selection
    """
    if product_name == "Not Found":
        return []
    
    try:
        logger.info(f"🔍 Starting candidate search for: '{product_name}'")
        
        # Extract search terms from the identified product name
        search_terms = []
        if product_name:
            # Break down the product name into individual words
            words = product_name.lower().split()
            # Remove common words and keep meaningful terms
            stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'ml', 'fl', 'oz']
            search_terms = [word for word in words if word not in stop_words and len(word) > 2]
            logger.info(f"🔍 Extracted search terms: {search_terms}")
        
        # Get products from Zoho Commerce API with dynamic search terms
        zoho_products = get_biolink_products(search_terms)
        if zoho_products:
            logger.info(f"✅ Found {len(zoho_products)} candidate products")
            # Return top 10 candidates for teacher selection
            return zoho_products[:10]
        
        logger.warning(f"⚠️ No candidate products found")
        return []
        
    except Exception as e:
        logger.error(f"❌ Error in candidate search: {e}")
        return []

def get_openai_client():
    """
    Get OpenAI client with error handling
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY not found in environment variables")
        return None
    
    try:
        # Use the older openai module approach for better compatibility
        import openai
        openai.api_key = api_key
        return openai
    except ImportError:
        logger.error("❌ OpenAI module not available")
        return None

def identify_lab_item(image_data):
    """
    Use OpenAI GPT-4o to identify the lab item in the image
    """
    try:
        logger.info("🔍 Starting GPT-4o analysis...")
        
        # Get OpenAI client
        client = get_openai_client()
        if not client:
            return {
                "identified_item": "Not Found",
                "confidence": "Low",
                "item_type": "Unknown",
                "key_features": [],
                "notes": "OpenAI API key not available"
            }

        logger.info("📤 Sending image to GPT-4o...")
        
        response = client.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """
                            Look at this image and identify the item. Return your response in this exact JSON format:
                            {
                                "identified_item": "Exact product name (e.g., Red Bull Sugarfree Energy Drink)",
                                "confidence": "High/Medium/Low",
                                "item_type": "General category (e.g., Beverage, Flask, Bottle, Filter, etc.)",
                                "key_features": ["feature1", "feature2", "feature3"],
                                "notes": "Any additional observations"
                            }

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
            temperature=0.1,
            timeout=60  # Add timeout to prevent hanging
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
            logger.error(f"❌ Failed to parse GPT response as JSON: {e}")
            return {
                "identified_item": "Not Found",
                "confidence": "Low",
                "item_type": "Unknown",
                "key_features": [],
                "notes": "Could not parse AI response"
            }

    except Exception as e:
        logger.error(f"❌ Error in GPT-4o analysis: {e}")
        return {
            "identified_item": "Not Found",
            "confidence": "Low",
            "item_type": "Unknown",
            "key_features": [],
            "notes": f"Error during analysis: {str(e)}"
        }

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

        # Check if OpenAI API key is available
        if not os.getenv('OPENAI_API_KEY'):
            return jsonify({
                'identification': {
                    'identified_item': 'Not Found',
                    'confidence': 'Low',
                    'item_type': 'Unknown',
                    'key_features': [],
                    'notes': 'OpenAI API key not configured'
                },
                'candidate_products': [],
                'image_data': f"data:image/jpeg;base64,{base64_image}"
            })

        # Identify the lab item using GPT-4o
        identification = identify_lab_item(base64_image)
        
        # Find candidate products for teacher selection
        candidate_products = find_product_candidates(identification['identified_item'])
        
        return jsonify({
            'identification': identification,
            'candidate_products': candidate_products,
            'image_data': f"data:image/jpeg;base64,{base64_image}"
        })

    except Exception as e:
        logger.error(f"❌ Error in upload_image: {e}")
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/select_product', methods=['POST'])
def select_product():
    """Handle product selection by teacher"""
    try:
        data = request.get_json()
        product_url = data.get('product_url')
        
        if not product_url:
            return jsonify({'error': 'No product URL provided'}), 400
        
        logger.info(f"✅ Teacher selected product: {product_url}")
        
        return jsonify({
            'success': True,
            'product_url': product_url,
            'message': 'Product selected successfully'
        })
        
    except Exception as e:
        logger.error(f"❌ Error in select_product: {e}")
        return jsonify({'error': 'Failed to select product'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
