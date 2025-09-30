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
from dotenv import load_dotenv
import logging
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def get_openai_client():
    """Get the OpenAI client instance"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("❌ OPENAI_API_KEY environment variable not set")
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
                                "identified_item": "Specific product name (e.g., 'Red Bull Sugarfree Energy Drink', 'Erlenmeyer Flask 250ml', 'Beaker 500ml'), or 'Not Found' if unclear",
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
            temperature=0.1,
            timeout=60
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

def break_down_product_name(product_name):
    """
    Break down product name into individual search terms
    """
    if not product_name or product_name == "Not Found":
        return []
    
    # Split into words and clean them
    words = product_name.lower().split()
    
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'ml', 'fl', 'oz', 'energy', 'drink'}
    
    # Keep meaningful terms
    search_terms = [word for word in words if word not in stop_words and len(word) > 2]
    
    logger.info(f"🔍 Broke down '{product_name}' into search terms: {search_terms}")
    return search_terms

def search_biolink_depot(search_term):
    """
    Search Bio-Link Depot using Zoho Commerce API since the site uses dynamic content
    """
    try:
        logger.info(f"🔍 Searching Bio-Link Depot API for: '{search_term}'")
        
        # Use Zoho Commerce Storefront API
        api_url = f"https://commerce.zoho.com/storefront/api/v1/search-products"
        
        headers = {
            'domain-name': 'www.shopbiolinkdepot.org',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        params = {
            'q': search_term,
            'limit': 20
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"📡 API response keys: {list(data.keys())}")
            
            # Extract products from the response
            products = []
            
            # Try different ways to get products from the response
            product_list = data.get('products', data.get('data', []))
            if 'payload' in data and 'products' in data['payload']:
                product_list = data['payload']['products']
            
            logger.info(f"📦 Found {len(product_list)} products in API response")
            
            for product in product_list:
                # Get product URL
                product_url = product.get('url', '')
                if not product_url:
                    # Try different URL fields
                    product_url = product.get('handle', '')
                if not product_url:
                    # Construct URL from product ID
                    product_id = product.get('product_id', product.get('id', ''))
                    product_url = f"https://www.shopbiolinkdepot.org/products/{product_id}"
                
                # Fix relative URLs
                if product_url.startswith('/'):
                    product_url = f"https://www.shopbiolinkdepot.org{product_url}"
                
                product_name = product.get('name', '')
                
                if product_name and product_url:
                    products.append({
                        'url': product_url,
                        'text': product_name,
                        'title': product_name,
                        'price': product.get('selling_price', product.get('price', '')),
                        'description': product.get('description', product.get('short_description', ''))
                    })
            
            logger.info(f"✅ Found {len(products)} products for '{search_term}'")
            return products
            
        else:
            logger.error(f"❌ API search failed with status {response.status_code}: {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"❌ Error searching Bio-Link Depot API: {e}")
        return []

def analyze_products_with_ai(target_product, product_links):
    """
    Use AI to analyze product links and find the best match
    """
    try:
        logger.info(f"🤖 AI analyzing {len(product_links)} products for match with '{target_product}'")
        
        if not product_links:
            return None
        
        # Prepare product list for AI
        products_text = "\n".join([f"{i+1}. {product['text']} - {product['url']}" for i, product in enumerate(product_links)])
        
        # Get OpenAI client
        client = get_openai_client()
        
        # Create prompt for AI analysis
        prompt = f"""
        I'm looking for this product: "{target_product}"
        
        Here are the products I found in the store:
        {products_text}
        
        Please analyze these products and tell me which one (if any) matches the product I'm looking for.
        
        Return your response in this exact JSON format:
        {{
            "match_found": true/false,
            "best_match_number": 1-{len(product_links)} (the number from the list above, or null if no match),
            "confidence": "High/Medium/Low",
            "reasoning": "Why this is or isn't a match",
            "fallback_match_number": 1-{len(product_links)} (the number of the most similar product if no exact match, or null)
        }}
        
        Consider:
        - Brand names (Red Bull, Coca-Cola, etc.)
        - Product types (Energy Drink, Flask, Beaker, etc.)
        - Variations (Sugarfree, Sugar-Free, etc.)
        - If no exact match, suggest the most similar product as a fallback
        """
        
        response = client.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1
        )
        
        response_content = response.choices[0].message.content
        logger.info(f"🤖 AI response: {response_content}")
        
        # Parse AI response
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            # Check for exact match first
            if result.get('match_found') and result.get('best_match_number'):
                match_index = result['best_match_number'] - 1
                if 0 <= match_index < len(product_links):
                    best_product = product_links[match_index]
                    logger.info(f"✅ AI found exact match: {best_product['text']} (confidence: {result.get('confidence', 'Unknown')})")
                    return best_product
            
            # If no exact match, try fallback match
            elif result.get('fallback_match_number'):
                fallback_index = result['fallback_match_number'] - 1
                if 0 <= fallback_index < len(product_links):
                    fallback_product = product_links[fallback_index]
                    logger.info(f"🔄 AI found fallback match: {fallback_product['text']} (reasoning: {result.get('reasoning', 'Unknown')})")
                    return fallback_product
        
        logger.info("⚠️ AI found no suitable match")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error in AI analysis: {e}")
        return None

def find_product_url(product_name):
    """
    Find the actual product URL in Bio-Link Depot using intelligent search
    """
    if product_name == "Not Found":
        return None
    
    try:
        logger.info(f"🔍 Starting intelligent search for: '{product_name}'")
        
        # Step 1: Break down the product name into search terms
        search_terms = break_down_product_name(product_name)
        
        if not search_terms:
            logger.warning("⚠️ No search terms extracted")
            return None
        
        # Store all found products for fallback analysis
        all_found_products = []
        
        # Step 2: Try each search term
        for term in search_terms:
            logger.info(f"🔍 Trying search: '{term}'")
            
            # Search Bio-Link Depot
            product_links = search_biolink_depot(term)
            
            if product_links:
                # Add to our collection of all products
                all_found_products.extend(product_links)
                
                # Use AI to find the best match
                best_match = analyze_products_with_ai(product_name, product_links)
                
                if best_match:
                    logger.info(f"✅ Found match for '{term}': {best_match['text']}")
                    return best_match['url']
                else:
                    logger.info(f"⚠️ No AI match found for '{term}', trying next term...")
            else:
                logger.info(f"⚠️ No products found for '{term}', trying next term...")
        
        # Step 3: If no individual terms worked, try the full name
        logger.info(f"🔍 Trying full name search: '{product_name}'")
        product_links = search_biolink_depot(product_name)
        
        if product_links:
            all_found_products.extend(product_links)
            best_match = analyze_products_with_ai(product_name, product_links)
            if best_match:
                logger.info(f"✅ Found match with full name: {best_match['text']}")
                return best_match['url']
        
        # Step 4: If still no match, try analyzing all found products together
        if all_found_products:
            logger.info(f"🔄 No exact match found, analyzing {len(all_found_products)} total products for best fallback...")
            best_match = analyze_products_with_ai(product_name, all_found_products)
            if best_match:
                logger.info(f"🔄 Found fallback match: {best_match['text']}")
                return best_match['url']
        
        logger.warning(f"⚠️ No product found for '{product_name}'")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error in intelligent search: {e}")
        return None

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/check-login', methods=['GET'])
def check_login():
    """Check if user is logged into Zoho Commerce store"""
    try:
        # Get the session cookie from the request
        session_cookie = request.cookies.get('zoho_session', '')
        
        if not session_cookie:
            return jsonify({
                'logged_in': False,
                'message': 'No session found'
            })
        
        # Check with Zoho Commerce API to verify the session
        api_url = "https://commerce.zoho.com/storefront/api/v1/customer/profile"
        
        headers = {
            'domain-name': 'www.shopbiolinkdepot.org',
            'Content-Type': 'application/json',
            'Cookie': f'zoho_session={session_cookie}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # If we get customer data, they're logged in
            if data.get('customer') or data.get('profile'):
                logger.info("✅ User is logged into Zoho Commerce")
                return jsonify({
                    'logged_in': True,
                    'message': 'User is logged in',
                    'customer_data': data.get('customer', data.get('profile', {}))
                })
        
        logger.info("❌ User is not logged into Zoho Commerce")
        return jsonify({
            'logged_in': False,
            'message': 'Session invalid or expired'
        })
        
    except Exception as e:
        logger.error(f"❌ Error checking login status: {e}")
        return jsonify({
            'logged_in': False,
            'message': f'Error checking login: {str(e)}'
        })

@app.route('/upload', methods=['POST'])
def upload_image():
    """Handle image upload and identification"""
    try:
        # First check if user is logged in
        session_cookie = request.cookies.get('zoho_session', '')
        if not session_cookie:
            return jsonify({
                'error': 'Please log in to the store first',
                'login_required': True,
                'store_url': 'https://www.shopbiolinkdepot.org/signin'
            }), 401
        
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
            logger.error("❌ OPENAI_API_KEY not set, returning error")
            return jsonify({'error': 'AI service not configured'}), 500

        # Identify the lab item
        identification_result = identify_lab_item(base64_image)

        # Find product URL if item was identified
        product_url = None
        item_in_inventory = False
        
        if identification_result["identified_item"] != "Not Found":
            product_url = find_product_url(identification_result["identified_item"])
            
            # Check if we found a product in inventory
            if product_url:
                item_in_inventory = True
                logger.info(f"✅ Item found in inventory: {product_url}")
            else:
                logger.info(f"⚠️ Item '{identification_result['identified_item']}' not found in inventory")

        # Return results
        result = {
            "success": True,
            "identification": identification_result,
            "product_url": product_url,
            "item_in_inventory": item_in_inventory,
            "image_data": f"data:image/jpeg;base64,{base64_image}"
        }

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': 'Failed to process image'}), 500

if __name__ == '__main__':
    app.run(debug=True)