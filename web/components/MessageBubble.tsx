import { extractDataValues, formatRelativeTime } from "@/lib/extractDataValues";
import type { ChatMessage } from "@/types";

import DataValueCards from "./DataValueCards";

interface MessageBubbleProps {
  message: ChatMessage;
}

function renderTextWithMonoNumbers(text: string) {
  const parts = text.split(/(₹[\d,]+(?:\.\d+)?(?:\s*(?:Cr|Lakh|L))?|[\d.]+%)/g);

  return parts.map((part, index) => {
    const isNumeric = /^₹/.test(part) || /^[\d.]+%$/.test(part);
    if (isNumeric) {
      return (
        <span key={`${part}-${index}`} className="font-mono text-accent">
          {part}
        </span>
      );
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-2">
        <div className="max-w-[80%] rounded-2xl bg-accent px-4 py-3 text-sm text-black">
          {message.content}
        </div>
      </div>
    );
  }

  const dataValues = extractDataValues(message.content);

  return (
    <div className="flex justify-start px-4 py-2">
      <div className="max-w-[85%]">
        <p className="mb-1.5 font-display text-[10px] font-semibold uppercase tracking-[0.14em] text-accent">
          HDFC AI Assistant · {formatRelativeTime(message.timestamp)}
        </p>
        <div className="rounded-2xl bg-card px-4 py-3 text-sm text-white">
          <DataValueCards values={dataValues} />
          <p className="whitespace-pre-wrap leading-relaxed">
            {renderTextWithMonoNumbers(message.content)}
          </p>
          {message.citation_url ? (
            <a
              href={message.citation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 block break-all text-accent hover:underline"
            >
              {message.citation_url}
            </a>
          ) : null}
          {message.footer ? (
            <p className="mt-2 text-xs text-muted">{message.footer}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
