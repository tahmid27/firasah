"use client";

// Last resort when even the root layout fails; it replaces the whole page,
// so it brings its own <html> and plain styling.
export default function GlobalError({ reset }: { reset: () => void }) {
  return (
    <html lang="en">
      <body
        style={{
          fontFamily: "system-ui, sans-serif",
          display: "grid",
          placeItems: "center",
          minHeight: "100vh",
          margin: 0,
          textAlign: "center",
        }}
      >
        <div>
          <h1 style={{ fontSize: 20 }}>Something went wrong</h1>
          <p>Firasah couldn&apos;t load. Try again in a moment.</p>
          <button type="button" onClick={reset}>
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
