'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, DEFAULT_API_BASE_URL, getStoredApiBaseUrl, setStoredApiBaseUrl } from '@/lib/api';

export default function SettingsPage() {
  const [apiBaseUrl, setApiBaseUrl] = useState(getStoredApiBaseUrl());
  const [status, setStatus] = useState('Idle');

  useEffect(() => {
    setApiBaseUrl(getStoredApiBaseUrl());
  }, []);

  const testConnection = async () => {
    try {
      const response = await api.health();
      setStatus(response.status === 'ok' ? 'Backend reachable' : 'Unexpected response');
      toast.success('Backend connection verified');
    } catch (error) {
      setStatus('Connection failed');
      toast.error(error instanceof Error ? error.message : 'Connection failed');
    }
  };

  const saveSettings = () => {
    setStoredApiBaseUrl(apiBaseUrl);
    toast.success('Settings saved');
    void testConnection();
  };

  const resetMemory = async () => {
    try {
      await api.resetMemory();
      toast.success('Memory reset');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to reset memory');
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4 shadow-2xl shadow-slate-950/40">
        <p className="text-sm text-sky-400">Configuration</p>
        <h2 className="text-xl font-semibold">Settings</h2>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-lg font-semibold">Backend connection</h3>
          <p className="mt-2 text-sm text-slate-400">Point the UI at the FastAPI service running on your machine.</p>
          <label className="mt-4 block text-sm font-medium text-slate-300">API base URL</label>
          <input value={apiBaseUrl} onChange={(event) => setApiBaseUrl(event.target.value)} className="mt-2 w-full rounded-2xl border border-slate-700 bg-slate-950/60 px-3 py-3 text-sm text-slate-100 outline-none" />
          <div className="mt-3 flex flex-wrap gap-2">
            <button onClick={saveSettings} className="rounded-full bg-sky-500 px-4 py-2 text-sm font-semibold text-slate-950">Save</button>
            <button onClick={() => void testConnection()} className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200">Test</button>
            <button onClick={() => { setApiBaseUrl(DEFAULT_API_BASE_URL); setStoredApiBaseUrl(DEFAULT_API_BASE_URL); }} className="rounded-full border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200">Reset</button>
          </div>
          <p className="mt-3 text-sm text-slate-400">Current status: {status}</p>
        </section>

        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
          <h3 className="text-lg font-semibold">Memory tools</h3>
          <p className="mt-2 text-sm text-slate-400">Reset stored facts and chat sessions when you want a fresh start.</p>
          <button onClick={() => void resetMemory()} className="mt-4 rounded-full border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm font-semibold text-rose-200">Reset memory</button>
        </section>
      </div>
    </div>
  );
}
