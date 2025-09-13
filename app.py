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
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Bio-Link Depot product catalog (we'll scrape this or get it via API)
BIOLINK_DEPOT_PRODUCTS = [
    {"name": "175 cm² Flask", "id": "1757018543-63ec5a68", "price": "$150.00"},
    {"name": "5L Erlenmeyer Flask w/ Vent Cap", "id": "1757018891-95c3d175", "price": "$150.00"},
    {"name": "Air Duster Spray", "id": "air-duster-spray", "price": "$16.49"},
    {"name": "Aluminum foil, Roll", "id": "aluminum-foil-roll", "price": "$37.76"},
    {"name": "Applicators, Cotton", "id": "applicators-cotton", "price": "$60.44"},
    {"name": "Assay Plates, 96-Well Microtitration, Clear", "id": "assay-plates-96-well", "price": "$256.73"},
    {"name": "Assay Tubes Invitrogen Qubit", "id": "assay-tubes-invitrogen", "price": "$121.00"},
    {"name": "Bags, Bio-hazard, 19\" x 24\"", "id": "bags-biohazard-19x24", "price": "$682.18"},
    {"name": "Bags, Bio-hazard, 25\" x 35\"", "id": "bags-biohazard-25x35", "price": "$682.18"},
    {"name": "Bags, Bio-hazard, 36\" x 45\"", "id": "bags-biohazard-36x45", "price": "$653.75"},
    {"name": "Bench Protectors, Black Mats", "id": "bench-protectors-black", "price": "$145.87"},
    {"name": "Bench Protectors, HazMat Handy Pad (PIG Mats)", "id": "bench-protectors-hazmat", "price": "$106.32"},
    {"name": "Bench Protectors, Safety Assay Mats", "id": "bench-protectors-safety", "price": "$66.45"},
    {"name": "Bench Protectors, Versi-Dry Lab Soakers", "id": "bench-protectors-versi-dry", "price": "$558.12"},
    {"name": "Benchkote", "id": "benchkote", "price": "$183.34"},
    {"name": "Bottle Top Filter, 0.2 um, PES, 150 ml", "id": "bottle-top-filter-150ml", "price": "$124.75"},
    {"name": "Bottle Top Filters, 0.2 um, PES, 1000 ml", "id": "bottle-top-filters-1000ml", "price": "$372.35"},
    {"name": "Bottle Top Filters, 0.2 um, PES, 500 ml", "id": "bottle-top-filters-500ml", "price": "$267.80"},
    {"name": "Bottles, Amber Glass, 250 ml", "id": "bottles-amber-glass-250ml", "price": "$145.42"},
    {"name": "Bottles, Amber Glass, 500 ml", "id": "bottles-amber-glass-500ml", "price": "$138.60"},
    {"name": "Bottles, Amber, HDPE, 1000 ml", "id": "bottles-amber-hdpe-1000ml", "price": "$136.30"},
    {"name": "Bottles, Amber, HDPE, 125 ml", "id": "bottles-amber-hdpe-125ml", "price": "$78.79"},
    {"name": "Bottles, Amber, HDPE, 500 ml", "id": "bottles-amber-hdpe-500ml", "price": "$153.97"},
    {"name": "Bottles, Nalgene 1000 ml PS Media Storage, sterile, 12/cs", "id": "bottles-nalgene-1000ml-ps", "price": "$142.49"},
    {"name": "Bottles, Nalgene 150 ml PS Media Storage, sterile, 24/cs", "id": "bottles-nalgene-150ml-ps", "price": "$130.89"},
    {"name": "Bottles, Nalgene 250 ml PS plastic storage, sterile, 24/cs", "id": "bottles-nalgene-250ml-ps", "price": "$143.70"},
    {"name": "Bottles, Nalgene 500 ml PS plastic storage, sterile, 12/cs", "id": "bottles-nalgene-500ml-ps", "price": "$92.14"},
    {"name": "Bottles, Nalgene, 1000 ml PETG, Media Storage, Square, sterile, 24/cs", "id": "bottles-nalgene-1000ml-petg", "price": "$344.72"},
    {"name": "Bottles, Nalgene, 125 ml PETG, Media Storage, Square, sterile, 48/cs", "id": "bottles-nalgene-125ml-petg", "price": "$287.39"},
    {"name": "Bottles, Nalgene, 2000 ml PETG, Media Storage, Square, sterile, 12/cs", "id": "bottles-nalgene-2000ml-petg", "price": "$300.41"},
    {"name": "Bottles, Nalgene, 250 ml PETG, Media Storage, Square, sterile, 48/cs", "id": "bottles-nalgene-250ml-petg", "price": "$357.75"},
    {"name": "Bottles, Nalgene, 30 ml PETG, Media Storage, Square, sterile, 48/cs", "id": "bottles-nalgene-30ml-petg", "price": "$317.74"},
    {"name": "Bottles, Nalgene, 500 ml PETG, Media Storage, Square, sterile, 24/cs", "id": "bottles-nalgene-500ml-petg", "price": "$258.30"},
    {"name": "Bottles, Nalgene, 60 ml PETG, Media Storage, Square, sterile, 48/cs", "id": "bottles-nalgene-60ml-petg", "price": "$417.38"},
    {"name": "Bottles, PP, N/M Round, 30 ml", "id": "bottles-pp-round-30ml", "price": "$67.00"},
    {"name": "Bottles, PP, W/M, Round, 1000 ml", "id": "bottles-pp-round-1000ml", "price": "$117.39"},
    {"name": "Bottles, PP, W/M, Round, 125 ml", "id": "bottles-pp-round-125ml", "price": "$65.64"},
    {"name": "Bottles, PP, W/M, Square, 1000 ml", "id": "bottles-pp-square-1000ml", "price": "$115.38"},
    {"name": "Bottles, Wash 1L", "id": "bottles-wash-1l", "price": "$42.08"},
    {"name": "Bottles, Wash, 250 ml", "id": "bottles-wash-250ml", "price": "$47.00"},
    {"name": "Bottles, Wash, 500 ml", "id": "bottles-wash-500ml", "price": "$57.63"},
    {"name": "Bottles, Wash, 750 ml", "id": "bottles-wash-750ml", "price": "$70.78"},
    {"name": "Bouffant Caps", "id": "bouffant-caps", "price": "$279.45"},
    {"name": "Boxes, Broken Glass Disposal Containers", "id": "boxes-broken-glass", "price": "$117.28"},
    {"name": "Boxes, Burn-Up Bins", "id": "boxes-burn-up", "price": "$84.54"},
    {"name": "Boxes, Fiberboard, 2 inch", "id": "boxes-fiberboard-2inch", "price": "$89.29"},
    {"name": "Boxes, Fiberboard, 3 inch", "id": "boxes-fiberboard-3inch", "price": "$98.67"},
    {"name": "Boxes, Insert, 10x 10 matrix", "id": "boxes-insert-10x10", "price": "$56.01"},
    {"name": "Boxes, Insert, 81CELL PK-12", "id": "boxes-insert-81cell", "price": "$52.52"},
    {"name": "Boxes, Insert, 8x8in F14mM VLPK 12", "id": "boxes-insert-8x8in", "price": "$50.50"}
]

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
        
        # Create product list for matching
        product_names = [product["name"] for product in BIOLINK_DEPOT_PRODUCTS]
        product_list_text = "\n".join([f"- {name}" for name in product_names])
        
        response = client.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""
                            Analyze this laboratory equipment image and identify the item. 
                            
                            Here are the available products from Bio-Link Depot:
                            {product_list_text}
                            
                            Return your response in this exact JSON format:
                            {{
                                "identified_item": "Exact product name from the list above, or 'Not Found' if no match",
                                "confidence": "High/Medium/Low",
                                "item_type": "General category (e.g., Flask, Bottle, Filter, etc.)",
                                "key_features": ["feature1", "feature2", "feature3"],
                                "notes": "Any additional observations"
                            }}
                            
                            IMPORTANT: Only return "Not Found" if the item doesn't match any of the products listed above.
                            Be very specific with product names - match them exactly to the list.
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
            logger.error(f"❌ JSON parsing error: {e}")
            return {
                "identified_item": "Not Found",
                "confidence": "Low",
                "item_type": "Unknown",
                "key_features": [],
                "notes": f"JSON parsing error: {str(e)}"
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
    Find the product URL in Bio-Link Depot
    """
    if product_name == "Not Found":
        return None
    
    # Find matching product
    for product in BIOLINK_DEPOT_PRODUCTS:
        if product["name"].lower() == product_name.lower():
            # Construct the product URL
            product_id = product["id"]
            return f"https://www.shopbiolinkdepot.org/product/{product_id}"
    
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
        logger.error(f"❌ Error in upload_image: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
