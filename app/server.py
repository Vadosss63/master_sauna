#!/usr/bin/env python3
import os
import sys
import json
import logging

from flask import Flask, request, jsonify


from sauna_module import process_sauna_interaction

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
log = logging.getLogger("harvia-test")

app = Flask(__name__)

@app.route('/')
def home():
    """Home endpoint with API information"""
    return jsonify({
        "message": "Control Harvia device by voice & ai",
        "endpoints": {
            "process": "POST /process with JSON: {'message': '<message>'}",\
        }
    })


@app.route('/process', methods=['POST'])
def get_devices():
    """
    Get list of available devices (helper endpoint)
    
    Returns:
        JSON with list of devices
    """
    try:
        text = request.get_json().get('message')
        answer = process_sauna_interaction(text)
        return json.dumps({"answer": answer})

    except Exception as e:
        return jsonify({"error": f"Failed to process message: {str(e)}"}), 500


if __name__ == '__main__':
    # Set environment variables for credentials
    # export HARVIA_USERNAME="your-email@example.com"
    # export HARVIA_PASSWORD="your-password"
    
    
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True,
        ssl_context='adhoc',
    )
