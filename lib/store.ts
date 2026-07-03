import { create } from 'zustand';

interface ChatStore {
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  activeSessionId: null,
  setActiveSessionId: (id) => set({ activeSessionId: id }),
}));
