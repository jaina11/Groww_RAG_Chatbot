import type { ChatMessage } from "@/types";

const FOOTER_PREFIX = "Last updated from sources:";
const URL_PATTERN = /https?:\/\/[^\s)>"]+/g;

export function enrichAssistantMessage(message: ChatMessage): ChatMessage {
  if (message.role !== "assistant") {
    return message;
  }

  let footer = "";
  let citationUrl: string | null = null;
  const bodyLines: string[] = [];

  for (const line of message.content.split("\n")) {
    const stripped = line.trim();
    if (!stripped) {
      continue;
    }
    if (stripped.toLowerCase().startsWith(FOOTER_PREFIX.toLowerCase())) {
      footer = stripped;
      continue;
    }
    const urlMatch = stripped.match(URL_PATTERN);
    if (urlMatch && stripped === urlMatch[0]) {
      citationUrl = urlMatch[0];
      continue;
    }
    bodyLines.push(stripped);
  }

  return {
    ...message,
    content: bodyLines.join("\n").trim() || message.content,
    citation_url: citationUrl,
    footer,
  };
}
