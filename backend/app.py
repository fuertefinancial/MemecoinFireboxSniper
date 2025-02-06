from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import logging
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# Initialize Flask and SocketIO
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev_key_123')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.route('/')
def index():
    return jsonify({"status": "Server is running"})

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/api/twitter/tracked-accounts')
def get_tracked_accounts():
    return jsonify({
        "accounts": [
            "elonmusk",
            "cz_binance",
            "solana"
        ]
    })

@app.route('/api/whale-activity')
def get_whale_activity():
    return jsonify({
        "activities": [
            {
                "time": "2024-01-20 12:00:00",
                "wallet": "0x1234...5678",
                "amount": 100,
                "type": "buy"
            }
        ]
    })

def main():
    try:
        load_dotenv()
        print("Starting server at http://localhost:5002")
        socketio.run(app, debug=True, port=5002, host='0.0.0.0', allow_unsafe_werkzeug=True)
    except Exception as e:
        logging.error(f"Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main() 