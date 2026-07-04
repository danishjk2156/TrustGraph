'use client';

import { useEffect, useState } from 'react';
import { RotateCcw, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { api, type FactRecord, type FactsResponse } from '@/lib/api';
import { TrustBadge } from '@/components/trust-badge';

export default function FactsPage() {
  const [facts, setFacts] = useState<FactRecord[]>([]);
  const [filter, setFilter] = useState<'all' | 'High' | 'Medium' | 'Low'>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadFacts();
  }, []);

  const loadFacts = async () => {
    setLoading(true);
    try {
      const data = await api.getFacts();
      setFacts(data.facts);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to load facts');
    } finally {
      setLoading(false);
    }
  };

  const reinforce = async (factId: string) => {
    try {
      await api.reinforceFact(factId);
      toast.success('Fact reinforced');
      await loadFacts();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to reinforce fact');
    }
  };

  const visibleFacts = facts.filter((item) => {
    if (filter === 'all') return true;
    const level = item.trust_score.score >= 0.7 ? 'High' : item.trust_score.score >= 0.4 ? 'Medium' : 'Low';
    return level === filter;
  });

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4 shadow-2xl shadow-slate-950/40">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm text-sky-400">Memory library</p>
            <h2 className="text-xl font-semibold">Trusted facts</h2>
          </div>
          <div className="flex gap-2">
            {(['all', 'High', 'Medium', 'Low'] as const).map((value) => (
              <button key={value} onClick={() => setFilter(value)} className={`rounded-full px-3 py-2 text-sm ${filter === value ? 'bg-sky-500 text-slate-950' : 'bg-slate-800 text-slate-300'}`}>
                {value}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading ? (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-center text-slate-400">Loading facts…</div>
      ) : visibleFacts.length === 0 ? (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-8 text-center text-slate-400">
          <Sparkles className="mx-auto mb-3 h-8 w-8 text-sky-400" />
          <p>No facts match the current filter yet.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {visibleFacts.map((item) => (
            <article key={item.fact.fact_id} className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.25em] text-slate-500">{item.fact.subject}</p>
                  <h3 className="mt-1 text-lg font-semibold text-slate-100">{item.fact.normalized_text}</h3>
                </div>
                <TrustBadge score={item.trust_score.score} />
              </div>
              <div className="mt-4 space-y-2 text-sm text-slate-400">
                <p>Source: {item.fact.source}</p>
                <p>Reinforced {item.fact.reinforcement_count}x</p>
                <p>Status: {item.fact.status}</p>
              </div>
              <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-300">
                <p className="font-medium text-slate-200">Trust breakdown</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <span className="rounded-full bg-slate-800 px-2.5 py-1">Recency {(item.trust_score.recency_component * 100).toFixed(0)}%</span>
                  <span className="rounded-full bg-slate-800 px-2.5 py-1">Reinforcement {(item.trust_score.reinforcement_component * 100).toFixed(0)}%</span>
                  <span className="rounded-full bg-slate-800 px-2.5 py-1">Consistency {(item.trust_score.consistency_component * 100).toFixed(0)}%</span>
                </div>
              </div>
              <button onClick={() => void reinforce(item.fact.fact_id)} className="mt-4 inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200">
                <RotateCcw className="h-4 w-4" /> Reinforce
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
