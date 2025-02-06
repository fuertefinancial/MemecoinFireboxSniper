import React, { useEffect, useState } from 'react';
import { Inter } from "next/font/google";
import Head from 'next/head';
import { io } from 'socket.io-client';

const inter = Inter({ subsets: ["latin"] });

interface Tweet {
  id: string;
  text: string;
  author: string;
  created_at: string;
  signals: {
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

export default function Dashboard() {
  const [tweets, setTweets] = useState<Tweet[]>([]);
  const [trackedAccounts, setTrackedAccounts] = useState<string[]>([]);
  const [newAccount, setNewAccount] = useState('');
  const [whaleActivity, setWhaleActivity] = useState<WhaleActivity[]>([]);
  const [walletConnected, setWalletConnected] = useState(false);
  const [walletAddress, setWalletAddress] = useState('');
  const [settings, setSettings] = useState({
    tradeAmount: 0.5,
    stopLoss: 5,
    riskReward: 3
  });

  useEffect(() => {
    // Initialize socket connection
    const socket = io('http://localhost:5002', {
      transports: ['websocket'],
      cors: {
        origin: "http://localhost:3000"
      }
    });

    socket.on('connect', () => {
      console.log('Connected to backend');
    });

    socket.on('new_tweet', (tweet: Tweet) => {
      setTweets(prev => [tweet, ...prev].slice(0, 50));
    });

    // Load initial data
    fetchTrackedAccounts();
    fetchWhaleActivity();

    return () => {
      socket.disconnect();
    };
  }, []);

  const fetchTrackedAccounts = async () => {
    try {
      const response = await fetch('http://localhost:5002/api/twitter/tracked-accounts');
      const data = await response.json();
      setTrackedAccounts(data.accounts);
    } catch (error) {
      console.error('Error fetching tracked accounts:', error);
    }
  };

  const fetchWhaleActivity = async () => {
    try {
      const response = await fetch('http://localhost:5002/api/whale-activity');
      const data = await response.json();
      setWhaleActivity(data.activities);
    } catch (error) {
      console.error('Error fetching whale activity:', error);
    }
  };

  const connectWallet = async () => {
    try {
      if (window.phantom?.solana) {
        const response = await window.phantom.solana.connect();
        setWalletAddress(response.publicKey.toString());
        setWalletConnected(true);
      } else {
        alert('Phantom wallet not found! Please install it first.');
      }
    } catch (error) {
      console.error('Error connecting wallet:', error);
    }
  };

  return (
    <div className={`min-h-screen bg-gray-100 ${inter.className}`}>
      <Head>
        <title>Meme Coin Twitter Sniper Bot</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <nav className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-bold">Meme Coin Sniper</h1>
            </div>
            <div className="flex items-center">
              <button
                onClick={connectWallet}
                className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
              >
                {walletConnected ? 'Connected' : 'Connect Phantom Wallet'}
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Twitter Feed Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Live Twitter Feed</h2>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {tweets.map((tweet) => (
                <div key={tweet.id} className="border rounded-lg p-4">
                  <div className="flex justify-between">
                    <span className="font-medium">@{tweet.author}</span>
                    <span className="text-gray-500 text-sm">
                      {new Date(tweet.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="mt-2">{tweet.text}</p>
                  {tweet.signals.should_trade && (
                    <div className="mt-2 bg-yellow-100 p-2 rounded">
                      <span className="text-yellow-800">Trading Signal Detected!</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Whale Activity Section */}
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

        {/* Settings Section */}
        <div className="mt-6 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">Bot Settings</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Trade Amount (SOL)
              </label>
              <input
                type="number"
                value={settings.tradeAmount}
                onChange={(e) => setSettings({...settings, tradeAmount: parseFloat(e.target.value)})}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Stop Loss (%)
              </label>
              <input
                type="number"
                value={settings.stopLoss}
                onChange={(e) => setSettings({...settings, stopLoss: parseFloat(e.target.value)})}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">
                Risk/Reward Ratio
              </label>
              <input
                type="number"
                value={settings.riskReward}
                onChange={(e) => setSettings({...settings, riskReward: parseFloat(e.target.value)})}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500"
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 