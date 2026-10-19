"use client";

import { Menu, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { Brand } from "./brand";
import { NavLinks } from "./nav-links";

// Below the md breakpoint the sidebar becomes a top bar with a slide-out menu.
export function MobileNav({ footer }: { footer: ReactNode }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="md:hidden">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-hairline bg-surface px-4 py-3">
        <Brand />
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={open}
          aria-controls="mobile-menu"
          className="rounded-md p-2 text-ink-2 hover:bg-surface-sunken"
        >
          <Menu size={20} aria-hidden />
          <span className="sr-only">Open menu</span>
        </button>
      </header>

      {open && (
        <div className="fixed inset-0 z-30">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/40"
          />
          <div
            id="mobile-menu"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col gap-6 bg-surface p-4 shadow-xl"
          >
            <div className="flex items-center justify-between">
              <Brand />
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md p-2 text-ink-2 hover:bg-surface-sunken"
              >
                <X size={20} aria-hidden />
                <span className="sr-only">Close menu</span>
              </button>
            </div>
            <nav aria-label="Main">
              <NavLinks onNavigate={() => setOpen(false)} />
            </nav>
            <div className="mt-auto border-t border-hairline pt-4">
              {footer}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
