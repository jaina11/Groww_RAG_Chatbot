import type { ChatMessage, PostMessageResponse, Thread } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function createThread(): Promise<Thread> {
  return request<Thread>("/threads", { method: "POST" });
}

export async function listThreads(): Promise<Thread[]> {
  const data = await request<{ threads: Thread[] }>("/threads");
  return data.threads;
}

export async function getMessages(threadId: string): Promise<ChatMessage[]> {
  const data = await request<{ thread_id: string; messages: ChatMessage[] }>(
    `/threads/${threadId}/messages`,
  );
  return data.messages;
}

export async function postMessage(
  threadId: string,
  query: string,
): Promise<PostMessageResponse> {
  return request<PostMessageResponse>(`/threads/${threadId}/messages`, {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export async function loadThreadsWithPreviews(): Promise<Thread[]> {
  const threads = await listThreads();
  const enriched = await Promise.all(
    threads.map(async (thread) => {
      try {
        const messages = await getMessages(thread.id);
        const firstUser = messages.find((message) => message.role === "user");
        return {
          ...thread,
          preview: firstUser?.content ?? "New conversation",
        };
      } catch {
        return { ...thread, preview: "New conversation" };
      }
    }),
  );
  return enriched;
}
