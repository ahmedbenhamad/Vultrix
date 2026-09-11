"use client";

import { useState } from "react";
import Link from "next/link";
import { Plus, Play, Loader2, Search } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import type { Assessment, Page } from "@/lib/types";
import {
  Button,
  Card,
  Input,
  Table,
  THead,
  TR,
  TH,
  TD,
} from "@/components/ui/primitives";
import { PageHeader, StatusBadge, EmptyState, TableSkeleton } from "@/components/ui/shared";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/utils";

export default function AssessmentsPage() {
  const { can } = useAuth();
  const toast = useToast();
  const [q, setQ] = useState("");
  const { data, loading, reload } = useApi<Page<Assessment>>(
    `/assessments?page=1&page_size=50${q ? `&q=${encodeURIComponent(q)}` : ""}`,
    [q],
    5000,
  );
  const [showCreate, setShowCreate] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  async function run(id: number, name: string) {
    setBusyId(id);
    try {
      await apiFetch(`/assessments/${id}/run`, { method: "POST" });
      toast.success("Assessment launched", name);
      await reload();
    } catch (e) {
      toast.error("Could not start assessment", e instanceof Error ? e.message : undefined);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Assessments"
        description="Create, launch and track Strix security assessments."
        action={
          can("assessment:create") && (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4" /> New assessment
            </Button>
          )
        }
      />

      <div className="mb-4 flex items-center gap-2">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or target…" className="pl-8" />
        </div>
      </div>

      <Card>
        {loading && !data ? (
          <TableSkeleton rows={6} cols={7} />
        ) : !data || data.items.length === 0 ? (
          <div className="p-6">
            <EmptyState title="No assessments" hint="Create your first assessment to get started." />
          </div>
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Name</TH>
                <TH>Target</TH>
                <TH>Status</TH>
                <TH>Phase</TH>
                <TH>Progress</TH>
                <TH>Findings</TH>
                <TH>Created</TH>
                <TH></TH>
              </TR>
            </THead>
            <tbody>
              {data.items.map((a) => (
                <TR key={a.id}>
                  <TD className="font-medium">
                    <Link href={`/assessments/${a.id}`} className="hover:text-primary hover:underline">
                      {a.name}
                    </Link>
                  </TD>
                  <TD className="font-mono text-xs text-muted-foreground">{a.target}</TD>
                  <TD><StatusBadge status={a.status} /></TD>
                  <TD className="text-sm capitalize">{a.phase}</TD>
                  <TD>
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-muted">
                        <div className="h-full bg-primary transition-all" style={{ width: `${a.progress}%` }} />
                      </div>
                      <span className="text-xs tabular-nums text-muted-foreground">{Math.round(a.progress)}%</span>
                    </div>
                  </TD>
                  <TD className="tabular-nums">{a.findings_count}</TD>
                  <TD className="text-xs text-muted-foreground">{formatDate(a.created_at)}</TD>
                  <TD>
                    {can("assessment:run") && ["queued", "failed", "cancelled"].includes(a.status) && (
                      <Button size="sm" variant="outline" disabled={busyId === a.id} onClick={() => run(a.id, a.name)}>
                        {busyId === a.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                        Run
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
        <CreateDialog
          onClose={() => setShowCreate(false)}
          onCreated={(name) => {
            toast.success("Assessment created", name);
            reload();
          }}
        />
      )}
    </div>
  );
}

function CreateDialog({ onClose, onCreated }: { onClose: () => void; onCreated: (name: string) => void }) {
  const [name, setName] = useState("");
  const [target, setTarget] = useState("");
  const [scanType, setScanType] = useState("full");
  const [instruction, setInstruction] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      await apiFetch("/assessments", { method: "POST", body: { name, target, scan_type: scanType, instruction } });
      onCreated(name);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <form onSubmit={submit} className="p-6">
          <h2 className="text-lg font-semibold">New assessment</h2>
          <p className="mb-4 mt-1 text-sm text-muted-foreground">Configure a new Strix scan.</p>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Name</label>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Q3 external assessment" required />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Target</label>
              <Input value={target} onChange={(e) => setTarget(e.target.value)} placeholder="https://app.example.com or 10.0.0.5" required />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Scan type</label>
              <select
                value={scanType}
                onChange={(e) => setScanType(e.target.value)}
                className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="full">Full</option>
                <option value="quick">Quick</option>
                <option value="api">API</option>
                <option value="infra">Infrastructure</option>
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Instructions <span className="font-normal text-muted-foreground">(optional)</span></label>
              <textarea
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="e.g. Focus on IDOR and authentication bypass; creds admin:pass123"
                rows={3}
                className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <p className="text-[11px] text-muted-foreground">Passed to the engine as <code>--instruction</code>.</p>
            </div>
          </div>
          {error && <p className="mt-3 text-sm text-critical">{error}</p>}
          <div className="mt-5 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>
              {saving && <Loader2 className="h-4 w-4 animate-spin" />} Create
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
