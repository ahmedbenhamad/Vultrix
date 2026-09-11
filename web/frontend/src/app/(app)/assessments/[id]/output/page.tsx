"use client";

import { use, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Radio, Cpu, Coins, Activity, Clock } from "lucide-react";
import { useApi } from "@/lib/hooks";
import { useLiveAssessment } from "@/lib/useLiveAssessment";
import type { AgentNode, AssessmentOutput } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Skeleton } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/shared";
import { LiveConsole } from "@/components/ui/live-console";

const AGENT_TONE: Record<string, string> = {
  running: "bg-primary",
  completed: "bg-success",
  failed: "bg-critical",
  waiting: "bg-medium",
  queued: "bg-info",
};

export default function OutputPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, loading } = useApi<AssessmentOutput>(`/assessments/${id}/output`, [id], 3000);
  const { connected, live, logs, feed } = useLiveAssessment(Number(id));

  return (
    <div>
      <Link href={`/assessments/${id}`} className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back to assessment
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Engine output</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Live agent tree, token usage and streaming console from the Strix engine.
          </p>
        </div>
        <LiveBadge connected={connected} status={live?.status} />
      </div>

      <TelemetryRow data={data} loading={loading} />

      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Agent tree</CardTitle></CardHeader>
          <CardContent>
            {loading && !data ? (
              <Skeleton className="h-40" />
            ) : !data?.has_run_dir || data.agents.length === 0 ? (
              <EmptyState title="No agent data" hint="Agents appear once a real engine run starts (not shown for simulations)." />
            ) : (
              <AgentTree agents={data.agents} />
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-3">
          <CardHeader><CardTitle>Live console</CardTitle></CardHeader>
          <CardContent><LiveConsole feed={feed} logs={logs} /></CardContent>
        </Card>
      </div>
    </div>
  );
}

function LiveBadge({ connected, status }: { connected: boolean; status?: string }) {
  const running = status === "running" || status === "queued";
  if (!connected && !running) return <span className="text-xs text-muted-foreground">{status ?? ""}</span>;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${connected ? "bg-success/15 text-success" : "bg-muted text-muted-foreground"}`}>
      <Radio className={`h-3 w-3 ${connected ? "animate-pulse" : ""}`} />
      {connected ? "Live" : "Offline"}
    </span>
  );
}

function TelemetryRow({ data, loading }: { data: AssessmentOutput | null; loading: boolean }) {
  const t = data?.telemetry;
  const elapsed = useMemo(() => {
    if (!t?.start_time) return "—";
    const end = t.end_time ? new Date(t.end_time) : new Date();
    const secs = Math.max(0, Math.round((end.getTime() - new Date(t.start_time).getTime()) / 1000));
    const m = Math.floor(secs / 60);
    return m > 0 ? `${m}m ${secs % 60}s` : `${secs}s`;
  }, [t]);

  if (loading && !data) {
    return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)}</div>;
  }

  const fmt = (n?: number) => (n ?? 0).toLocaleString();
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Stat icon={Activity} label="LLM requests" value={fmt(t?.requests)} accent="bg-primary/10 text-primary" />
      <Stat icon={Cpu} label="Total tokens" value={fmt(t?.total_tokens)} sub={`${fmt(t?.input_tokens)} in · ${fmt(t?.output_tokens)} out`} accent="bg-info/15 text-info" />
      <Stat icon={Coins} label="Est. cost" value={t?.cost ? `$${Number(t.cost).toFixed(4)}` : "$0"} accent="bg-success/15 text-success" />
      <Stat icon={Clock} label="Elapsed" value={elapsed} accent="bg-medium/15 text-medium" />
    </div>
  );
}

function Stat({ icon: Icon, label, value, sub, accent }: { icon: typeof Activity; label: string; value: string; sub?: string; accent: string }) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 truncate text-2xl font-semibold tabular-nums">{value}</p>
          {sub && <p className="mt-0.5 truncate text-[11px] text-muted-foreground">{sub}</p>}
        </div>
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${accent}`}><Icon className="h-5 w-5" /></div>
      </CardContent>
    </Card>
  );
}

function AgentTree({ agents }: { agents: AgentNode[] }) {
  const roots = agents.filter((a) => !a.parent || !agents.some((x) => x.id === a.parent));
  const childrenOf = (id: string) => agents.filter((a) => a.parent === id);
  return (
    <div className="space-y-1">
      {roots.map((r) => <AgentRow key={r.id} node={r} childrenOf={childrenOf} depth={0} />)}
    </div>
  );
}

function AgentRow({ node, childrenOf, depth }: { node: AgentNode; childrenOf: (id: string) => AgentNode[]; depth: number }) {
  const [open, setOpen] = useState(true);
  const kids = childrenOf(node.id);
  return (
    <div>
      <div
        className="flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5 hover:bg-muted/50"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => setOpen((o) => !o)}
      >
        <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${AGENT_TONE[node.status] ?? "bg-muted-foreground"} ${node.status === "running" ? "animate-pulse" : ""}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">{node.name}</span>
            <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{node.status}</span>
            {node.pending > 0 && <span className="rounded bg-muted px-1 text-[10px]">{node.pending} pending</span>}
          </div>
          {node.task && <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{node.task}</p>}
        </div>
      </div>
      {open && kids.map((k) => <AgentRow key={k.id} node={k} childrenOf={childrenOf} depth={depth + 1} />)}
    </div>
  );
}

