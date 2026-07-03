import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Dynamically update baseURL from settings saved in localStorage
if (typeof window !== 'undefined') {
  api.interceptors.request.use((config) => {
    const savedUrl = localStorage.getItem('apiUrl');
    if (savedUrl) {
      config.baseURL = savedUrl;
    }
    return config;
  });
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  trustScore?: number;
  timestamp: Date;
}

export interface Fact {
  id: string;
  text: string;
  trustScore: number;
  storedAt: string;
  source?: string;
  reinforcementCount: number;
  isContradicted?: boolean;
}

export interface Contradiction {
  id: string;
  factA: Fact;
  factB: Fact;
  severity: 'low' | 'medium' | 'high';
  description: string;
}

export interface QueryResponse {
  response: string;
  facts: Fact[];
  webResults: Array<{
    title: string;
    url: string;
    snippet?: string;
  }>;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: 'fact' | 'subject' | 'contradiction';
    trustLevel: 'high' | 'medium' | 'low';
  }>;
  edges: Array<{
    from: string;
    to: string;
    label?: string;
  }>;
}

function factText(fact: any): string {
  return fact?.normalized_text || fact?.original_text || fact?.text || 'Untitled fact';
}

function mapFact(item: any): Fact {
  const fact = item?.fact || item;
  const trustScore = item?.trust_score?.score ?? fact?.trustScore ?? 0;

  return {
    id: fact?.fact_id || fact?.id || '',
    text: factText(fact),
    trustScore,
    storedAt: fact?.timestamp || fact?.storedAt || new Date().toISOString(),
    source: fact?.source,
    reinforcementCount: fact?.reinforcement_count ?? fact?.reinforcementCount ?? 0,
    isContradicted: (fact?.status || '').toLowerCase() === 'contradicted',
  };
}

function trustLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

// Store text in memory
export async function storeText(text: string): Promise<{ success: boolean; factId?: string }> {
  try {
    const response = await api.post('/api/store', { text, source: 'frontend' });
    const stored = response.data?.stored_facts?.[0];
    return { success: true, factId: stored?.fact_id };
  } catch (error) {
    console.error('Error storing text:', error);
    throw error;
  }
}

// Query memory
export async function queryMemory(query: string): Promise<QueryResponse> {
  try {
    const response = await api.post('/api/query', { query_text: query });
    const data = response.data;
    return {
      response: data.answer_text || 'No answer was returned.',
      facts: (data.ranked_facts || []).map(mapFact),
      webResults: data.web_results || [],
    };
  } catch (error) {
    console.error('Error querying memory:', error);
    throw error;
  }
}

// Get all facts
export async function listFacts(): Promise<Fact[]> {
  try {
    const response = await api.get('/api/facts');
    return (response.data.facts || []).map(mapFact);
  } catch (error) {
    console.error('Error listing facts:', error);
    throw error;
  }
}

// Get contradictions
export async function listContradictions(): Promise<Contradiction[]> {
  try {
    const response = await api.get('/api/contradictions');
    return (response.data.contradictions || []).map((item: any) => {
      const trustA = Number(item.trust_a || 0);
      const trustB = Number(item.trust_b || 0);
      const severity: 'low' | 'medium' | 'high' = Math.abs(trustA - trustB) < 0.2 ? 'high' : 'medium';
      return {
        id: item.contradiction_id,
        factA: mapFact({ fact: item.fact_a, trust_score: { score: trustA } }),
        factB: mapFact({ fact: item.fact_b, trust_score: { score: trustB } }),
        severity,
        description: item.explanation || '',
      };
    });
  } catch (error) {
    console.error('Error listing contradictions:', error);
    throw error;
  }
}

// Resolve a contradiction
export async function resolveFact(
  contradictionId: string,
  winnerId: string | null,
  action: 'keep_winner' | 'keep_both' = 'keep_winner'
): Promise<{ success: boolean }> {
  try {
    await api.post('/api/resolve', {
      contradiction_id: contradictionId,
      winner_id: winnerId,
      action,
    });
    return { success: true };
  } catch (error) {
    console.error('Error resolving fact:', error);
    throw error;
  }
}

// Reinforce a fact
export async function reinforceFact(factId: string): Promise<{ success: boolean; newScore: number }> {
  try {
    await api.post('/api/reinforce', { fact_id: factId });
    return { success: true, newScore: 0 };
  } catch (error) {
    console.error('Error reinforcing fact:', error);
    throw error;
  }
}

// Get knowledge graph
export async function getGraph(): Promise<GraphData> {
  try {
    const response = await api.get('/api/graph');
    return {
      nodes: (response.data.nodes || []).map((node: any) => ({
        id: node.id,
        label: node.label,
        type: node.node_type || node.type,
        trustLevel: trustLevel(Number(node.trust || 0)),
      })),
      edges: (response.data.edges || []).map((edge: any) => ({
        from: edge.source || edge.from,
        to: edge.target || edge.to,
        label: edge.relation || edge.label,
      })),
    };
  } catch (error) {
    console.error('Error getting graph:', error);
    throw error;
  }
}

// Get memory stats
export async function getStats(): Promise<{
  activeFacts: number;
  contradictions: number;
  decayedFacts: number;
  totalMemorySize: number;
}> {
  try {
    const response = await api.get('/api/stats');
    return response.data;
  } catch (error) {
    console.error('Error getting stats:', error);
    throw error;
  }
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
    query?: any;
  }>;
}

export async function createChatSession(title?: string): Promise<ChatSession> {
  try {
    const response = await api.post('/api/chat/sessions', { title });
    return response.data;
  } catch (error) {
    console.error('Error creating chat session:', error);
    throw error;
  }
}

export async function listChatSessions(): Promise<ChatSession[]> {
  try {
    const response = await api.get('/api/chat/sessions');
    return response.data.sessions || [];
  } catch (error) {
    console.error('Error listing chat sessions:', error);
    throw error;
  }
}

export async function getChatSession(sessionId: string): Promise<ChatSession> {
  try {
    const response = await api.get(`/api/chat/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting chat session:', error);
    throw error;
  }
}

export async function sendChatMessage(
  sessionId: string,
  content: string
): Promise<{ session: ChatSession; message: any }> {
  try {
    const response = await api.post(`/api/chat/sessions/${sessionId}/messages`, {
      content,
      feedback_influence: 0.5,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
}

export async function uploadDocument(file: File): Promise<any> {
  try {
    const reader = new FileReader();
    const content = await new Promise<string>((resolve, reject) => {
      reader.onload = (e) => resolve(e.target?.result as string || '');
      reader.onerror = (err) => reject(err);
      reader.readAsText(file);
    });

    const response = await api.post(`/api/upload?filename=${encodeURIComponent(file.name)}`, content, {
      headers: {
        'Content-Type': 'text/plain',
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error uploading document:', error);
    throw error;
  }
}

export default api;
