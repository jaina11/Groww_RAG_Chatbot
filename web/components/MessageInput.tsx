"use client";

import { FormEvent, useState } from "react";

interface MessageInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

function AttachmentIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M14.5 6.5l-7 7a3 3 0 104.24 4.24l7.5-7.5a4.5 4.5 0 00-6.36-6.36l-8 8a6 6 0 108.49 8.49l7.75-7.75"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M5 12h14M13 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) {
      return;
    }
    onSend(trimmed);
    setValue("");
  }

  return (
    <form onSubmit={handleSubmit} className="bg-background px-4 pb-4">
      <div className="mx-auto flex max-w-3xl items-center gap-2 rounded-full border border-white/10 bg-card px-3 py-2">
        <button
          type="button"
          disabled={disabled}
          className="rounded-full p-2 text-muted transition hover:text-white disabled:opacity-50"
          aria-label="Attach file"
        >
          <AttachmentIcon />
        </button>

        <input
          type="text"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask about HDFC funds on Groww..."
          disabled={disabled}
          className="min-w-0 flex-1 bg-transparent px-1 py-2 text-sm text-white outline-none placeholder:text-muted disabled:cursor-not-allowed disabled:opacity-50"
        />

        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent text-black transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="Send message"
        >
          <SendIcon />
        </button>
      </div>
    </form>
  );
}
