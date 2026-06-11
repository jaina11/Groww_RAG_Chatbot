"use client";

interface HeaderProps {
  onMenuClick: () => void;
}

function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M4 7h16M4 12h16M4 17h16"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}

function InfoIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path d="M12 11v5M12 8h.01" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

export default function Header({ onMenuClick }: HeaderProps) {
  return (
    <header className="flex items-center justify-between border-b border-white/10 bg-background px-4 py-3">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-lg p-2 text-muted transition hover:bg-card hover:text-white"
        aria-label="Toggle sidebar"
      >
        <MenuIcon />
      </button>

      <div className="flex-1 px-4 text-center">
        <h1 className="font-display text-base font-semibold tracking-tight text-white sm:text-lg">
          Groww · HDFC Fund FAQ
        </h1>
        <p className="mt-0.5 font-display text-[11px] text-muted sm:text-xs">
          Powered by official HDFC AMC data via Groww
        </p>
      </div>

      <button
        type="button"
        className="rounded-lg p-2 text-muted transition hover:bg-card hover:text-white"
        aria-label="Information"
      >
        <InfoIcon />
      </button>
    </header>
  );
}
