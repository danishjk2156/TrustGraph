'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import useSWR from 'swr';
import { getStats, createChatSession, listChatSessions } from '@/lib/api';
import { useChatStore } from '@/lib/store';
import { toast } from 'sonner';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { data: stats } = useSWR('stats', getStats, { refreshInterval: 5000 });
  const { activeSessionId, setActiveSessionId } = useChatStore();

  const { data: sessions = [], mutate: mutateSessions } = useSWR(
    'chat-sessions',
    listChatSessions,
    { refreshInterval: 5000 }
  );

  const navItems = [
    { href: '/chat', label: 'Chat', icon: '💬' },
    { href: '/facts', label: 'Facts', icon: '📚' },
    { href: '/graph', label: 'Graph', icon: '🔗' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  const isActive = (href: string) => pathname === href || pathname.startsWith(href + '/');

  const handleNewChat = async () => {
    try {
      const newSession = await createChatSession();
      setActiveSessionId(newSession.id);
      mutateSessions();
      router.push('/chat');
      toast.success('New chat session started!');
    } catch (error) {
      toast.error('Failed to create new chat session');
    }
  };

  const handleSelectSession = (id: string) => {
    setActiveSessionId(id);
    router.push('/chat');
  };

  return (
    <div
      className={`${
        isCollapsed ? 'w-20' : 'w-64'
      } bg-slate-900 border-r border-slate-800 flex flex-col transition-all duration-300 h-screen sticky top-0`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">T</span>
            </div>
            <span className="font-semibold text-slate-100">TrustGraph</span>
          </div>
        )}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 hover:bg-slate-800 rounded-lg transition-colors"
          aria-label="Toggle sidebar"
        >
          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="p-3 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
              isActive(item.href)
                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/40'
                : 'text-slate-400 hover:text-slate-300 hover:bg-slate-800/50'
            }`}
            title={isCollapsed ? item.label : undefined}
          >
            <span className="text-lg flex-shrink-0">{item.icon}</span>
            {!isCollapsed && <span className="text-sm font-medium">{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* Chat Sessions History */}
      {!isCollapsed && (
        <div className="flex-1 border-t border-slate-800 p-3 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">Chats</span>
            <button
              onClick={handleNewChat}
              className="px-2 py-0.5 hover:bg-slate-800 text-blue-400 hover:text-blue-300 rounded text-xs flex items-center gap-1 font-medium transition-colors"
            >
              ➕ New
            </button>
          </div>
          <div className="flex-1 overflow-y-auto space-y-1 pr-1">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs truncate transition-all ${
                  activeSessionId === session.id
                    ? 'bg-slate-800 text-slate-100 font-medium border-l-2 border-blue-500 pl-2'
                    : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-300'
                }`}
              >
                💬 {session.title || 'New Chat'}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Stats */}
      {!isCollapsed && stats && (
        <div className="p-4 border-t border-slate-800 space-y-3">
          <div className="bg-slate-800/50 rounded-lg p-3">
            <div className="text-xs text-slate-400 mb-1">Memory Stats</div>
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Active Facts</span>
                <span className="text-slate-100 font-semibold">{stats.activeFacts}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Contradictions</span>
                <span className="text-red-400 font-semibold">{stats.contradictions}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Decayed</span>
                <span className="text-yellow-400 font-semibold">{stats.decayedFacts}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
