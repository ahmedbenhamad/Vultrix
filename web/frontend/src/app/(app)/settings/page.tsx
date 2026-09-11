"use client";

import { useState } from "react";
import { Loader2, Check, ShieldCheck, ShieldAlert, Monitor, LogOut } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useApi } from "@/lib/hooks";
import type { AuthSession } from "@/lib/types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from "@/components/ui/primitives";
import { PageHeader } from "@/components/ui/shared";
import { useToast } from "@/components/ui/toast";
import { formatDate, relativeTime } from "@/lib/utils";

export default function SettingsPage() {
  const { user } = useAuth();

  return (
    <div className="max-w-2xl space-y-4">
      <PageHeader title="Settings" description="Manage your profile and security." />

      <Card>
        <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
        <CardContent className="space-y-3 text-sm">
          <Row label="Name" value={user?.full_name || "—"} />
          <Row label="Email" value={user?.email ?? ""} />
          <Row label="Role" value={<Badge tone="primary">{user?.role?.name ?? (user?.is_superuser ? "superuser" : "—")}</Badge>} />
          <Row label="Permissions" value={`${user?.permissions.length ?? 0} granted`} />
        </CardContent>
      </Card>

      <MfaCard />
      <SessionsCard />
      <ChangePasswordCard />
    </div>
  );
}

function MfaCard() {
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const [setup, setSetup] = useState<{ secret: string; provisioning_uri: string; recovery_codes: string[] } | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  async function startSetup() {
    setBusy(true);
    try {
      setSetup(await apiFetch("/auth/mfa/setup", { method: "POST" }));
    } catch (e) {
      toast.error("Could not start MFA setup", e instanceof Error ? e.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  async function enable() {
    setBusy(true);
    try {
      await apiFetch("/auth/mfa/enable", { method: "POST", body: { code } });
      toast.success("Two-factor authentication enabled");
      setSetup(null);
      setCode("");
      await refreshUser();
    } catch (e) {
      toast.error("Invalid code", e instanceof Error ? e.message : undefined);
    } finally {
      setBusy(false);
    }
  }

  async function disable() {
    const otp = window.prompt("Enter a current authenticator code to disable MFA:");
    if (!otp) return;
    try {
      await apiFetch("/auth/mfa/disable", { method: "POST", body: { code: otp } });
      toast.success("Two-factor authentication disabled");
      await refreshUser();
    } catch (e) {
      toast.error("Could not disable MFA", e instanceof Error ? e.message : undefined);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Two-factor authentication</CardTitle>
          {user?.mfa_enabled ? (
            <Badge tone="success"><ShieldCheck className="mr-1 h-3 w-3" /> Enabled</Badge>
          ) : user?.mfa_required ? (
            <Badge tone="critical"><ShieldAlert className="mr-1 h-3 w-3" /> Required</Badge>
          ) : (
            <Badge tone="muted">Disabled</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {user?.mfa_enabled ? (
          <>
            <p className="text-muted-foreground">Your account is protected with an authenticator app.</p>
            {!user.mfa_required && <Button variant="outline" onClick={disable}>Disable MFA</Button>}
            {user.mfa_required && (
              <p className="text-xs text-muted-foreground">MFA is mandatory for your role and can’t be disabled.</p>
            )}
          </>
        ) : !setup ? (
          <>
            <p className="text-muted-foreground">
              Add a second factor with any TOTP app (Google Authenticator, 1Password, Authy…).
            </p>
            <Button onClick={startSetup} disabled={busy}>
              {busy && <Loader2 className="h-4 w-4 animate-spin" />} Set up MFA
            </Button>
          </>
        ) : (
          <div className="space-y-3">
            <div>
              <p className="mb-1 font-medium">1. Add this secret to your authenticator app</p>
              <code className="block break-all rounded bg-muted px-2 py-1.5 font-mono text-xs">{setup.secret}</code>
              <p className="mt-1 break-all text-[11px] text-muted-foreground">{setup.provisioning_uri}</p>
            </div>
            <div>
              <p className="mb-1 font-medium">2. Save these recovery codes (shown once)</p>
              <div className="grid grid-cols-2 gap-1 rounded bg-muted p-2 font-mono text-xs">
                {setup.recovery_codes.map((c) => <span key={c}>{c}</span>)}
              </div>
            </div>
            <div>
              <p className="mb-1 font-medium">3. Enter the current 6-digit code</p>
              <div className="flex gap-2">
                <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" inputMode="numeric" className="max-w-[160px]" />
                <Button onClick={enable} disabled={busy || !code}>
                  {busy && <Loader2 className="h-4 w-4 animate-spin" />} Verify & enable
                </Button>
                <Button variant="ghost" onClick={() => setSetup(null)}>Cancel</Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SessionsCard() {
  const toast = useToast();
  const { data, loading, reload } = useApi<AuthSession[]>("/auth/sessions", []);

  async function revoke(id: number) {
    try {
      await apiFetch(`/auth/sessions/${id}`, { method: "DELETE" });
      toast.success("Session revoked");
      reload();
    } catch (e) {
      toast.error("Could not revoke session", e instanceof Error ? e.message : undefined);
    }
  }

  async function revokeAll() {
    try {
      await apiFetch("/auth/sessions/revoke-all", { method: "POST" });
      toast.info("Signed out of all sessions", "You may need to sign in again.");
      reload();
    } catch (e) {
      toast.error("Could not revoke sessions", e instanceof Error ? e.message : undefined);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Active sessions</CardTitle>
          <Button size="sm" variant="outline" onClick={revokeAll}><LogOut className="h-3.5 w-3.5" /> Sign out everywhere</Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading && !data ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : (
          <div className="space-y-2">
            {(data ?? []).map((s) => (
              <div key={s.id} className="flex items-center justify-between rounded-md border p-3 text-sm">
                <div className="flex items-center gap-3">
                  <Monitor className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="font-medium">
                      {s.user_agent ? s.user_agent.slice(0, 42) : "Unknown device"}
                      {s.current && <Badge tone="primary" className="ml-2">This device</Badge>}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {s.ip_address || "—"} · active {relativeTime(s.last_used_at)} · since {formatDate(s.created_at)}
                    </p>
                  </div>
                </div>
                {!s.current && (
                  <Button size="sm" variant="ghost" onClick={() => revoke(s.id)}>Revoke</Button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ChangePasswordCard() {
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [saving, setSaving] = useState(false);
  const [ok, setOk] = useState(false);

  async function changePassword(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setOk(false);
    try {
      await apiFetch("/auth/change-password", { method: "POST", body: { current_password: current, new_password: next } });
      setOk(true);
      setCurrent("");
      setNext("");
      toast.success("Password updated", "Sign in again to continue.");
    } catch (err) {
      toast.error("Could not change password", err instanceof Error ? err.message : undefined);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Change password</CardTitle></CardHeader>
      <CardContent>
        <form onSubmit={changePassword} className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Current password</label>
            <Input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium">New password</label>
            <Input type="password" value={next} onChange={(e) => setNext(e.target.value)} minLength={8} required />
          </div>
          {ok && <p className="flex items-center gap-1.5 text-sm text-success"><Check className="h-4 w-4" /> Updated.</p>}
          <Button type="submit" disabled={saving}>{saving && <Loader2 className="h-4 w-4 animate-spin" />} Update password</Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b py-1.5 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
