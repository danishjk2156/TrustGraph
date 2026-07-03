'use client';

import { useEffect, useRef } from 'react';
import useSWR from 'swr';
import { getGraph } from '@/lib/api';
import { DataSet, Network } from 'vis-network/standalone';

export default function GraphPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<any>(null);

  const { data: graphData, isLoading } = useSWR('graph', getGraph, { refreshInterval: 10000 });

  useEffect(() => {
    if (!containerRef.current || !graphData) return;

    const nodes = new DataSet<any>(
      graphData.nodes.map((node) => ({
        id: node.id,
        label: node.label.length > 30 ? node.label.substring(0, 30) + '...' : node.label,
        title: node.label,
        color:
          node.trustLevel === 'high'
            ? '#86efac'
            : node.trustLevel === 'medium'
              ? '#fde68a'
              : '#fca5a5',
        shape: node.type === 'contradiction' ? 'diamond' : 'dot',
        font: { color: '#f1f5f9' },
      }))
    );

    const edges = new DataSet<any>(
      graphData.edges.map((edge) => ({
        from: edge.from,
        to: edge.to,
        label: edge.label,
        color: { color: '#475569' },
        arrows: 'to',
      }))
    );

    const options = {
      physics: {
        enabled: true,
        barnesHut: {
          gravitationalConstant: -26000,
          centralGravity: 0.3,
          springLength: 200,
        },
      },
      interaction: {
        navigationButtons: true,
        keyboard: true,
        hover: true,
      },
      nodes: {
        font: {
          size: 16,
          face: 'Segoe UI, Roboto, system-ui',
        },
        borderWidth: 2,
        borderWidthSelected: 4,
      },
      edges: {
        smooth: {
          type: 'continuous',
        },
        font: {
          size: 12,
          face: 'Segoe UI, Roboto, system-ui',
          color: '#cbd5e1',
        },
      },
    };

    if (networkRef.current) {
      networkRef.current.destroy();
    }

    const network = new Network(
      containerRef.current,
      { nodes, edges } as any,
      options as any
    );

    networkRef.current = network;

    network.on('click', (params: any) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = graphData.nodes.find((n) => n.id === nodeId);
        if (node) {
          console.log('Clicked node:', node);
        }
      }
    });

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
      }
    };
  }, [graphData]);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 py-4 z-10">
        <h1 className="text-2xl font-bold text-slate-100">Knowledge Graph</h1>
        <p className="text-sm text-slate-400 mt-1">
          Visual representation of facts, subjects, and their relationships
        </p>
      </div>

      {/* Graph Container */}
      <div className="flex-1 relative overflow-hidden">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-950/50 z-20">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-2 border-blue-500 border-t-transparent mx-auto mb-4" />
              <p className="text-slate-400">Loading graph...</p>
            </div>
          </div>
        )}

        <div
          ref={containerRef}
          className="w-full h-full bg-gradient-to-br from-slate-900 to-slate-950"
        />

        {/* Legend */}
        <div className="absolute bottom-6 left-6 bg-slate-900/80 backdrop-blur-sm border border-slate-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-slate-100 mb-3">Legend</h3>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span className="text-slate-300">High Trust Facts</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-300" />
              <span className="text-slate-300">Medium Trust Facts</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <span className="text-slate-300">Low Trust Facts</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 rotate-45 border-2 border-blue-400 bg-blue-400/10" />
              <span className="text-slate-300">Contradiction</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
