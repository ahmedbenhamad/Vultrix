"use client";

import { usePathname } from "next/navigation";
import { LogOut, Menu, Moon, Sun } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";
import { NAV_ITEMS } from "@/lib/nav";
import { Button } from "@/components/ui/primitives";

export function Topbar({ onMenu }: { onMenu: () => void }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();

  const current =
    NAV_ITEMS.find((i) => pathname === i.href || pathname.startsWith(i.href + "/"))?.label ?? "Console";

  const initials =
    (user?.full_name || user?.email || "?")
      .split(/[ @.]/)
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase())
      .join("") || "?";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-card/80 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenu} aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </Button>
        <div>
          <p className="text-sm font-semibold leading-tight">{current}</p>
          {user && (
            <p className="hidden text-xs text-muted-foreground sm:block">
              {user.full_name || user.email} · <span className="capitalize">{user.role?.name ?? (user.is_superuser ? "superuser" : "user")}</span>
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme" title="Toggle theme">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <div className="flex items-center gap-2 rounded-full border bg-background py-1 pl-1 pr-3">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
            {initials}
          </div>
          <span className="hidden text-sm font-medium sm:inline">{user?.email}</span>
        </div>
        <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out" title="Log out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
