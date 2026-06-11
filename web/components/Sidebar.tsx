"use client";

import type { Thread } from "@/types";

interface SidebarProps {
  threads: Thread[];
  activeThreadId: string | null;
  isOpen: boolean;
  onNewChat: () => void;
  onSelectThread: (threadId: string) => void;
}

export default function Sidebar({
  threads,
  activeThreadId,
  isOpen,
  onNewChat,
  onSelectThread,
}: SidebarProps) {
  return (
    <aside
      className={`${
        isOpen ? "flex" : "hidden"
      } h-full w-72 shrink-0 flex-col border-r border-white/10 bg-sidebar lg:flex`}
    >
      <div className="border-b border-white/10 px-4 py-5">
        <h1 className="font-display text-lg font-semibold text-white">Groww FAQ</h1>
        <p className="mt-1 font-display text-xs text-muted">HDFC Mutual Funds</p>
      </div>

      <div className="p-4">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full rounded-full bg-accent px-4 py-3 font-display text-sm font-medium text-black transition hover:opacity-90"
        >
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {threads.length === 0 ? (
          <p className="px-2 text-sm text-muted">No conversations yet</p>
        ) : (
          <ul className="space-y-1">
            {threads.map((thread) => {
              const isActive = thread.id === activeThreadId;
              return (
                <li key={thread.id}>
                  <button
                    type="button"
                    onClick={() => onSelectThread(thread.id)}
                    className={`w-full rounded-xl px-3 py-3 text-left transition ${
                      isActive
                        ? "bg-card text-white"
                        : "text-muted hover:bg-card/60 hover:text-white"
                    }`}
                  >
                    <p className="line-clamp-2 text-sm">{thread.preview ?? "New conversation"}</p>
                    <p className="mt-1 text-xs opacity-60">
                      {new Date(thread.created_at).toLocaleDateString()}
                    </p>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
