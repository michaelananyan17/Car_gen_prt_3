from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import time
import os

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'file://'])

# Rate limiting storage
request_counts = {}
RATE_LIMIT = 10  # 10 requests per hour per API key
HOUR_SECONDS = 60 * 60

def rate_limit_check(api_key):
    now = time.time()
    key_data = request_counts.get(api_key, {'count': 0, 'reset_time': now + HOUR_SECONDS})
    
    # Reset counter if hour has passed
    if now > key_data['reset_time']:
        key_data['count'] = 0
        key_data['reset_time'] = now + HOUR_SECONDS
    
    # Check rate limit
    if key_data['count'] >= RATE_LIMIT:
        return False
    
    key_data['count'] += 1
    request_counts[api_key] = key_data
    return True

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Car Photo Generator Server is running"})

@app.route('/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        api_key = data.get('apiKey')

        # Validate input
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        
        if not api_key:
            return jsonify({"error": "API key is required"}), 400
        
        if not api_key.startswith('sk-') or len(api_key) < 20:
            return jsonify({"error": "Invalid OpenAI API key format"}), 400

        # Validate prompt length
        if len(prompt) > 1000:
            return jsonify({"error": "Prompt too long. Maximum 1000 characters."}), 400

        # Rate limiting check
        if not rate_limit_check(api_key):
            return jsonify({"error": "Rate limit exceeded. Maximum 10 requests per hour per API key."}), 429

        print(f"Generating image with prompt: {prompt[:100]}...")

        # Initialize OpenAI client with the provided API key
        client = OpenAI(api_key=api_key)

        # Call OpenAI DALL-E API
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )

        image_url = response.data[0].url
        print("Image generated successfully")

        return jsonify({
            "success": True,
            "imageUrl": image_url,
            "prompt": prompt
        })

    except Exception as e:
        print(f"Server error: {e}")
        error_message = str(e)
        if "rate_limit" in error_message.lower():
            return jsonify({"error": "OpenAI rate limit exceeded. Please try again later."}), 429
        elif "billing" in error_message.lower() or "quota" in error_message.lower():
            return jsonify({"error": "OpenAI billing issue. Please check your account."}), 400
        elif "authentication" in error_message.lower():
            return jsonify({"error": "Invalid OpenAI API key"}), 401
        else:
            return jsonify({"error": f"Internal server error: {error_message}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=False)