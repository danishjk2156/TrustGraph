import { cn } from '@/lib/utils';

export function TrustBadge({ score }: { score: number }) {
  const level = score >= 0.7 ? 'High' : score >= 0.4 ? 'Medium' : 'Low';
  const tones = {
    High: 'border-emerald-500/40 bg-emerald-500/15 text-emerald-200',
    Medium: 'border-amber-500/40 bg-amber-500/15 text-amber-200',
    Low: 'border-rose-500/40 bg-rose-500/15 text-rose-200',
  } as const;

  return (
    <span className={cn('rounded-full border px-2.5 py-1 text-xs font-semibold', tones[level])}>
      {level} • {(score * 100).toFixed(0)}%
    </span>
  );
}
