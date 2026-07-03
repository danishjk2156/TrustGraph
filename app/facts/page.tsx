'use client';

import { useState } from 'react';
import useSWR from 'swr';
import { FactCard } from '@/components/fact-card';
import { listFacts } from '@/lib/api';

export default function FactsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLevel, setFilterLevel] = useState<'all' | 'high' | 'medium' | 'low'>('all');

  const { data: facts = [], isLoading, mutate } = useSWR('facts', listFacts, { refreshInterval: 5000 });

  const filteredFacts = facts.filter((fact) => {
    // Search filter
    if (searchQuery && !fact.text.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }

    // Trust level filter
    if (filterLevel === 'high' && fact.trustScore < 0.7) return false;
    if (filterLevel === 'medium' && (fact.trustScore < 0.4 || fact.trustScore >= 0.7)) return false;
    if (filterLevel === 'low' && fact.trustScore >= 0.4) return false;

    return true;
  });

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 py-4">
        <h1 className="text-2xl font-bold text-slate-100">Memory Library</h1>
        <p className="text-sm text-slate-400 mt-1">
          Explore all stored facts, their trust scores, and manage contradictions
        </p>
      </div>

      {/* Controls */}
      <div className="border-b border-slate-800 bg-slate-900/30 px-6 py-4 space-y-3">
        <input
          type="text"
          placeholder="Search facts..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20"
        />

        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setFilterLevel('all')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterLevel === 'all'
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-300 border border-slate-700/50 hover:border-slate-600/50'
            }`}
          >
            All ({facts.length})
          </button>
          <button
            onClick={() => setFilterLevel('high')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterLevel === 'high'
                ? 'bg-green-500/20 text-green-400 border border-green-500/40'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-300 border border-slate-700/50 hover:border-slate-600/50'
            }`}
          >
            High Trust ({facts.filter((f) => f.trustScore >= 0.7).length})
          </button>
          <button
            onClick={() => setFilterLevel('medium')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterLevel === 'medium'
                ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/40'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-300 border border-slate-700/50 hover:border-slate-600/50'
            }`}
          >
            Medium ({facts.filter((f) => f.trustScore >= 0.4 && f.trustScore < 0.7).length})
          </button>
          <button
            onClick={() => setFilterLevel('low')}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterLevel === 'low'
                ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                : 'bg-slate-800/50 text-slate-400 hover:text-slate-300 border border-slate-700/50 hover:border-slate-600/50'
            }`}
          >
            Low ({facts.filter((f) => f.trustScore < 0.4).length})
          </button>
        </div>
      </div>

      {/* Facts List */}
      <div className="flex-1 overflow-y-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-2 border-blue-500 border-t-transparent mx-auto mb-4" />
              <p className="text-slate-400">Loading facts...</p>
            </div>
          </div>
        ) : filteredFacts.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">📚</span>
              </div>
              <p className="text-slate-400">
                {searchQuery || filterLevel !== 'all' ? 'No facts match your filters' : 'No facts stored yet'}
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm text-slate-400 mb-4">
              Showing {filteredFacts.length} fact{filteredFacts.length !== 1 ? 's' : ''}
            </p>
            {filteredFacts.map((fact) => (
              <FactCard
                key={fact.id}
                id={fact.id}
                text={fact.text}
                trustScore={fact.trustScore}
                storedAt={fact.storedAt}
                reinforcementCount={fact.reinforcementCount}
                isContradicted={fact.isContradicted}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
