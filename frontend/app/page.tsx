'use client';

import React, { useEffect, useState } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:5002';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5002';

// Types
interface Tweet {
  id: string;
  text: string;
  author: string;
  created_at: string;
  signals?: {
    should_trade: boolean;
    token_address?: string;
    token_symbol?: string;
  };
}

interface WhaleActivity {
  time: string;
  wallet: string;
  amount: number;
  type: 'buy' | 'sell';
}

interface BotSettings {
  tradeAmount: number;
  stopLoss: number;
  riskReward: number;
}

export default function Dashboard() {
  // State
  const [socketConnected, setSocketConnected] = useState(false);
  const [tweets, setTweets] = useState<Tweet[]>([]);
  const [whaleActivity, setWhaleActivity] = useState<WhaleActivity[]>([]);
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [botSettings, setBotSettings] = useState<BotSettings>({
    tradeAmount: 0.5,
    stopLoss: 5,
    riskReward: 3,
  });

  useEffect(() => {
    // Connect to backend
    const socket = io(SOCKET_URL, {
      transports: ['websocket'],
      reconnectionAttempts: 5
    });

    socket.on('connect', () => {
      console.log('Connected to backend');
      setSocketConnected(true);
    });

    socket.on('disconnect', () => {
      console.log('Disconnected from backend');
      setSocketConnected(false);
    });

    socket.on('new_tweet', (tweet: Tweet) => {
      console.log('New tweet received:', tweet);
      setTweets(prev => [tweet, ...prev].slice(0, 50));
    });

    socket.on('new_whale_activity', (activity: WhaleActivity) => {
      console.log('New whale activity received:', activity);
      setWhaleActivity(prev => [activity, ...prev].slice(0, 50));
    });

    // Fetch initial data
    fetchData();

    return () => {
      socket.disconnect();
    };
  }, []);

  const fetchData = async () => {
    try {
      const [whaleRes] = await Promise.all([
        fetch(`${API_URL}/api/whale-activity`)
      ]);

      const whaleData = await whaleRes.json();
      setWhaleActivity(whaleData.activities);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const connectWallet = async () => {
    try {
      if (typeof window !== 'undefined' && (window as any).phantom?.solana) {
        const response = await (window as any).phantom.solana.connect();
        setWalletAddress(response.publicKey.toString());
        setWalletConnected(true);
      } else {
        alert('Please install Phantom wallet!');
      }
    } catch (error) {
      console.error('Error connecting wallet:', error);
    }
  };

  const saveSettings = async () => {
    try {
      const response = await fetch(`${API_URL}/api/save-settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(botSettings)
      });
      
      if (response.ok) {
        alert('Settings saved successfully!');
      } else {
        alert('Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      alert('Error saving settings');
    }
  };

  return (
    <main className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Status Bar */}
        <div className="bg-white shadow-sm rounded-lg mb-4 p-2 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${socketConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span>{socketConnected ? 'Connected to Backend' : 'Disconnected'}</span>
          </div>
          <button
            onClick={connectWallet}
            className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
          >
            {walletConnected 
              ? `Connected: ${walletAddress.slice(0,4)}...${walletAddress.slice(-4)}`
              : 'Connect Phantom Wallet'}
          </button>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Twitter Feed */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Live Twitter Feed</h2>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {tweets.map((tweet) => (
                <div key={tweet.id} className="border rounded-lg p-4">
                  <div className="flex justify-between">
                    <span className="font-medium">@{tweet.author}</span>
                    <span className="text-gray-500 text-sm">
                      {new Date(tweet.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="mt-2">{tweet.text}</p>
                  {tweet.signals?.should_trade && (
                    <div className="mt-2 bg-yellow-100 p-2 rounded">
                      <span className="text-yellow-800">Trading Signal Detected!</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Whale Activity */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Whale Activity</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr>
                    <th className="px-4 py-2">Time</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Amount (SOL)</th>
                  </tr>
                </thead>
                <tbody>
                  {whaleActivity.map((activity, index) => (
                    <tr key={index} className={index % 2 === 0 ? 'bg-gray-50' : ''}>
                      <td className="px-4 py-2">{activity.time}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded ${
                          activity.type === 'buy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {activity.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-2">{activity.amount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Settings */}
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">Bot Settings</h2>
            <button
              onClick={saveSettings}
              className="bg-blue-500 text-white px-4 py-2 rounded-md hover:bg-blue-600"
            >
              Save Settings
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Trade Amount (SOL)
              </label>
              <input
                type="number"
                value={botSettings.tradeAmount}
                onChange={(e) => setBotSettings({...botSettings, tradeAmount: parseFloat(e.target.value)})}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Stop Loss (%)
              </label>
              <input
                type="number"
                value={botSettings.stopLoss}
                onChange={(e) => setBotSettings({...botSettings, stopLoss: parseFloat(e.target.value)})}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Risk/Reward Ratio
              </label>
              <input
                type="number"
                value={botSettings.riskReward}
                onChange={(e) => setBotSettings({...botSettings, riskReward: parseFloat(e.target.value)})}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
} 