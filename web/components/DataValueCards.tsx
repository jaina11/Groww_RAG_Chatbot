import type { DataValue } from "@/lib/extractDataValues";

interface DataValueCardsProps {
  values: DataValue[];
}

const LABEL_ALIASES: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /expense\s+ratio/i, label: "EXPENSE RATIO" },
  { pattern: /min(?:imum)?(?:\s+\w+){0,2}\s+sip/i, label: "MINIMUM SIP" },
  { pattern: /exit\s+load/i, label: "EXIT LOAD" },
  { pattern: /assets?\s+under\s+management|\baum\b/i, label: "AUM" },
  { pattern: /\bnav\b/i, label: "NAV" },
  { pattern: /lock[\s-]?in/i, label: "LOCK-IN" },
  { pattern: /benchmark/i, label: "BENCHMARK" },
  { pattern: /riskometer/i, label: "RISKOMETER" },
];

const STOP_WORDS = new Set([
  "a",
  "an",
  "the",
  "is",
  "are",
  "was",
  "were",
  "be",
  "been",
  "being",
  "has",
  "have",
  "had",
  "its",
  "it",
  "this",
  "that",
  "for",
  "of",
  "at",
  "with",
  "from",
  "if",
  "within",
  "one",
  "year",
  "years",
  "fund",
  "scheme",
  "currently",
  "approximately",
  "about",
  "around",
  "stands",
  "amount",
  "redeemed",
  "redemption",
]);

function formatCardLabel(rawLabel: string): string {
  const trimmed = rawLabel.trim().replace(/\s+/g, " ");

  for (const { pattern, label } of LABEL_ALIASES) {
    if (pattern.test(trimmed)) {
      return label;
    }
  }

  if (/^amount$/i.test(trimmed)) {
    return "AMOUNT";
  }
  if (/^rate$/i.test(trimmed)) {
    return "RATE";
  }

  const words = trimmed
    .split(/\s+/)
    .map((word) => word.replace(/[^A-Za-z-]/g, ""))
    .filter((word) => word.length > 0 && !STOP_WORDS.has(word.toLowerCase()));

  if (words.length === 0) {
    return trimmed.toUpperCase();
  }

  return words.slice(-3).join(" ").toUpperCase();
}

export default function DataValueCards({ values }: DataValueCardsProps) {
  if (values.length === 0) {
    return null;
  }

  return (
    <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
      {values.map((item) => (
        <div
          key={`${item.label}-${item.value}`}
          className="rounded-lg bg-[#1e1e1e] px-3 py-2"
        >
          <p className="font-display text-[10px] uppercase tracking-wide text-muted">
            {formatCardLabel(item.label)}
          </p>
          <p className="font-mono text-sm font-medium text-accent">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
