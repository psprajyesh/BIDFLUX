import {
  BarChart3,
  FileSearch,
  FolderOpen,
  LayoutDashboard,
  Link2,
  Scale,
  ScrollText,
  Settings,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

/**
 * The app-wide navigation, shared by the desktop sidebar and the mobile menu so
 * the two can never drift apart.
 */
export const NAV: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/verification", label: "Verifications", icon: FileSearch },
  { href: "/verification/new", label: "New Verification", icon: FileSearch },
  { href: "/documents", label: "Documents", icon: FolderOpen },
  { href: "/compliance", label: "Compliance", icon: Scale },
  { href: "/evidence", label: "Evidence Chain", icon: Link2 },
  { href: "/audit", label: "Audit Trail", icon: ScrollText },
  { href: "/reports", label: "Reports", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function isActiveNav(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  // "New Verification" must not still be lit while browsing other cases, and the
  // list item must not stay lit on the create page.
  if (href === "/verification/new") return pathname === href;
  if (href === "/verification") {
    return (
      pathname === href ||
      (pathname.startsWith(`${href}/`) && !pathname.startsWith("/verification/new"))
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}