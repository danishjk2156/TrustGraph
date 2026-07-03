'use client';

import { TrustBadge } from './trust-badge';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  trustScore?: number;
  timestamp?: Date;
}

export function ChatMessage({ role, content, trustScore, timestamp }: ChatMessageProps) {
  const isUser = role === 'user';

  const handleSpeak = () => {
    if (!('speechSynthesis' in window)) {
      alert('Text-to-Speech is not supported in this browser.');
      return;
    }
    // Cancel any ongoing speech first
    window.speechSynthesis.cancel();

    const cleanContent = content.replace(/(?:https?|ftp):\/\/[\n\S]+/g, ''); // strip links for reading
    const utterance = new SpeechSynthesisUtterance(cleanContent);
    utterance.lang = 'en-US';
    window.speechSynthesis.speak(utterance);
  };

  return (
    <div className={`flex gap-4 mb-4 animate-fade-in ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-sm font-bold">T</span>
        </div>
      )}

      <div className={`max-w-xl ${isUser ? 'order-2' : ''}`}>
        <div
          className={`rounded-xl px-4 py-3 ${
            isUser
              ? 'bg-blue-600 text-white rounded-tr-none'
              : 'bg-slate-800 text-slate-100 border border-slate-700 rounded-tl-none'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
        </div>

        <div className={`flex items-center gap-2 mt-2 text-xs text-slate-400 ${isUser ? 'justify-end' : 'justify-start'}`}>
          {!isUser && trustScore !== undefined && (
            <div className="scale-75 origin-left">
              <TrustBadge score={trustScore} showTooltip={false} size="sm" />
            </div>
          )}
          {timestamp && <span>{timestamp instanceof Date ? timestamp.toLocaleTimeString() : new Date(timestamp).toLocaleTimeString()}</span>}
          {!isUser && (
            <button
              onClick={handleSpeak}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-slate-200 transition-colors ml-1"
              title="Read aloud"
            >
              🔊
            </button>
          )}
        </div>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center flex-shrink-0">
          <span className="text-white text-sm font-bold">U</span>
        </div>
      )}
    </div>
  );
}
