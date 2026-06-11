"use client";

const SUGGESTIONS = [
  "What are the top holdings?",
  "Who is the fund manager?",
  "What is the expense ratio?",
];

interface SuggestionChipsProps {
  onChipClick: (question: string) => void;
  disabled?: boolean;
}

export default function SuggestionChips({
  onChipClick,
  disabled = false,
}: SuggestionChipsProps) {
  return (
    <div className="border-t border-white/5 bg-background px-4 pb-2 pt-3">
      <div className="mx-auto flex max-w-3xl flex-wrap gap-2">
        {SUGGESTIONS.map((suggestion) => (
          <button
            key={suggestion}
            type="button"
            disabled={disabled}
            onClick={() => onChipClick(suggestion)}
            className="rounded-full border border-white/10 bg-card px-3 py-1.5 font-display text-xs text-white transition hover:border-accent/50 hover:bg-accent/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}
