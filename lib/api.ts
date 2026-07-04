export const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const STORAGE_KEY = 'trustgraph.apiBaseUrl';

export function normalizeApiBaseUrl(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return DEFAULT_API_BASE_URL;
  return trimmed.replace(/\/$/, '');
}

export function getStoredApiBaseUrl() {
  if (typeof window === 'undefined') return DEFAULT_API_BASE_URL;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return normalizeApiBaseUrl(stored || DEFAULT_API_BASE_URL);
}

export function setStoredApiBaseUrl(value: string) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(STORAGE_KEY, normalizeApiBaseUrl(value));
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getStoredApiBaseUrl();
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
  });

  const text = await response.text();
  let data: unknown = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new Error((data as { detail?: string })?.detail || `Request failed: ${response.status}`);
  }

  return data as T;
}

export interface TrustScore {
  fact_id: string;
  score: number;
  recency_component: number;
  reinforcement_component: number;
  consistency_component: number;
  reasoning: string;
}

export interface FactRecord {
  fact: {
    fact_id: string;
    original_text: string;
    normalized_text: string;
    subject: string;
    predicate: string;
    object_value: string;
    timestamp: string;
    reinforcement_count: number;
    source: string;
    status: string;
    contradiction_group: string | null;
    contradiction_explanation: string | null;
  };
  trust_score: TrustScore;
}

export interface FactsResponse {
  facts: FactRecord[];
  total: number;
  active_count: number;
  contradicted_count: number;
  decayed_count: number;
}

export interface StatsResponse {
  activeFacts: number;
  contradictions: number;
  decayedFacts: number;
  totalMemorySize: number;
}

export interface ContradictionPair {
  contradiction_id: string;
  fact_a: Record<string, unknown>;
  fact_b: Record<string, unknown>;
  trust_a: number;
  trust_b: number;
  subject: string;
  predicate: string;
  explanation: string;
  resolved: boolean;
  winner_id: string | null;
}

export interface ContradictionsResponse {
  contradictions: ContradictionPair[];
  total: number;
}

export interface GraphResponse {
  nodes: Array<{
    id: string;
    label: string;
    node_type: string;
    trust: number;
    status: string | null;
    source: string;
    timestamp: string;
    reinforcement_count: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relation: string;
    weight: number;
  }>;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  query?: {
    contradictions?: Array<Record<string, unknown>>;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  getFacts: () => request<FactsResponse>('/api/facts'),
  getStats: () => request<StatsResponse>('/api/stats'),
  getContradictions: () => request<ContradictionsResponse>('/api/contradictions'),
  getGraph: () => request<GraphResponse>('/api/graph'),
  getChatSessions: () => request<{ sessions: ChatSessionSummary[] }>('/api/chat/sessions'),
  createChatSession: (title?: string) => request<ChatSession>('/api/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  }),
  sendChatMessage: (sessionId: string, content: string) => request<{ session: ChatSession; message: ChatMessage }>(`/api/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  }),
  reinforceFact: (factId: string) => request<{ reinforced: boolean; fact_id: string }>('/api/reinforce', {
    method: 'POST',
    body: JSON.stringify({ fact_id: factId }),
  }),
  resolveContradiction: (contradictionId: string, winnerId: string) => request<{ resolved: boolean }>('/api/resolve', {
    method: 'POST',
    body: JSON.stringify({ contradiction_id: contradictionId, winner_id: winnerId, action: 'keep_winner' }),
  }),
  resetMemory: () => request<{ reset: boolean }>('/api/reset', {
    method: 'POST',
  }),
};
