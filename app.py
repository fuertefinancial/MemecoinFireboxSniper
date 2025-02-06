#!/usr/bin/env python3
"""
app.py

A Flask web application that integrates Phantom wallet connectivity,
fetches top trader wallet data from Dexscreener, and displays a wallet tracker.
This file is designed for local development (for example on Cursor) and can be extended
with further trade execution or blockchain integration features.
"""

import logging
import requests
from flask import Flask, jsonify, render_template_string
from flask_socketio import SocketIO
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# Initialize Flask and SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev_key_123')  # Add a secret key
socketio = SocketIO(app)

# Hypothetical Dexscreener API endpoint for top traders
DEXSCREENER_TOP_TRADERS_API_URL = "https://api.dexscreener.com/latest/traders"

# -------------------------------------------------------------------
# HTML Template: Phantom wallet integration and wallet tracker display
# -------------------------------------------------------------------
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Solana Trade Bot & Wallet Tracker</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        h1, h2 { color: #333; }
        table { border-collapse: collapse; width: 80%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        #connectButton { padding: 10px 20px; font-size: 16px; }
    </style>
</head>
<body>
    <h1>Solana Trade Bot & Wallet Tracker</h1>
    
    <section id="walletSection">
        <button id="connectButton">Connect Phantom Wallet</button>
        <p id="walletAddress">Not connected</p>
    </section>
    
    <section id="trackerSection">
        <h2>Top Trader Wallets (Dexscreener)</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Wallet Address</th>
                    <th>Volume</th>
                </tr>
            </thead>
            <tbody id="topTradersTable">
                <tr><td colspan="3">Loading data...</td></tr>
            </tbody>
        </table>
    </section>
    
    <script>
        // --- Phantom Wallet Integration ---
        async function connectWallet() {
            if (window.solana && window.solana.isPhantom) {
                try {
                    const resp = await window.solana.connect();
                    document.getElementById('walletAddress').innerText = "Connected: " + resp.publicKey.toString();
                } catch (err) {
                    console.error("Wallet connection failed", err);
                    alert("Wallet connection failed!");
                }
            } else {
                alert("Phantom wallet not found. Please install it from https://phantom.app/");
            }
        }
        document.getElementById("connectButton").addEventListener("click", connectWallet);
        
        // --- Fetch Top Trader Wallet Data from Dexscreener ---
        async function fetchTopTraders() {
            try {
                const response = await fetch("/api/top-traders");
                const data = await response.json();
                const tableBody = document.getElementById("topTradersTable");
                tableBody.innerHTML = "";
                if (data.traders.length === 0) {
                    tableBody.innerHTML = "<tr><td colspan='3'>No data available</td></tr>";
                } else {
                    data.traders.forEach(function(trader, index) {
                        const row = document.createElement("tr");
                        const rankCell = document.createElement("td");
                        rankCell.innerText = index + 1;
                        const addressCell = document.createElement("td");
                        addressCell.innerText = trader.wallet;
                        const volumeCell = document.createElement("td");
                        volumeCell.innerText = trader.volume;
                        row.appendChild(rankCell);
                        row.appendChild(addressCell);
                        row.appendChild(volumeCell);
                        tableBody.appendChild(row);
                    });
                }
            } catch (err) {
                console.error("Error fetching top traders", err);
                document.getElementById("topTradersTable").innerHTML = "<tr><td colspan='3'>Error loading data</td></tr>";
            }
        }
        // Fetch data on page load
        window.onload = fetchTopTraders;
    </script>
</body>
</html>
"""

# -------------------------------------------------------------------
# Flask Routes
# -------------------------------------------------------------------
@app.route("/")
def index():
    """
    Render the main page with Phantom wallet integration and wallet tracker.
    """
    return render_template_string(INDEX_HTML)

@app.route('/health')
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy", "message": "Server is running"})

@app.route("/api/top-traders")
def api_top_traders():
    """
    API endpoint that fetches the top trader wallet data from Dexscreener.
    In case of error, returns fallback dummy data.
    """
    try:
        response = requests.get(DEXSCREENER_TOP_TRADERS_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Assuming the API returns a JSON object with a key "traders" containing a list.
        traders = data.get("traders", [])
        logging.info("Fetched top traders data from Dexscreener.")
    except Exception as e:
        logging.error("Error fetching top traders from Dexscreener: %s", e)
        # Fallback dummy data if API call fails.
        traders = [
            {"wallet": "7Tz...dummy1", "volume": 1200},
            {"wallet": "9Xf...dummy2", "volume": 950},
            {"wallet": "3Ab...dummy3", "volume": 870}
        ]
    return jsonify({"traders": traders})

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    try:
        # Load environment variables
        load_dotenv()
        
        # Start the server
        logging.info("Starting server on http://localhost:5002")
        socketio.run(app, debug=True, port=5002, host='0.0.0.0')
        
    except Exception as e:
        logging.error(f"Server failed to start: {e}")
        raise

if __name__ == "__main__":
    main()
