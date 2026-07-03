'use client';

import { useState, useRef, useEffect } from 'react';
import useSWR from 'swr';
import { ChatMessage } from '@/components/chat-message';
import { ChatInput } from '@/components/chat-input';
import { ContradictionCard } from '@/components/contradiction-card';
import {
  listContradictions,
  getChatSession,
  sendChatMessage,
  createChatSession,
  listChatSessions,
  uploadDocument,
} from '@/lib/api';
import { useChatStore } from '@/lib/store';
import { toast } from 'sonner';

export default function ChatPage() {
  const { activeSessionId, setActiveSessionId } = useChatStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch contradictions
  const { data: contradictions = [], mutate: mutateContradictions } = useSWR(
    'contradictions',
    listContradictions,
    { refreshInterval: 5000 }
  );

  // Fetch sessions list to initialize if needed
  const { data: sessions = [], mutate: mutateSessions } = useSWR(
    'chat-sessions',
    listChatSessions
  );

  // Fetch messages for the active session
  const { data: sessionData, mutate: mutateSession } = useSWR(
    activeSessionId ? ['chat-session', activeSessionId] : null,
    () => getChatSession(activeSessionId!)
  );

  // Initialize active session on mount
  useEffect(() => {
    const initSession = async () => {
      if (activeSessionId) return;

      if (sessions && sessions.length > 0) {
        // Set first session as active
        setActiveSessionId(sessions[0].id);
      } else {
        // Create a new session if none exist
        try {
          const newSession = await createChatSession();
          setActiveSessionId(newSession.id);
          mutateSessions();
        } catch (error) {
          console.error('Failed to initialize chat session:', error);
        }
      }
    };
    initSession();
  }, [sessions, activeSessionId, setActiveSessionId, mutateSessions]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sessionData?.messages]);

  const handleSendMessage = async (text: string) => {
    if (!activeSessionId) {
      toast.error('No active chat session');
      return;
    }

    setIsLoading(true);

    try {
      // Send chat message to backend (it will process and query memory)
      await sendChatMessage(activeSessionId, text);
      
      // Refresh current session messages & session list titles
      await Promise.all([
        mutateSession(),
        mutateSessions(),
        mutateContradictions(),
      ]);
    } catch (error) {
      toast.error('Failed to process message. Please check the backend connection.');
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    toast.loading(`Ingesting document: ${file.name}...`, { id: 'upload-toast' });

    try {
      await uploadDocument(file);
      toast.success(`"${file.name}" ingested. Self-improvement run complete!`, { id: 'upload-toast' });
      // Mutate contradictions and stats
      mutateContradictions();
    } catch (error) {
      toast.error(`Ingestion failed for "${file.name}"`, { id: 'upload-toast' });
      console.error('Upload error:', error);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const messages = sessionData?.messages || [];

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">
            {sessionData?.title || 'Chat with TrustGraph'}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Ask questions, upload documents, and track confidence levels in real time.
          </p>
        </div>
        <div>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".txt,.md,.json,.pdf"
            className="hidden"
            disabled={isUploading}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-semibold transition-all shadow-lg flex items-center gap-2"
          >
            {isUploading ? 'Ingesting...' : '📂 Ingest Document'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center mb-4">
                <span className="text-3xl text-white">T</span>
              </div>
              <h2 className="text-2xl font-bold text-slate-100 mb-2">Welcome to TrustGraph</h2>
              <p className="text-slate-400 max-w-md">
                Start a conversation to create and manage a trusted knowledge base. TrustGraph will
                store facts, track their reliability, and alert you to contradictions.
              </p>
            </div>
          ) : (
            messages.map((msg: any) => (
              <ChatMessage
                key={msg.id}
                role={msg.role}
                content={msg.content}
                trustScore={msg.query?.ranked_facts?.[0]?.trust_score?.score}
                timestamp={msg.created_at}
              />
            ))
          )}

          {isLoading && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0">
                <span className="text-white text-sm font-bold">T</span>
              </div>
              <div className="max-w-xl">
                <div className="rounded-xl px-4 py-3 bg-slate-800 border border-slate-700 rounded-tl-none">
                  <div className="flex gap-2 items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Contradictions Alert */}
        {contradictions && contradictions.length > 0 && (
          <div className="px-6 py-4 border-t border-slate-800 bg-slate-900/50 max-h-96 overflow-y-auto">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <h3 className="font-semibold text-slate-100">Active Contradictions ({contradictions.length})</h3>
            </div>
            <div className="space-y-3">
              {contradictions.slice(0, 2).map((contradiction, idx) => (
                <ContradictionCard
                  key={`contradiction-${contradiction.id}-${idx}`}
                  id={contradiction.id}
                  factA={contradiction.factA}
                  factB={contradiction.factB}
                  severity={contradiction.severity}
                  onResolved={() => mutateContradictions()}
                />
              ))}
              {contradictions.length > 2 && (
                <div className="text-xs text-slate-400 text-center py-2">
                  +{contradictions.length - 2} more contradiction{contradictions.length > 3 ? 's' : ''}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-slate-800 bg-slate-900/50 backdrop-blur-sm px-6 py-4">
          <ChatInput onSubmit={handleSendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
