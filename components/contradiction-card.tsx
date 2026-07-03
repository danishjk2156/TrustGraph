'use client';

import { useState } from 'react';
import { TrustBadge } from './trust-badge';
import { resolveFact } from '@/lib/api';
import { toast } from 'sonner';

interface ContradictionCardProps {
  id: string;
  factA: {
    id: string;
    text: string;
    trustScore: number;
    storedAt: string;
  };
  factB: {
    id: string;
    text: string;
    trustScore: number;
    storedAt: string;
  };
  severity: 'low' | 'medium' | 'high';
  onResolved?: () => void;
}

export function ContradictionCard({
  id,
  factA,
  factB,
  severity,
  onResolved,
}: ContradictionCardProps) {
  const [isResolving, setIsResolving] = useState(false);

  // Validate that factA and factB exist
  if (!factA || !factB) {
    return null;
  }

  const getSeverityColor = () => {
    switch (severity) {
      case 'high':
        return 'bg-red-500/10 border-red-500/40 text-red-400';
      case 'medium':
        return 'bg-yellow-500/10 border-yellow-500/40 text-yellow-400';
      case 'low':
        return 'bg-blue-500/10 border-blue-500/40 text-blue-400';
    }
  };

  const handleResolve = async (action: 'keep' | 'remove') => {
    setIsResolving(true);
    try {
      await resolveFact(id, action === 'keep' ? factA.id : factB.id);
      toast.success('Contradiction resolved');
      onResolved?.();
    } catch (error) {
      toast.error('Failed to resolve contradiction');
      console.error(error);
    } finally {
      setIsResolving(false);
    }
  };

  return (
    <div
      className={`rounded-lg border p-4 mb-4 ${getSeverityColor()} animate-fade-in`}
    >
      <div className="flex items-center gap-2 mb-4">
        <svg
          className="w-5 h-5"
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path
            fillRule="evenodd"
            d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-sm font-semibold">Contradiction Detected ({severity})</span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
          <div className="text-xs text-slate-400 mb-2">Fact A</div>
          <p className="text-sm text-slate-100 mb-2">{factA.text}</p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">{new Date(factA.storedAt).toLocaleDateString()}</span>
            <TrustBadge score={factA.trustScore} showTooltip={false} size="sm" />
          </div>
        </div>

        <div className="bg-slate-900/50 rounded-lg p-3 border border-slate-700">
          <div className="text-xs text-slate-400 mb-2">Fact B</div>
          <p className="text-sm text-slate-100 mb-2">{factB.text}</p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">{new Date(factB.storedAt).toLocaleDateString()}</span>
            <TrustBadge score={factB.trustScore} showTooltip={false} size="sm" />
          </div>
        </div>
      </div>

      <div className="flex gap-2 justify-end">
        <button
          onClick={() => handleResolve('remove')}
          disabled={isResolving}
          className="px-3 py-2 text-xs rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 disabled:opacity-50 transition-colors"
        >
          Remove B
        </button>
        <button
          onClick={() => handleResolve('keep')}
          disabled={isResolving}
          className="px-3 py-2 text-xs rounded-lg bg-green-500/20 text-green-400 border border-green-500/40 hover:bg-green-500/30 disabled:opacity-50 transition-colors"
        >
          Keep A
        </button>
      </div>
    </div>
  );
}
