import {
  Activity,
  HandCoins,
  LayoutDashboard,
  Mail,
  Megaphone,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/fundraising", label: "Fundraising", icon: HandCoins },
  { href: "/social", label: "Social", icon: Users },
  { href: "/email", label: "Email", icon: Mail },
  { href: "/appeals", label: "Appeals", icon: Megaphone },
  { href: "/data-health", label: "Data health", icon: Activity },
];

export function isActive(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
