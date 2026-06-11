export interface DataValue {
  label: string;
  value: string;
}

const LABELED_VALUE_PATTERN =
  /([A-Za-z][A-Za-z\s]{2,40}?)\s+(₹[\d,]+(?:\.\d+)?(?:\s*(?:Cr|Lakh|L))?|[\d.]+%)/g;

const STANDALONE_RUPEE_PATTERN = /₹[\d,]+(?:\.\d+)?(?:\s*(?:Cr|Lakh|L))?/g;
const STANDALONE_PERCENT_PATTERN = /[\d.]+%/g;

function normalizeLabel(label: string): string {
  return label.trim().replace(/\s+/g, " ");
}

export function extractDataValues(text: string): DataValue[] {
  const found: DataValue[] = [];
  const seen = new Set<string>();

  function add(label: string, value: string) {
    const key = `${label}|${value}`;
    if (seen.has(key)) {
      return;
    }
    seen.add(key);
    found.push({ label, value });
  }

  Array.from(text.matchAll(LABELED_VALUE_PATTERN)).forEach((match) => {
    add(normalizeLabel(match[1]), match[2].trim());
  });

  Array.from(text.matchAll(STANDALONE_RUPEE_PATTERN)).forEach((match) => {
    const value = match[0];
    if (!found.some((item) => item.value === value)) {
      add("Amount", value);
    }
  });

  Array.from(text.matchAll(STANDALONE_PERCENT_PATTERN)).forEach((match) => {
    const value = match[0];
    if (!found.some((item) => item.value === value)) {
      add("Rate", value);
    }
  });

  return found.slice(0, 4);
}

export function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);

  if (diffMinutes < 1) {
    return "Just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  return date.toLocaleDateString();
}
