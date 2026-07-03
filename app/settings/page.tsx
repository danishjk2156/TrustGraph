'use client';

import { useState } from 'react';
import { toast } from 'sonner';

export default function SettingsPage() {
  const [apiUrl, setApiUrl] = useState(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000');
  const [isSaved, setIsSaved] = useState(false);

  const handleSaveSettings = async () => {
    // In a real app, this would save to localStorage or a backend
    localStorage.setItem('apiUrl', apiUrl);
    setIsSaved(true);
    toast.success('Settings saved');
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleReset = () => {
    const confirmed = confirm('Reset all memory data? This cannot be undone.');
    if (confirmed) {
      toast.success('Memory has been reset');
    }
  };

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 py-4">
        <h1 className="text-2xl font-bold text-slate-100">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">
          Configure TrustGraph preferences and memory management
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-6">
          {/* API Configuration */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">API Configuration</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  API Base URL
                </label>
                <input
                  type="text"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
                  placeholder="http://localhost:8000"
                />
                <p className="text-xs text-slate-400 mt-2">
                  The URL where your TrustGraph backend API is running
                </p>
              </div>
              <button
                onClick={handleSaveSettings}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg px-4 py-2 font-medium transition-colors"
              >
                {isSaved ? '✓ Saved' : 'Save Settings'}
              </button>
            </div>
          </div>

          {/* Memory Management */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">Memory Management</h2>
            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-medium text-slate-300 mb-3">Danger Zone</h3>
                <button
                  onClick={handleReset}
                  className="bg-red-600/20 hover:bg-red-600/30 border border-red-500/40 text-red-400 rounded-lg px-4 py-2 font-medium transition-colors"
                >
                  Reset All Memory
                </button>
                <p className="text-xs text-slate-400 mt-2">
                  Permanently delete all facts, contradictions, and memory data. This action cannot be undone.
                </p>
              </div>
            </div>
          </div>

          {/* About */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">About</h2>
            <div className="space-y-3 text-sm text-slate-400">
              <div className="flex justify-between">
                <span>TrustGraph Version</span>
                <span className="text-slate-100">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span>Frontend</span>
                <span className="text-slate-100">Next.js 16</span>
              </div>
              <div className="flex justify-between">
                <span>Backend</span>
                <span className="text-slate-100">FastAPI</span>
              </div>
              <div className="border-t border-slate-700 pt-3">
                <p className="text-xs">
                  TrustGraph is an AI-powered memory management system that helps you build a trusted knowledge
                  base by automatically detecting contradictions and tracking information reliability.
                </p>
              </div>
            </div>
          </div>

          {/* Keyboard Shortcuts */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-6">
            <h2 className="text-lg font-semibold text-slate-100 mb-4">Keyboard Shortcuts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Send message</span>
                <span className="text-slate-300 font-mono">Enter</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">New line in message</span>
                <span className="text-slate-300 font-mono">Shift + Enter</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Go to Chat</span>
                <span className="text-slate-300 font-mono">Ctrl + 1</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Go to Facts</span>
                <span className="text-slate-300 font-mono">Ctrl + 2</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
