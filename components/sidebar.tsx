'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';
import { BrainCircuit, MessageSquareText, Network, Settings, Sparkles } from 'lucide-react';
import { api, type StatsResponse } from '@/lib/api';
import { cn } from '@/lib/utils';

const links = [
  { href: '/chat', label: 'Chat', icon: MessageSquareText },
  { href: '/facts', label: 'Facts', icon: BrainCircuit },
  { href: '/graph', label: 'Graph', icon: Network },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api
      .getStats()
      .then((data) => {
        if (active) setStats(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Connection failed');
      });
    return () => {
      active = false;
    };
  }, []);

  const summary = useMemo(() => {
    if (!stats) return null;
    return [
      { label: 'Facts', value: stats.totalMemorySize },
      { label: 'Active', value: stats.activeFacts },
      { label: 'Contradictions', value: stats.contradictions },
    ];
  }, [stats]);

  return (
    <aside className="w-full border-b border-slate-800 bg-slate-900/80 p-4 backdrop-blur lg:w-72 lg:border-b-0 lg:border-r">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-sky-400">TrustGraph</p>
          <h1 className="text-xl font-semibold">Memory Dashboard</h1>
        </div>
        <div className="rounded-full border border-sky-500/30 bg-sky-500/10 p-2 text-sky-300">
          <Sparkles className="h-5 w-5" />
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <p className="text-sm font-medium text-slate-200">Connection</p>
        <p className="mt-1 text-sm text-slate-400">{error ? `Offline: ${error}` : 'Connected to backend'}</p>
        {summary?.map((item) => (
          <div key={item.label} className="mt-3 flex items-center justify-between rounded-lg bg-slate-800/70 px-3 py-2 text-sm">
            <span className="text-slate-400">{item.label}</span>
            <span className="font-semibold text-slate-100">{item.value}</span>
          </div>
        ))}
      </div>

      <nav className="mt-6 space-y-2">
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = pathname?.startsWith(link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition',
                isActive ? 'bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30' : 'text-slate-300 hover:bg-slate-800/80 hover:text-white',
              )}
            >
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
