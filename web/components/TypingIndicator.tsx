export default function TypingIndicator() {
  return (
    <div className="flex justify-start px-4 py-2">
      <div className="max-w-[85%]">
        <p className="mb-1.5 font-display text-[10px] font-semibold uppercase tracking-[0.14em] text-accent">
          HDFC AI Assistant · Just now
        </p>
        <div className="flex items-center gap-1 rounded-2xl bg-card px-4 py-3">
          <span className="typing-dot h-2 w-2 rounded-full bg-muted" />
          <span className="typing-dot h-2 w-2 rounded-full bg-muted" />
          <span className="typing-dot h-2 w-2 rounded-full bg-muted" />
        </div>
      </div>
    </div>
  );
}
