'use client';

import { useRef, useState } from 'react';

interface ChatInputProps {
  onSubmit: (message: string) => Promise<void>;
  isLoading?: boolean;
}

export function ChatInput({ onSubmit, isLoading = false }: ChatInputProps) {
  const [value, setValue] = useState('');
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    // Auto-expand textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim() || isLoading) return;

    const message = value;
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      await onSubmit(message);
    } catch (error) {
      console.error('Error submitting message:', error);
      setValue(message); // Restore on error
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Check for composition events to handle CJK IMEs
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as any);
    }
  };

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Web Speech API SpeechRecognition is not supported in this browser. Try Chrome or Edge!");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setValue((prev) => (prev ? prev + ' ' + transcript : transcript));
      setIsListening(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    };

    recognition.onerror = () => {
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="Ask TrustGraph anything... (Enter to send, Shift+Enter for new line)"
        disabled={isLoading}
        className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 resize-none transition-colors disabled:opacity-50"
        rows={1}
        style={{ minHeight: '44px', maxHeight: '200px' }}
      />
      <button
        type="button"
        onClick={startListening}
        className={`flex-shrink-0 rounded-lg px-3 py-3 transition-colors flex items-center justify-center border border-slate-700 ${
          isListening
            ? 'bg-red-600 text-white animate-pulse'
            : 'bg-slate-800 text-slate-400 hover:text-slate-300 hover:bg-slate-700'
        }`}
        title="Voice Input (Speech to Text)"
      >
        🎙️
      </button>
      <button
        type="submit"
        disabled={!value.trim() || isLoading}
        className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white rounded-lg px-4 py-3 font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Sending...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5.951-1.429 5.951 1.429a1 1 0 001.169-1.409l-7-14z" />
            </svg>
            Send
          </>
        )}
      </button>
    </form>
  );
}
