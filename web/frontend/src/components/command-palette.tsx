"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search, CornerDownLeft } from "lucide-react";
import { NAV_ITEMS } from "@/lib/nav";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

interface Command {
  label: string;
  hint?: string;
  icon: typeof Search;
  run: () => void;
}

export function CommandPalette() {
  const router = useRouter();
  const { can, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands = useMemo<Command[]>(() => {
    const nav: Command[] = NAV_ITEMS.filter((i) => !i.permission || can(i.permission)).map((i) => ({
      label: `Go to ${i.label}`,
      hint: i.group,
      icon: i.icon,
      run: () => router.push(i.href),
    }));
    const actions: Command[] = [];
    if (can("assessment:create")) {
      actions.push({
        label: "New assessment",
        hint: "Action",
        icon: Search,
        run: () => router.push("/assessments"),
      });
    }
    actions.push({ label: "Sign out", hint: "Account", icon: CornerDownLeft, run: () => logout() });
    return [...nav, ...actions];
  }, [can, router, logout]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? commands.filter((c) => c.label.toLowerCase().includes(s)) : commands;
  }, [q, commands]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => inputRef.current?.focus(), 20);
    }
  }, [open]);

  useEffect(() => setActive(0), [q]);

  if (!open) return null;

  function onListKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, filtered.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
    else if (e.key === "Enter") { e.preventDefault(); filtered[active]?.run(); setOpen(false); }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/40 pt-[15vh]" onClick={() => setOpen(false)}>
      <div className="w-full max-w-lg overflow-hidden rounded-xl border bg-card shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b px-3">
          <Search className="h-4 w-4 text-muted-foreground" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onListKey}
            placeholder="Search commands…"
            className="h-12 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="rounded border px-1.5 py-0.5 text-[10px] text-muted-foreground">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {filtered.length === 0 ? (
            <p className="px-3 py-6 text-center text-sm text-muted-foreground">No commands found</p>
          ) : (
            filtered.map((c, i) => {
              const Icon = c.icon;
              return (
                <button
                  key={c.label}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => { c.run(); setOpen(false); }}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm",
                    i === active ? "bg-accent text-accent-foreground" : "hover:bg-accent/50",
                  )}
                >
                  <Icon className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1">{c.label}</span>
                  {c.hint && <span className="text-[11px] text-muted-foreground">{c.hint}</span>}
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
