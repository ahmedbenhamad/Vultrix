"use client";

import { useState } from "react";
import { Plus, Trash2, Loader2, CalendarClock } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import type { Schedule } from "@/lib/types";
import { Badge, Button, Card, Input, Table, THead, TR, TH, TD } from "@/components/ui/primitives";
import { PageHeader, EmptyState, TableSkeleton } from "@/components/ui/shared";
import { ConfirmDialog } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/utils";

const CRON_PRESETS: { label: string; cron: string }[] = [
  { label: "Every hour", cron: "0 * * * *" },
  { label: "Daily at 02:00", cron: "0 2 * * *" },
  { label: "Weekdays at 08:00", cron: "0 8 * * 1-5" },
  { label: "Weekly (Mon 03:00)", cron: "0 3 * * 1" },
];

export default function SchedulesPage() {
  const { can } = useAuth();
  const toast = useToast();
  const { data, loading, reload } = useApi<Schedule[]>("/schedules", []);
  const [showCreate, setShowCreate] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<Schedule | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function toggle(s: Schedule) {
    try {
      await apiFetch(`/schedules/${s.id}`, { method: "PATCH", body: { enabled: !s.enabled } });
      reload();
    } catch (e) {
      toast.error("Could not update schedule", e instanceof Error ? e.message : undefined);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await apiFetch(`/schedules/${pendingDelete.id}`, { method: "DELETE" });
      toast.success("Schedule deleted", pendingDelete.name);
      setPendingDelete(null);
      reload();
    } catch (e) {
      toast.error("Could not delete", e instanceof Error ? e.message : undefined);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Schedules"
        description="Run assessments automatically on a recurring cron schedule."
        action={
          can("schedule:manage") && (
            <Button onClick={() => setShowCreate(true)}><Plus className="h-4 w-4" /> New schedule</Button>
          )
        }
      />

      <Card>
        {loading && !data ? (
          <TableSkeleton rows={5} cols={6} />
        ) : !data || data.length === 0 ? (
          <div className="p-6"><EmptyState title="No schedules" hint="Create a schedule to run scans automatically." /></div>
        ) : (
          <Table>
            <THead>
              <TR><TH>Name</TH><TH>Target</TH><TH>Cron</TH><TH>Next run</TH><TH>Last run</TH><TH>Status</TH><TH></TH></TR>
            </THead>
            <tbody>
              {data.map((s) => (
                <TR key={s.id}>
                  <TD className="font-medium">{s.name}</TD>
                  <TD className="font-mono text-xs text-muted-foreground">{s.target}</TD>
                  <TD><code className="rounded bg-muted px-1.5 py-0.5 text-xs">{s.cron}</code></TD>
                  <TD className="text-xs text-muted-foreground">{s.enabled ? formatDate(s.next_run_at) : "—"}</TD>
                  <TD className="text-xs text-muted-foreground">{formatDate(s.last_run_at)}</TD>
                  <TD>
                    {can("schedule:manage") ? (
                      <button onClick={() => toggle(s)} className="cursor-pointer">
                        <Badge tone={s.enabled ? "success" : "muted"}>{s.enabled ? "enabled" : "paused"}</Badge>
                      </button>
                    ) : (
                      <Badge tone={s.enabled ? "success" : "muted"}>{s.enabled ? "enabled" : "paused"}</Badge>
                    )}
                  </TD>
                  <TD>
                    {can("schedule:manage") && (
                      <Button size="icon" variant="ghost" aria-label="Delete schedule" onClick={() => setPendingDelete(s)}>
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

      {showCreate && (
        <CreateScheduleDialog
          onClose={() => setShowCreate(false)}
          onCreated={(name) => { toast.success("Schedule created", name); reload(); }}
        />
      )}

      <ConfirmDialog
        open={!!pendingDelete}
        onClose={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
        title="Delete schedule"
        message={`Delete the schedule “${pendingDelete?.name}”? Future runs will stop.`}
        confirmLabel="Delete"
        destructive
        loading={deleting}
      />
    </div>
  );
}

function CreateScheduleDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (name: string) => void }) {
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [scanType, setScanType] = useState("full");
  const [cron, setCron] = useState("0 2 * * *");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch("/schedules", { method: "POST", body: { name, target, scan_type: scanType, cron } });
      onCreated(name);
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
          <h2 className="flex items-center gap-2 text-lg font-semibold"><CalendarClock className="h-4 w-4" /> New schedule</h2>
          <div className="mt-4 space-y-3">
            <Field label="Name"><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nightly external scan" required /></Field>
            <Field label="Target"><Input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="app.example.com" required /></Field>
            <Field label="Scan type">
              <select value={scanType} onChange={(e) => setScanType(e.target.value)} className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm">
                <option value="full">Full</option><option value="quick">Quick</option><option value="api">API</option><option value="infra">Infrastructure</option>
              </select>
            </Field>
            <Field label="Cron schedule">
              <Input value={cron} onChange={(e) => setCron(e.target.value)} placeholder="0 2 * * *" className="font-mono" required />
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {CRON_PRESETS.map((p) => (
                  <button type="button" key={p.cron} onClick={() => setCron(p.cron)} className="rounded-full border px-2 py-0.5 text-[11px] hover:bg-accent">
                    {p.label}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">5-field crontab (min hour day month weekday), UTC.</p>
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
