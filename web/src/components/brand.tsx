import { BrandMark } from "@/components/brand-mark";

export function Brand() {
  return (
    <div className="flex items-center gap-2 text-accent">
      <BrandMark className="size-8 shrink-0" />
      <span
        aria-label="Firasah"
        className="sb-hide font-heading text-lg font-bold tracking-tight"
      >
        <span aria-hidden>
          F
          <span className="relative">
            ı
            <span
              className="absolute left-1/2 top-[0.3em] size-[0.21em] -translate-x-1/2 rounded-full"
              style={{ background: "var(--series-2)" }}
            />
          </span>
          rasah
        </span>
      </span>
    </div>
  );
}
