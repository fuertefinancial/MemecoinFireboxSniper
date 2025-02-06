#!/usr/bin/env python3
"""
server.py

Backend server for MemeSniper.
Provides REST API endpoints and uses SocketIO to send real-time
simulated tweets and whale activity events.
"""

import os
import time
import random
from threading import Thread
from datetime import datetime

# IMPORTANT: Monkey-patch for eventlet BEFORE other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev_key')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global data
whale_activity_data = []  # List to hold latest whale events
bot_settings = {
    "tradeAmount": 0.5,
    "stopLoss": 5,
    "riskReward": 3
}
tracked_accounts = ["elonmusk", "cz_binance", "solana", "raydium_io"]

# API Endpoints
@app.route('/')
def index():
    return jsonify({"status": "Server is running", "message": "MemeSniper backend active"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/api/twitter/tracked-accounts')
def get_tracked_accounts():
    return jsonify({"accounts": tracked_accounts})

@app.route('/api/whale-activity')
def get_whale_activity():
    return jsonify({"activities": whale_activity_data})

@app.route('/api/save-settings', methods=["POST"])
def save_settings():
    global bot_settings
    data = request.get_json()
    if not data:
        return jsonify({"message": "Invalid settings data"}), 400
    try:
        bot_settings["tradeAmount"] = float(data.get("tradeAmount", 0.5))
        bot_settings["stopLoss"] = float(data.get("stopLoss", 5))
        bot_settings["riskReward"] = float(data.get("riskReward", 3))
        return jsonify({"message": "Settings updated successfully."})
    except Exception as e:
        return jsonify({"message": f"Error updating settings: {e}"}), 500

# Background simulation functions
def simulate_tweets():
    """Simulate incoming tweets every 10 seconds."""
    while True:
        time.sleep(10)
        tweet = {
            "id": str(random.randint(100000, 999999)),
            "text": random.choice([
                "Check out this new meme coin!",
                "Market is about to explode!",
                "Warning: pump incoming!",
                "New listing on Raydium!"
            ]),
            "author": random.choice(tracked_accounts),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "signals": {
                "should_trade": random.choice([True, False])
            }
        }
        logging.info(f"Emitting tweet: {tweet}")
        socketio.emit("new_tweet", tweet)

def simulate_whale_activity():
    """Simulate whale activity events every 15 seconds."""
    while True:
        time.sleep(15)
        event = {
            "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "wallet": "0x" + ''.join(random.choices("abcdef0123456789", k=40)),
            "amount": round(random.uniform(10, 200), 2),
            "type": random.choice(["buy", "sell"])
        }
        whale_activity_data.append(event)
        # Keep only the latest 50 events
        if len(whale_activity_data) > 50:
            whale_activity_data.pop(0)
        logging.info(f"New whale activity: {event}")
        socketio.emit("new_whale_activity", event)

def start_background_threads():
    tweet_thread = Thread(target=simulate_tweets)
    tweet_thread.daemon = True
    tweet_thread.start()

    whale_thread = Thread(target=simulate_whale_activity)
    whale_thread.daemon = True
    whale_thread.start()

if __name__ == "__main__":
    start_background_threads()
    port = int(os.getenv("PORT", 5002))
    logging.info(f"Starting server on port {port}")
    socketio.run(app, host="0.0.0.0", port=port, debug=True) 