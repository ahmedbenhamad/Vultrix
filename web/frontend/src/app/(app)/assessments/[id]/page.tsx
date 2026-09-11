"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft, Play, Ban, FileDown, Loader2, Radio, Terminal as TerminalIcon,
  TerminalSquare, ArrowUpCircle, Anchor, Network, Upload, KeyRound, GitCompare,
} from "lucide-react";
import { apiFetch, downloadExport } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { useLiveAssessment, type LiveLog, type FeedItem } from "@/lib/useLiveAssessment";
import { LiveConsole } from "@/components/ui/live-console";
import type { Assessment, PostExEvent, Finding, DiffFinding, ScanDiff } from "@/lib/types";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Skeleton } from "@/components/ui/primitives";
import { PageHeader, SeverityBadge, StatusBadge, EmptyState } from "@/components/ui/shared";
import { useToast } from "@/components/ui/toast";
import { formatDate } from "@/lib/utils";

const PHASES = ["recon", "vuln-assessment", "exploitation", "post-exploitation", "reporting"];


export default function AssessmentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { can } = useAuth();
  const toast = useToast();
  // Poll as a safety net; the WebSocket provides the snappy live overlay.
  const { data: a, loading, reload } = useApi<Assessment>(`/assessments/${id}`, [id], 8000);
  const { connected, live, logs, feed } = useLiveAssessment(Number(id), reload);

  async function action(verb: "run" | "cancel") {
    try {
      await apiFetch(`/assessments/${id}/${verb}`, { method: "POST" });
      toast.success(verb === "run" ? "Assessment launched" : "Assessment cancelled");
      reload();
    } catch (e) {
      toast.error(`Could not ${verb} assessment`, e instanceof Error ? e.message : undefined);
    }
  }

  async function exportPdf(assessmentId: number) {
    toast.info("Preparing PDF", "Your download will start shortly.");
    try {
      await downloadExport(assessmentId, "pdf");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    }
  }

  if (loading && !a)
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-56 lg:col-span-2" />
          <Skeleton className="h-56" />
        </div>
      </div>
    );
  if (!a) return <EmptyState title="Assessment not found" />;

  // Live overlay wins when present.
  const status = live?.status ?? a.status;
  const phase = live?.phase ?? a.phase;
  const progress = live?.progress ?? a.progress;
  const findingsCount = live?.findings_count ?? a.findings_count;
  const error = live?.error ?? a.error;
  const activePhaseIdx = PHASES.indexOf(phase);
  const running = status === "running" || status === "queued";

  return (
    <div>
      <Link href="/assessments" className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to assessments
      </Link>

      <PageHeader
        title={a.name}
        description={a.target}
        action={
          <div className="flex gap-2">
            <Link href={`/assessments/${id}/output`}>
              <Button variant="outline"><TerminalIcon className="h-4 w-4" /> Engine output</Button>
            </Link>
            {can("assessment:run") && ["queued", "failed", "cancelled"].includes(status) && (
              <Button onClick={() => action("run")}><Play className="h-4 w-4" /> Run</Button>
            )}
            {can("assessment:cancel") && ["running", "queued"].includes(status) && (
              <Button variant="outline" onClick={() => action("cancel")}><Ban className="h-4 w-4" /> Cancel</Button>
            )}
            {can("report:export") && (
              <Button variant="outline" onClick={() => exportPdf(a.id)}>
                <FileDown className="h-4 w-4" /> Export PDF
              </Button>
            )}
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Pipeline</CardTitle>
              <LiveBadge connected={connected} running={running} />
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-6 flex items-center justify-between gap-2">
              {PHASES.map((p, i) => {
                const done = status === "completed" || i < activePhaseIdx;
                const active = i === activePhaseIdx && status === "running";
                return (
                  <div key={p} className="flex flex-1 flex-col items-center gap-2">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-semibold ${done ? "bg-success text-white" : active ? "bg-primary text-white" : "bg-muted text-muted-foreground"}`}>
                      {active ? <Loader2 className="h-4 w-4 animate-spin" /> : i + 1}
                    </div>
                    <span className="text-center text-[11px] capitalize text-muted-foreground">{p}</span>
                  </div>
                );
              })}
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} />
            </div>
            {error && (
              <div className="mt-3 rounded-md border border-critical/30 bg-critical/10 p-3">
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-critical">Engine error</p>
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-critical">{error}</pre>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Details</CardTitle></CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            <Detail label="Status" value={<StatusBadge status={status} />} />
            <Detail label="Scan type" value={<span className="capitalize">{a.scan_type}</span>} />
            <Detail label="Findings" value={findingsCount} />
            <Detail label="Created" value={formatDate(a.created_at)} />
            <Detail label="Started" value={formatDate(a.started_at)} />
            <Detail label="Finished" value={formatDate(a.finished_at)} />
          </CardContent>
        </Card>
      </div>

      {(logs.length > 0 || feed.length > 0 || running) && <ConsoleCard logs={logs} feed={feed} />}

      {a.post_ex && a.post_ex.length > 0 && <PostExSection events={a.post_ex} />}

      <DiffSection assessmentId={Number(id)} />

      <Card className="mt-4">
        <CardHeader><CardTitle>Findings ({a.findings?.length ?? 0})</CardTitle></CardHeader>
        <CardContent>
          {!a.findings || a.findings.length === 0 ? (
            <EmptyState title="No findings yet" hint="Findings appear as the assessment progresses." />
          ) : (
            <div className="space-y-3">
              {a.findings.map((f) => (
                <FindingCard key={f.id} assessmentId={Number(id)} finding={f} canTriage={can("finding:triage")} onChange={reload} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

const FINDING_STATUS_META: Record<string, { label: string; tone: string }> = {
  open: { label: "Open", tone: "muted" },
  confirmed: { label: "Confirmed", tone: "critical" },
  false_positive: { label: "False positive", tone: "info" },
  remediated: { label: "Remediated", tone: "success" },
  accepted_risk: { label: "Accepted risk", tone: "high" },
};

function FindingCard({
  assessmentId, finding, canTriage, onChange,
}: { assessmentId: number; finding: Finding; canTriage: boolean; onChange: () => void }) {
  const toast = useToast();
  const [saving, setSaving] = useState(false);

  async function patch(body: Record<string, unknown>) {
    setSaving(true);
    try {
      await apiFetch(`/assessments/${assessmentId}/findings/${finding.id}`, { method: "PATCH", body });
      toast.success("Finding updated");
      onChange();
    } catch (e) {
      toast.error("Could not update finding", e instanceof Error ? e.message : undefined);
    } finally {
      setSaving(false);
    }
  }

  const statusMeta = FINDING_STATUS_META[finding.status] ?? FINDING_STATUS_META.open;
  const overridden = finding.severity_override && finding.severity_override !== finding.severity;

  return (
    <div className="rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <SeverityBadge severity={finding.effective_severity} />
        {overridden && <span className="text-[10px] text-muted-foreground">(was {finding.severity})</span>}
        {finding.cve && <span className="font-mono text-xs text-muted-foreground">{finding.cve}</span>}
        <Badge tone={statusMeta.tone} className="ml-auto">{statusMeta.label}</Badge>
      </div>
      <p className="mt-2 font-medium">{finding.title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{finding.description}</p>
      {finding.recommendation && <p className="mt-2 text-sm"><span className="font-medium">Fix:</span> {finding.recommendation}</p>}

      {canTriage && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t pt-3">
          <span className="text-xs font-medium text-muted-foreground">Triage:</span>
          <select
            aria-label="Finding status"
            value={finding.status}
            disabled={saving}
            onChange={(e) => patch({ status: e.target.value })}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs"
          >
            {Object.entries(FINDING_STATUS_META).map(([k, m]) => <option key={k} value={k}>{m.label}</option>)}
          </select>
          <select
            aria-label="Severity override"
            value={finding.severity_override ?? ""}
            disabled={saving}
            onChange={(e) => patch({ severity_override: e.target.value })}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs capitalize"
          >
            <option value="">Severity: {finding.severity}</option>
            {["critical", "high", "medium", "low", "info"].map((s) => <option key={s} value={s}>Override → {s}</option>)}
          </select>
          {saving && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
        </div>
      )}
    </div>
  );
}

function DiffSection({ assessmentId }: { assessmentId: number }) {
  const { data } = useApi<ScanDiff>(`/assessments/${assessmentId}/diff`, [assessmentId]);
  if (!data || data.baseline_id == null) return null;
  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <GitCompare className="h-4 w-4" /> Change since last scan
        </CardTitle>
        <p className="text-sm text-muted-foreground">Compared with “{data.baseline_name}” on the same target.</p>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-3">
        <DiffColumn label="New" tone="text-critical" items={data.new} />
        <DiffColumn label="Fixed" tone="text-success" items={data.fixed} />
        <DiffColumn label="Unchanged" tone="text-muted-foreground" items={data.unchanged} />
      </CardContent>
    </Card>
  );
}

function DiffColumn({ label, tone, items }: { label: string; tone: string; items: DiffFinding[] }) {
  return (
    <div>
      <p className={`mb-2 text-sm font-semibold ${tone}`}>{label} ({items.length})</p>
      <div className="space-y-1.5">
        {items.length === 0 ? (
          <p className="text-xs text-muted-foreground">None</p>
        ) : (
          items.map((f, i) => (
            <div key={i} className="flex items-center gap-2 rounded border p-2 text-xs">
              <SeverityBadge severity={f.severity} />
              <span className="truncate">{f.title}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function LiveBadge({ connected, running }: { connected: boolean; running: boolean }) {
  if (!running && !connected) return null;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${connected ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"}`}>
      <Radio className={`h-3 w-3 ${connected ? "animate-pulse" : ""}`} />
      {connected ? "Live" : "Reconnecting…"}
    </span>
  );
}

function ConsoleCard({ logs, feed }: { logs: LiveLog[]; feed: FeedItem[] }) {
  return (
    <Card className="mt-4">
      <CardHeader><CardTitle>Live console</CardTitle></CardHeader>
      <CardContent>
        <LiveConsole feed={feed} logs={logs} height="max-h-80" />
      </CardContent>
    </Card>
  );
}

const POSTEX_META: Record<string, { icon: typeof KeyRound; label: string; tone: string }> = {
  session: { icon: TerminalSquare, label: "Session", tone: "text-primary bg-primary/10" },
  privesc: { icon: ArrowUpCircle, label: "Priv-esc", tone: "text-critical bg-critical/10" },
  persistence: { icon: Anchor, label: "Persistence", tone: "text-high bg-high/10" },
  lateral: { icon: Network, label: "Lateral", tone: "text-medium bg-medium/10" },
  exfil: { icon: Upload, label: "Exfil", tone: "text-critical bg-critical/10" },
  credential: { icon: KeyRound, label: "Credentials", tone: "text-high bg-high/10" },
};

function PostExSection({ events }: { events: PostExEvent[] }) {
  return (
    <Card className="mt-4 border-critical/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TerminalSquare className="h-4 w-4 text-critical" />
          Post-exploitation ({events.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative space-y-3 before:absolute before:left-[15px] before:top-2 before:h-[calc(100%-1rem)] before:w-px before:bg-border">
          {events.map((e) => {
            const meta = POSTEX_META[e.kind] ?? { icon: TerminalSquare, label: e.kind, tone: "text-muted-foreground bg-muted" };
            const Icon = meta.icon;
            return (
              <div key={e.id} className="relative flex gap-3">
                <div className={`z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.tone}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1 rounded-lg border p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{meta.label}</span>
                    {e.host && <span className="font-mono text-[11px] text-muted-foreground">{e.host}</span>}
                  </div>
                  <p className="mt-0.5 text-sm font-medium">{e.title}</p>
                  {e.detail && <p className="mt-0.5 text-xs text-muted-foreground">{e.detail}</p>}
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
