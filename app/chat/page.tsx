'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { SendHorizonal, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { api, type ChatMessage, type ChatSession, type ChatSessionSummary } from '@/lib/api';
import { TrustBadge } from '@/components/trust-badge';
import { cn } from '@/lib/utils';

export default function ChatPage() {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [draft, setDraft] = useState('');
  const [loading, setLoading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const loadSessions = async () => {
    try {
      const response = await api.getChatSessions();
      setSessions(response.sessions);
      if (!activeSessionId && response.sessions[0]) {
        setActiveSessionId(response.sessions[0].id);
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to load chat history');
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (!activeSessionId) return;
    const session = sessions.find((item) => item.id === activeSessionId);
    if (!session) return;
    const loadSession = async () => {
      try {
        const response = await fetch(`${typeof window !== 'undefined' ? window.localStorage.getItem('trustgraph.apiBaseUrl') || 'http://localhost:8000' : 'http://localhost:8000'}/api/chat/sessions/${activeSessionId}`);
        const data = (await response.json()) as ChatSession;
        setActiveSession(data);
      } catch {
        setActiveSession(null);
      }
    };
    loadSession();
  }, [activeSessionId, sessions]);

  const createNewSession = async () => {
    try {
      const session = await api.createChatSession('New Chat');
      setSessions((prev) => [session, ...prev]);
      setActiveSessionId(session.id);
      setActiveSession(session);
      setDraft('');
      toast.success('Started a new chat');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to create chat');
    }
  };

  const sendMessage = async () => {
    const content = draft.trim();
    if (!content) return;
    if (!activeSessionId) {
      await createNewSession();
    }

    setLoading(true);
    try {
      const sessionId = activeSessionId ?? (await api.createChatSession('New Chat')).id;
      const response = await api.sendChatMessage(sessionId, content);
      setActiveSession(response.session);
      setSessions((prev) => prev.map((item) => (item.id === sessionId ? { ...item, title: response.session.title, updated_at: response.session.updated_at, message_count: response.session.messages.length } : item)));
      setDraft('');
      toast.success('Message sent');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Unable to send message');
    } finally {
      setLoading(false);
    }
  };

  const currentMessages = activeSession?.messages ?? [];
  const canSend = draft.trim().length > 0 && !loading;

  return (
    <div className="mx-auto flex h-[calc(100vh-3rem)] max-w-6xl flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-4 shadow-2xl shadow-slate-950/40">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
        <div>
          <p className="text-sm text-sky-400">Conversational memory</p>
          <h2 className="text-xl font-semibold">Talk with TrustGraph</h2>
        </div>
        <button onClick={createNewSession} className="rounded-full border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200">
          New Chat
        </button>
      </div>

      <div className="grid flex-1 gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="rounded-2xl border border-slate-800 bg-slate-950/40 p-3">
          <p className="mb-3 text-sm font-semibold text-slate-300">Recent chats</p>
          <div className="space-y-2">
            {sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={cn('w-full rounded-xl border px-3 py-3 text-left', activeSessionId === session.id ? 'border-sky-500/40 bg-sky-500/10' : 'border-transparent bg-slate-900/60 hover:border-slate-700')}
              >
                <div className="truncate text-sm font-medium text-slate-100">{session.title}</div>
                <div className="mt-1 text-xs text-slate-400">{session.message_count} messages</div>
              </button>
            ))}
          </div>
        </aside>

        <section className="flex min-h-0 flex-col rounded-2xl border border-slate-800 bg-slate-950/40">
          <div className="flex-1 space-y-3 overflow-auto p-4">
            {currentMessages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center text-slate-400">
                <Sparkles className="mb-3 h-8 w-8 text-sky-400" />
                <h3 className="text-lg font-semibold text-slate-200">Start a conversation</h3>
                <p className="mt-2 max-w-md text-sm">Ask a question, share a memory, or test the backend connection.</p>
              </div>
            ) : (
              currentMessages.map((message) => (
                <div key={message.id} className={cn('flex', message.role === 'user' ? 'justify-end' : 'justify-start')}>
                  <div className={cn('max-w-[80%] rounded-2xl border px-4 py-3', message.role === 'user' ? 'border-sky-500/30 bg-sky-500/10' : 'border-slate-700 bg-slate-900/80')}>
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <span className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-400">{message.role === 'user' ? 'You' : 'TrustGraph'}</span>
                      {message.role === 'assistant' ? <TrustBadge score={0.65} /> : null}
                    </div>
                    <p className="whitespace-pre-wrap text-sm leading-7 text-slate-100">{message.content}</p>
                  </div>
                </div>
              ))
            )}
            {loading ? (
              <div className="flex items-center gap-3 rounded-2xl border border-slate-700 bg-slate-900/80 px-4 py-3 text-sm text-slate-300">
                <Loader2 className="h-4 w-4 animate-spin" />
                Thinking and querying memory…
              </div>
            ) : null}
          </div>

          <div className="border-t border-slate-800 p-4">
            <div className="flex items-end gap-3 rounded-2xl border border-slate-700 bg-slate-900/80 p-3">
              <textarea
                ref={textareaRef}
                rows={1}
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    void sendMessage();
                  }
                }}
                placeholder="Ask about your memory, share a fact, or test a contradiction"
                className="min-h-[44px] flex-1 resize-none border-none bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
              />
              <button disabled={!canSend} onClick={() => void sendMessage()} className="rounded-full bg-sky-500 p-3 text-slate-950 transition enabled:hover:bg-sky-400 disabled:cursor-not-allowed disabled:opacity-50">
                <SendHorizonal className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
