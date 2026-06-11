"use client";

import { useCallback, useEffect, useState } from "react";

import ChatWindow from "@/components/ChatWindow";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import Header from "@/components/Header";
import MessageInput from "@/components/MessageInput";
import Sidebar from "@/components/Sidebar";
import SuggestionChips from "@/components/SuggestionChips";
import {
  createThread,
  getMessages,
  loadThreadsWithPreviews,
  postMessage,
} from "@/lib/api";
import { enrichAssistantMessage } from "@/lib/parseMessage";
import type { ChatMessage, Thread } from "@/types";

function toAssistantMessage(
  threadId: string,
  response: {
    answer: string;
    citation_url: string | null;
    footer: string;
  },
): ChatMessage {
  return {
    id: `assistant-${Date.now()}`,
    thread_id: threadId,
    role: "assistant",
    content: response.answer,
    timestamp: new Date().toISOString(),
    citation_url: response.citation_url,
    footer: response.footer,
  };
}

export default function HomePage() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const refreshThreads = useCallback(async () => {
    const nextThreads = await loadThreadsWithPreviews();
    setThreads(nextThreads);
  }, []);

  useEffect(() => {
    refreshThreads().catch(() => {
      setError("Unable to connect to the API. Is the backend running on port 8000?");
    });
  }, [refreshThreads]);

  async function handleNewChat() {
    setError(null);
    const thread = await createThread();
    setThreads((current) => [
      { ...thread, preview: "New conversation" },
      ...current.filter((item) => item.id !== thread.id),
    ]);
    setActiveThreadId(thread.id);
    setMessages([]);
  }

  async function handleSelectThread(threadId: string) {
    setError(null);
    setActiveThreadId(threadId);
    setIsLoading(true);
    try {
      const history = await getMessages(threadId);
      setMessages(history.map((message) => enrichAssistantMessage(message)));
    } catch {
      setError("Failed to load conversation history.");
      setMessages([]);
    } finally {
      setIsLoading(false);
    }
  }

  async function ensureThread(): Promise<string> {
    if (activeThreadId) {
      return activeThreadId;
    }
    const thread = await createThread();
    setThreads((current) => [
      { ...thread, preview: "New conversation" },
      ...current,
    ]);
    setActiveThreadId(thread.id);
    return thread.id;
  }

  async function handleSend(query: string) {
    setError(null);
    setIsLoading(true);

    const threadId = await ensureThread();
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      thread_id: threadId,
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((current) => [...current, userMessage]);
    setThreads((current) =>
      current.map((thread) =>
        thread.id === threadId
          ? { ...thread, preview: query }
          : thread,
      ),
    );

    try {
      const response = await postMessage(threadId, query);
      const assistantMessage = toAssistantMessage(threadId, response);
      setMessages((current) => [...current, assistantMessage]);
      await refreshThreads();
    } catch {
      setError("Failed to send your message. Please try again.");
      setMessages((current) => current.filter((message) => message.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      <Header onMenuClick={() => setSidebarOpen((open) => !open)} />
      <DisclaimerBanner />
      {error ? (
        <div className="border-b border-red-500/30 bg-red-500/10 px-4 py-2 text-center text-sm text-red-300">
          {error}
        </div>
      ) : null}
      <div className="flex min-h-0 flex-1">
        <Sidebar
          threads={threads}
          activeThreadId={activeThreadId}
          isOpen={sidebarOpen}
          onNewChat={() => {
            handleNewChat().catch(() => {
              setError("Failed to create a new chat.");
            });
          }}
          onSelectThread={(threadId) => {
            setSidebarOpen(false);
            handleSelectThread(threadId).catch(() => undefined);
          }}
        />
        <main className="flex min-w-0 flex-1 flex-col">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            onExampleClick={(question) => {
              handleSend(question).catch(() => undefined);
            }}
          />
          <SuggestionChips
            onChipClick={(question) => {
              handleSend(question).catch(() => undefined);
            }}
            disabled={isLoading}
          />
          <MessageInput
            onSend={(message) => {
              handleSend(message).catch(() => undefined);
            }}
            disabled={isLoading}
          />
        </main>
      </div>
    </div>
  );
}
