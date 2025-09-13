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
        
        # Zoho Commerce API credentials
        client_id = os.getenv('ZOHO_CLIENT_ID')
        client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        access_token = os.getenv('ZOHO_ACCESS_TOKEN')
        
        # Clean up the credentials (remove newlines, extra spaces, etc.)
        if access_token:
            access_token = access_token.strip()
            logger.info(f"🔑 Access token length: {len(access_token)}")
            logger.info(f"🔑 Access token starts with: {repr(access_token[:10])}")
        
        if client_secret:
            client_secret = client_secret.strip()
            logger.info(f"🔑 Client secret length: {len(client_secret)}")
            logger.info(f"🔑 Client secret starts with: {repr(client_secret[:10])}")

        logger.info(f"🔑 Checking Zoho credentials: Client ID={'✅' if client_id else '❌'}, Secret={'✅' if client_secret else '❌'}, Token={'✅' if access_token else '❌'}")

        if not all([client_id, client_secret, access_token]):
            logger.warning("⚠️ Zoho Commerce credentials not configured")
            return []

        # Try different Zoho Commerce API endpoints
        api_endpoints = [
            "https://commerce.zoho.com/api/v1/products",
            "https://commerce.zoho.com/api/v1/store/products", 
            f"https://commerce.zoho.com/api/v1/store/{client_id}/products"
        ]

        headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json',
            'X-ZOHO-CLIENT-ID': client_id,
            'X-ZOHO-CLIENT-SECRET': client_secret
        }
        
        logger.info(f"🔑 Authorization header: Bearer {access_token[:20]}...")
        
        for api_url in api_endpoints:
            logger.info(f"🌐 Trying Zoho API endpoint: {api_url}")
            
            try:
                response = requests.get(api_url, headers=headers, timeout=30)
                logger.info(f"📡 Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"📦 Raw API response: {str(data)[:500]}...")
                    
                    products = []
                    product_list = data.get('products', data.get('data', []))
                    
                    for product in product_list:
                        products.append({
                            "name": product.get('name', ''),
                            "id": product.get('id', ''),
                            "price": f"${product.get('price', 0)}",
                            "description": product.get('description', ''),
                            "status": product.get('status', ''),
                            "url": product.get('url', f"https://www.shopbiolinkdepot.org/products/{product.get('id', '')}")
                        })

                    logger.info(f"✅ Retrieved {len(products)} products from Zoho Commerce")
                    return products
                    
                else:
                    logger.error(f"❌ Zoho Commerce API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"❌ Error with endpoint {api_url}: {e}")
                continue

        logger.error("❌ All Zoho Commerce API endpoints failed")
        return []

    except Exception as e:
        logger.error(f"❌ Error getting Zoho Commerce products: {e}")
        return []

def get_biolink_products():
    """
    Get Bio-Link Depot products from Zoho Commerce API ONLY
    """
    # Only use Zoho Commerce API - no web scraping bullshit
    zoho_products = get_zoho_commerce_products()
    if zoho_products:
        logger.info("✅ Using Zoho Commerce API products")
        return zoho_products

    # If API fails, return empty list
    logger.warning("⚠️ Zoho Commerce API failed - no products available")
    return []

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
    Find the actual product URL in Bio-Link Depot using intelligent search
    """
    if product_name == "Not Found":
        return None
    
    try:
        logger.info(f"🔍 Starting intelligent search for: '{product_name}'")
        
        # Step 1: Try Zoho Commerce API first (if credentials are available)
        zoho_products = get_zoho_commerce_products()
        if zoho_products:
            logger.info("✅ Using Zoho Commerce API for product search")
            best_match = analyze_products_with_ai(product_name, zoho_products)
            if best_match:
                logger.info(f"✅ Found match in Zoho API: {best_match['name']}")
                return best_match['url']
        
        
        # Step 2: If no match found in API, return None
        logger.warning(f"⚠️ No product match found in Zoho Commerce API, returning None")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error in intelligent search: {e}")
        return None



def analyze_products_with_ai(target_product, product_list):
    """
    Use AI to analyze product list and find the best match
    """
    try:
        logger.info(f"🤖 AI analyzing {len(product_list)} products for match with '{target_product}'")
        
        # Prepare product list for AI
        products_text = "\n".join([f"{i+1}. {product['name']}" for i, product in enumerate(product_list)])
        
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
            "best_match_number": 1-{len(product_list)} (the number from the list above),
            "confidence": "High/Medium/Low",
            "reasoning": "Why this is or isn't a match"
        }}
        
        Consider:
        - Brand names (Red Bull, Coca-Cola, etc.)
        - Product types (Energy Drink, Flask, Beaker, etc.)
        - Variations (Sugarfree, Sugar-Free, etc.)
        - Similar products if exact match not found
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
        import re
        json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            
            if result.get('match_found') and result.get('best_match_number'):
                match_index = result['best_match_number'] - 1
                if 0 <= match_index < len(product_list):
                    best_product = product_list[match_index]
                    logger.info(f"✅ AI found match: {best_product['name']} (confidence: {result.get('confidence', 'Unknown')})")
                    return best_product
        
        logger.info("⚠️ AI found no suitable match")
        return None
        
    except Exception as e:
        logger.error(f"❌ Error in AI analysis: {e}")
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

        # Check if OpenAI API key is available
        if not os.getenv('OPENAI_API_KEY'):
            logger.error("❌ OPENAI_API_KEY not set, returning error")
            return jsonify({'error': 'AI service not configured'}), 500

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
