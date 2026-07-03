'use client';

import { useState } from 'react';

interface TrustBadgeProps {
  score: number;
  showTooltip?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function TrustBadge({ score, showTooltip = true, size = 'md' }: TrustBadgeProps) {
  const [showDetails, setShowDetails] = useState(false);

  const getTrustLevel = (score: number): 'high' | 'medium' | 'low' => {
    if (score >= 0.7) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  };

  const getColors = (level: 'high' | 'medium' | 'low') => {
    switch (level) {
      case 'high':
        return 'bg-green-500/20 text-green-400 border-green-500/40';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/40';
      case 'low':
        return 'bg-red-500/20 text-red-400 border-red-500/40';
    }
  };

  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'px-2 py-1 text-xs';
      case 'md':
        return 'px-3 py-1.5 text-sm';
      case 'lg':
        return 'px-4 py-2 text-base';
    }
  };

  const level = getTrustLevel(score);
  const percentage = Math.round(score * 100);

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`border rounded-lg font-medium transition-all ${getColors(level)} ${getSizeClasses()}`}
        title={`Trust Score: ${percentage}%`}
      >
        {level === 'high' && '✓'} {level === 'medium' && '◐'} {level === 'low' && '✗'} {percentage}%
      </button>

      {showTooltip && showDetails && (
        <div className="absolute bottom-full mb-2 left-0 bg-slate-900 border border-slate-700 rounded-lg p-3 w-48 text-xs text-slate-100 z-50 shadow-lg">
          <div className="font-semibold mb-2">Trust Breakdown</div>
          <div className="space-y-1.5 text-slate-300">
            <div className="flex justify-between">
              <span>Recency:</span>
              <span className="text-slate-100">75%</span>
            </div>
            <div className="flex justify-between">
              <span>Reinforcement:</span>
              <span className="text-slate-100">60%</span>
            </div>
            <div className="flex justify-between">
              <span>Consistency:</span>
              <span className="text-slate-100">85%</span>
            </div>
            <div className="border-t border-slate-700 mt-2 pt-2 flex justify-between font-semibold">
              <span>Overall:</span>
              <span className="text-slate-100">{percentage}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
