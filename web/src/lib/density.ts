// Layout density: how much space and text size the dashboard uses. Stored per
// browser like the theme, since it is a display preference.
export type Density = "compact" | "normal" | "spacious";

export const DENSITY_STORAGE_KEY = "firasah-density";

// Runs in <head> before first paint, same reason as the theme script.
export const DENSITY_BOOT_SCRIPT = `try{var d=localStorage.getItem("${DENSITY_STORAGE_KEY}");if(d==="compact"||d==="spacious")document.documentElement.dataset.density=d}catch(e){}`;

export function applyDensity(density: Density) {
  const root = document.documentElement;
  if (density === "normal") delete root.dataset.density;
  else root.dataset.density = density;
  try {
    if (density === "normal") localStorage.removeItem(DENSITY_STORAGE_KEY);
    else localStorage.setItem(DENSITY_STORAGE_KEY, density);
  } catch {
    // Storage blocked (private mode): the choice still applies for this page.
  }
}

export function readDensity(): Density {
  const value = document.documentElement.dataset.density;
  return value === "compact" || value === "spacious" ? value : "normal";
}
