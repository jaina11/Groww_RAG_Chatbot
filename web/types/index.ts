export interface Thread {
  id: string;
  created_at: string;
  preview?: string;
}

export interface ChatMessage {
  id: string;
  thread_id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citation_url?: string | null;
  footer?: string;
}

export interface PostMessageResponse {
  answer: string;
  citation_url: string | null;
  footer: string;
  thread_id: string;
  refused: boolean;
}
