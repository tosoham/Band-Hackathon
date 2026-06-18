"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = { href: string; label: string };

const ITEMS: NavItem[] = [
  { href: "/intake", label: "Intake" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/ledger", label: "Promise Ledger" },
  { href: "/audit", label: "Audit Trail" },
];

export function NavShell() {
  const pathname = usePathname();

  // The login screen owns the full viewport — no chrome there.
  if (!pathname || pathname.startsWith("/login")) {
    return null;
  }

  return (
    <nav className="navShell" aria-label="Primary">
      <Link href="/intake" className="navBrand">
        <span className="navBrandMark">BG</span>
        <span>BandGate</span>
      </Link>
      <ul>
        {ITEMS.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={pathname.startsWith(item.href) ? "navLink navLinkActive" : "navLink"}
            >
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
      <form action="/api/auth/logout" method="post" className="navLogout">
        <button type="submit">Sign out</button>
      </form>
    </nav>
  );
}
