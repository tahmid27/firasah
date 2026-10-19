// Light/dark choice: "system" follows the OS. Stored per browser, which is fine
// for a display preference (nothing else depends on it).
export type Theme = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "firasah-theme";

// Runs in <head> before the page paints, so a saved choice never flashes the
// other theme first. Kept tiny and dependency-free on purpose.
export const THEME_BOOT_SCRIPT = `try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === "system") delete root.dataset.theme;
  else root.dataset.theme = theme;
  try {
    if (theme === "system") localStorage.removeItem(THEME_STORAGE_KEY);
    else localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Storage blocked (private mode): the choice still applies for this page.
  }
}

export function readTheme(): Theme {
  const value = document.documentElement.dataset.theme;
  return value === "light" || value === "dark" ? value : "system";
}
