"use client";

import type { ChatMessage } from "@/types";

import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";

const EXAMPLE_QUESTIONS = [
  "What is the expense ratio of HDFC Mid Cap Fund?",
  "What is the minimum SIP for HDFC ELSS Fund?",
  "What is the exit load of HDFC Large Cap Fund?",
];

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onExampleClick: (question: string) => void;
}

export default function ChatWindow({
  messages,
  isLoading,
  onExampleClick,
}: ChatWindowProps) {
  const showWelcome = messages.length === 0 && !isLoading;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        {showWelcome ? (
          <div className="flex h-full flex-col items-center justify-center px-6 text-center">
            <h2 className="max-w-xl font-display text-2xl font-semibold text-white">
              Ask me anything about HDFC Mutual Fund schemes
            </h2>
            <p className="mt-3 max-w-lg text-sm text-muted">
              I answer factual questions using indexed Groww scheme pages. I do
              not provide investment advice.
            </p>
            <div className="mt-8 flex max-w-2xl flex-wrap justify-center gap-3">
              {EXAMPLE_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => onExampleClick(question)}
                  className="rounded-full border border-accent/30 bg-card px-4 py-2 font-display text-sm text-white transition hover:border-accent hover:bg-accent/10"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl py-4">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {isLoading ? <TypingIndicator /> : null}
          </div>
        )}
      </div>
    </div>
  );
}
