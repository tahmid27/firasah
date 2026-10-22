// Sidebar state: expanded (default) or collapsed to an icon rail. Collapsing
// also switches the page to the roomier "spacious" spacing (see globals.css).
// Stored per browser like the theme, since it is a display preference.
export type SidebarState = "expanded" | "collapsed";

export const SIDEBAR_STORAGE_KEY = "firasah-sidebar";

// Runs in <head> before first paint, same reason as the theme script.
export const SIDEBAR_BOOT_SCRIPT = `try{if(localStorage.getItem("${SIDEBAR_STORAGE_KEY}")==="collapsed")document.documentElement.dataset.sidebar="collapsed"}catch(e){}`;

export function applySidebar(state: SidebarState) {
  const root = document.documentElement;
  if (state === "expanded") delete root.dataset.sidebar;
  else root.dataset.sidebar = "collapsed";
  try {
    if (state === "expanded") localStorage.removeItem(SIDEBAR_STORAGE_KEY);
    else localStorage.setItem(SIDEBAR_STORAGE_KEY, "collapsed");
  } catch {
    // Storage blocked (private mode): the choice still applies for this page.
  }
}

export function readSidebar(): SidebarState {
  return document.documentElement.dataset.sidebar === "collapsed"
    ? "collapsed"
    : "expanded";
}
