export default function DisclaimerBanner() {
  return (
    <div className="flex items-center justify-center gap-2 border-b border-white/5 bg-[#141414] px-4 py-1.5">
      <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent" aria-hidden="true" />
      <p className="font-display text-[10px] font-medium uppercase tracking-[0.12em] text-muted sm:text-[11px]">
        Facts-only mode: responses sourced from Groww · official HDFC AMC data
      </p>
    </div>
  );
}
