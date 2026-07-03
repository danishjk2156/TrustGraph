'use client';

import { useState } from 'react';
import { TrustBadge } from './trust-badge';
import { reinforceFact } from '@/lib/api';
import { toast } from 'sonner';

interface FactCardProps {
  id: string;
  text: string;
  trustScore: number;
  storedAt: string;
  reinforcementCount: number;
  isContradicted?: boolean;
}

export function FactCard({
  id,
  text,
  trustScore,
  storedAt,
  reinforcementCount,
  isContradicted,
}: FactCardProps) {
  const [isReinforcing, setIsReinforcing] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleReinforce = async () => {
    setIsReinforcing(true);
    try {
      await reinforceFact(id);
      toast.success('Fact reinforced');
    } catch (error) {
      toast.error('Failed to reinforce fact');
      console.error(error);
    } finally {
      setIsReinforcing(false);
    }
  };

  const storedDate = new Date(storedAt);
  const daysOld = Math.floor((Date.now() - storedDate.getTime()) / (1000 * 60 * 60 * 24));

  return (
    <div
      className={`rounded-lg border p-4 mb-3 transition-all ${
        isContradicted
          ? 'bg-red-500/5 border-red-500/30'
          : 'bg-slate-800/50 border-slate-700/50'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm text-slate-100 leading-relaxed break-words">{text}</p>
        </div>
        {isContradicted && (
          <div className="flex-shrink-0">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-red-500/20 text-red-400 border border-red-500/30 whitespace-nowrap">
              ⚠ Contradicted
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between mt-3 text-xs text-slate-400">
        <div className="flex items-center gap-3">
          <span>{storedDate.toLocaleDateString()} ({daysOld}d ago)</span>
          <span>•</span>
          <span>{reinforcementCount} reinforcements</span>
        </div>
        <TrustBadge score={trustScore} showTooltip={false} size="sm" />
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-2 text-xs text-slate-400">
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-900/50 rounded p-2">
              <div className="text-slate-500 mb-1">Recency Score</div>
              <div className="font-semibold text-slate-200">75%</div>
            </div>
            <div className="bg-slate-900/50 rounded p-2">
              <div className="text-slate-500 mb-1">Reinforcement</div>
              <div className="font-semibold text-slate-200">{reinforcementCount}×</div>
            </div>
            <div className="bg-slate-900/50 rounded p-2">
              <div className="text-slate-500 mb-1">Consistency</div>
              <div className="font-semibold text-slate-200">85%</div>
            </div>
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="px-2 py-1.5 rounded text-xs text-slate-400 hover:text-slate-300 hover:bg-slate-700/50 transition-colors"
        >
          {expanded ? 'Hide' : 'Details'}
        </button>
        <button
          onClick={handleReinforce}
          disabled={isReinforcing}
          className="px-2 py-1.5 rounded text-xs bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50 transition-colors"
        >
          {isReinforcing ? 'Reinforcing...' : 'Reinforce'}
        </button>
      </div>
    </div>
  );
}
