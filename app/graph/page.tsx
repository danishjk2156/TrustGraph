'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { toast } from 'sonner';
import { api, type GraphResponse } from '@/lib/api';

export default function GraphPage() {
  const [graph, setGraph] = useState<GraphResponse | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .getGraph()
      .then((data) => setGraph(data))
      .catch((error) => toast.error(error instanceof Error ? error.message : 'Unable to load graph'));
  }, []);

  useEffect(() => {
    if (!graph || !containerRef.current) return;
    const { Network } = require('vis-network/standalone');
    const nodes = new window.DataSet(
      graph.nodes.map((node) => ({
        id: node.id,
        label: node.label,
        color: node.node_type === 'contradiction' ? '#f87171' : node.trust >= 0.7 ? '#34d399' : node.trust >= 0.4 ? '#fbbf24' : '#f87171',
        shape: node.node_type === 'contradiction' ? 'diamond' : 'dot',
        size: node.node_type === 'subject' ? 18 : 12,
      })),
    );
    const edges = new window.DataSet(
      graph.edges.map((edge) => ({
        from: edge.source,
        to: edge.target,
        arrows: 'to',
        label: edge.relation,
        color: edge.relation === 'contradicts' ? '#f87171' : '#60a5fa',
      })),
    );

    const data = { nodes, edges };
    const options = {
      interaction: { hover: true, dragNodes: true, dragView: true },
      physics: { stabilization: false },
      nodes: { font: { color: '#f8fafc' } },
      edges: { smooth: true },
    };

    const network = new Network(containerRef.current, data, options);
    return () => network.destroy();
  }, [graph]);

  const summary = useMemo(() => graph ? `${graph.nodes.length} nodes • ${graph.edges.length} edges` : 'Loading graph…', [graph]);

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4 shadow-2xl shadow-slate-950/40">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm text-sky-400">Knowledge graph</p>
            <h2 className="text-xl font-semibold">Linked memory network</h2>
          </div>
          <div className="rounded-full border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-300">{summary}</div>
        </div>
      </div>
      <div className="rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
        <div ref={containerRef} className="h-[70vh] rounded-2xl border border-slate-800 bg-slate-950/60" />
      </div>
    </div>
  );
}
