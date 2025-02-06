#!/usr/bin/env python3
"""
twitter_utils.py

Utility script for Twitter API operations like user lookup and validation.
"""

import os
import json
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

class TwitterAPI:
    def __init__(self):
        load_dotenv()
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        if not self.bearer_token or self.bearer_token == "YOUR_BEARER_TOKEN":
            raise ValueError("""
            Twitter Bearer Token not found!
            
            Please follow these steps:
            1. Go to https://developer.twitter.com/en/portal/dashboard
            2. Create or select your app
            3. Get your Bearer Token
            4. Add it to your .env file as:
               TWITTER_BEARER_TOKEN=your_actual_token_here
            """)
        
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "v2UserLookupPython"
        }

    def lookup_user(self, username):
        """Look up a Twitter user by username."""
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={
                    "user.fields": "description,public_metrics,verified"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logging.error(f"Request failed: {str(e)}")
            return None

    def validate_accounts(self, usernames):
        """Validate a list of Twitter usernames."""
        results = []
        for username in usernames:
            data = self.lookup_user(username)
            if data and 'data' in data:
                user = data['data']
                results.append({
                    'username': username,
                    'id': user['id'],
                    'valid': True,
                    'verified': user.get('verified', False),
                    'metrics': user.get('public_metrics', {})
                })
            else:
                results.append({
                    'username': username,
                    'valid': False,
                    'error': 'User not found or private'
                })
        return results

def main():
    # Example target accounts
    target_accounts = [
        "elonmusk",
        "cz_binance",
        "solana",
        "raydium_io"
    ]
    
    try:
        api = TwitterAPI()
        
        # Validate all target accounts
        print("\nValidating target accounts...")
        results = api.validate_accounts(target_accounts)
        
        # Display results in a formatted way
        print("\nValidation Results:")
        print("-" * 50)
        for result in results:
            if result['valid']:
                print(f"✅ @{result['username']}:")
                print(f"   ID: {result['id']}")
                print(f"   Verified: {'✓' if result['verified'] else '✗'}")
                if 'metrics' in result:
                    metrics = result['metrics']
                    print(f"   Followers: {metrics.get('followers_count', 'N/A')}")
                    print(f"   Following: {metrics.get('following_count', 'N/A')}")
            else:
                print(f"❌ @{result['username']}: {result['error']}")
            print("-" * 50)
            
    except ValueError as ve:
        logging.error(f"Configuration error: {ve}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main() 