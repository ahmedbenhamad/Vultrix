"use client";

import { useState } from "react";
import { Plus, Lock, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import type { PermissionInfo, Role } from "@/lib/types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/shared";

interface Catalog { permissions: PermissionInfo[] }

export default function RolesPage() {
  const { can } = useAuth();
  const { data: roles, loading, reload } = useApi<Role[]>("/roles", []);
  const { data: catalog } = useApi<Catalog>("/roles/permissions", []);
  const [creating, setCreating] = useState(false);

  return (
    <div>
      <PageHeader
        title="Roles & Permissions"
        description="Define what each role can do. System roles are locked."
        action={
          can("role:manage") && (
            <Button onClick={() => setCreating(true)}><Plus className="h-4 w-4" /> New role</Button>
          )
        }
      />

      {loading && !roles ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {roles?.map((role) => (
            <Card key={role.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="capitalize">{role.name}</CardTitle>
                  {role.is_system && (
                    <Badge tone="muted"><Lock className="mr-1 h-3 w-3" /> system</Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{role.description}</p>
              </CardHeader>
              <CardContent>
                <p className="mb-2 text-xs font-medium text-muted-foreground">
                  {role.permissions.length} permissions
                </p>
                <div className="flex flex-wrap gap-1">
                  {role.permissions.slice(0, 8).map((p) => (
                    <span key={p} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{p}</span>
                  ))}
                  {role.permissions.length > 8 && (
                    <span className="text-[10px] text-muted-foreground">+{role.permissions.length - 8} more</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {creating && catalog && (
        <RoleDialog catalog={catalog.permissions} onClose={() => setCreating(false)} onSaved={reload} />
      )}
    </div>
  );
}

function RoleDialog({
  catalog,
  onClose,
  onSaved,
}: {
  catalog: PermissionInfo[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  function toggle(key: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch("/roles", {
        method: "POST",
        body: { name, description, permissions: Array.from(selected) },
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <Card className="flex max-h-[85vh] w-full max-w-2xl flex-col" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit} className="flex min-h-0 flex-col p-6">
          <h2 className="text-lg font-semibold">New role</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Input placeholder="Role name" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <p className="mb-2 mt-4 text-sm font-medium">Permissions ({selected.size} selected)</p>
          <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto rounded-md border p-3">
            {catalog.map((p) => (
              <label key={p.key} className="flex cursor-pointer items-center gap-2.5 rounded px-2 py-1.5 hover:bg-muted">
                <input type="checkbox" checked={selected.has(p.key)} onChange={() => toggle(p.key)} className="h-4 w-4" />
                <span className="font-mono text-xs">{p.key}</span>
                <span className="text-xs text-muted-foreground">— {p.description}</span>
              </label>
            ))}
          </div>
          {error && <p className="mt-3 text-sm text-critical">{error}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving && <Loader2 className="h-4 w-4 animate-spin" />} Create role</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
