"use client";

import { useState } from "react";
import { Plus, Trash2, Loader2, ShieldCheck } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import type { Page, Role, User } from "@/lib/types";
import { Badge, Button, Card, Input, Table, THead, TR, TH, TD } from "@/components/ui/primitives";
import { PageHeader, EmptyState, TableSkeleton } from "@/components/ui/shared";
import { ConfirmDialog } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/utils";

export default function UsersPage() {
  const { can, user: me } = useAuth();
  const toast = useToast();
  const { data, loading, reload } = useApi<Page<User>>("/users?page=1&page_size=100", []);
  const { data: roles } = useApi<Role[]>("/roles", []);
  const [showCreate, setShowCreate] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<User | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await apiFetch(`/users/${pendingDelete.id}`, { method: "DELETE" });
      toast.success("User deleted", pendingDelete.email);
      setPendingDelete(null);
      reload();
    } catch (e) {
      toast.error("Could not delete user", e instanceof Error ? e.message : undefined);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Users"
        description="Manage accounts and role assignments."
        action={
          can("user:create") && (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" /> Add user
            </Button>
          )
        }
      />

      <Card>
        {loading && !data ? (
          <TableSkeleton rows={6} cols={6} />
        ) : !data || data.items.length === 0 ? (
          <div className="p-6"><EmptyState title="No users" /></div>
        ) : (
          <Table>
            <THead>
              <TR><TH>Name</TH><TH>Email</TH><TH>Role</TH><TH>Status</TH><TH>Last login</TH><TH></TH></TR>
            </THead>
            <tbody>
              {data.items.map((u) => (
                <TR key={u.id}>
                  <TD className="font-medium">
                    {u.full_name || "—"}
                    {u.is_superuser && <ShieldCheck className="ml-1 inline h-3.5 w-3.5 text-primary" />}
                  </TD>
                  <TD className="text-muted-foreground">{u.email}</TD>
                  <TD>{u.role ? <Badge tone="primary">{u.role.name}</Badge> : <span className="text-muted-foreground">—</span>}</TD>
                  <TD>
                    {u.is_active ? <Badge tone="success">active</Badge> : <Badge tone="muted">disabled</Badge>}
                  </TD>
                  <TD className="text-xs text-muted-foreground">{formatDate(u.last_login_at)}</TD>
                  <TD>
                    {can("user:delete") && u.id !== me?.id && (
                      <Button size="icon" variant="ghost" onClick={() => setPendingDelete(u)} aria-label="Delete user">
                        <Trash2 className="h-4 w-4 text-critical" />
                      </Button>
                    )}
                  </TD>
                </TR>
              ))}
            </tbody>
          </Table>
        )}
      </Card>

      {showCreate && roles && (
        <CreateUserDialog
          roles={roles}
          onClose={() => setShowCreate(false)}
          onCreated={(email) => {
            toast.success("User created", email);
            reload();
          }}
        />
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title="Delete user"
        message={`Permanently delete ${pendingDelete?.email}? This cannot be undone.`}
        confirmLabel="Delete user"
        destructive
        loading={deleting}
      />
    </div>
  );
}

function CreateUserDialog({
  roles,
  onClose,
  onCreated,
}: {
  roles: Role[];
  onClose: () => void;
  onCreated: (email: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState<number>(roles.find((r) => r.name === "viewer")?.id ?? roles[0]?.id);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch("/users", {
        method: "POST",
        body: { email, full_name: fullName, password, role_id: roleId },
      });
      onCreated(email);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit} className="p-6">
          <h2 className="text-lg font-semibold">Add user</h2>
          <div className="mt-4 space-y-3">
            <Field label="Full name"><Input value={fullName} onChange={(e) => setFullName(e.target.value)} /></Field>
            <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
            <Field label="Temporary password">
              <Input type="text" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required />
            </Field>
            <Field label="Role">
              <select
                value={roleId}
                onChange={(e) => setRoleId(Number(e.target.value))}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm capitalize"
              >
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>{r.name}</option>
                ))}
              </select>
            </Field>
          </div>
          {error && <p className="mt-3 text-sm text-critical">{error}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving && <Loader2 className="h-4 w-4 animate-spin" />} Create</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium">{label}</label>
      {children}
    </div>
  );
}
