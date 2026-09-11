"use client";

import { useEffect, useRef, useState } from "react";
import { Search } from "lucide-react";
import type { FeedItem, LiveLog } from "@/lib/useLiveAssessment";
import { Input } from "@/components/ui/primitives";

const LOG_TONE: Record<string, string> = {
  error: "text-critical",
  warn: "text-high",
  info: "text-slate-300",
  debug: "text-slate-500",
};

// Map a tool call to a Strix-CLI-style prefix, icon and one-line summary.
function toolPresentation(item: Extract<FeedItem, { kind: "tool" }>): {
  icon: string;
  prefix: string;
  detail: string;
  cls: string;
} {
  const a = item.args ?? {};
  const s = (k: string) => (typeof a[k] === "string" ? (a[k] as string) : "");
  const name = item.toolName;
  const first = () => {
    for (const v of Object.values(a)) if (typeof v === "string" && v.trim()) return v as string;
    return "";
  };

  if (/(terminal|shell|command|bash)/i.test(name)) {
    return { icon: ">_", prefix: "$", detail: s("command") || s("input") || s("cmd") || first(), cls: "text-emerald-400" };
  }
  if (/browser/i.test(name)) {
    const url = s("url");
    const action = s("action") || "browser";
    return { icon: "🌐", prefix: url ? "launching" : action, detail: url || first(), cls: "text-sky-400" };
  }
  if (/web_search/i.test(name)) {
    return { icon: "🌐", prefix: "searching the web", detail: s("query") || first(), cls: "text-sky-400" };
  }
  if (/create_agent|spawn/i.test(name)) {
    return { icon: "◆", prefix: "spawning", detail: s("name") || s("task") || first(), cls: "text-violet-400" };
  }
  if (/exploit_research/i.test(name)) {
    const subj = [s("service"), s("version")].filter(Boolean).join(" ") || s("cve") || first();
    return { icon: "🎯", prefix: "exploit research", detail: subj, cls: "text-violet-400" };
  }
  if (/proxy|scope/i.test(name)) {
    return { icon: "<~>", prefix: "proxy scope", detail: s("name") || first(), cls: "text-sky-400" };
  }
  if (/report|finish|vulnerability/i.test(name)) {
    return { icon: "✓", prefix: name.replace(/_/g, " "), detail: first(), cls: "text-amber-400" };
  }
  return { icon: "→", prefix: `using ${name.replace(/_/g, " ")}`, detail: first(), cls: "text-slate-300" };
}

function FeedRow({ item }: { item: FeedItem }) {
  if (item.kind === "message") {
    if (item.role !== "assistant") return null;
    return (
      <div className="mt-2">
        <div className="text-fuchsia-400">💭 Thinking</div>
        <div className="whitespace-pre-wrap break-words pl-4 italic text-slate-400">{item.content}</div>
      </div>
    );
  }
  if (item.kind === "agent") {
    if (item.action === "created") {
      return (
        <div className="mt-1 text-violet-400">
          ◆ spawning <span className="font-semibold">{item.name}</span>
          {item.task ? <span className="text-slate-500"> — {item.task}</span> : null}
        </div>
      );
    }
    return (
      <div className="text-slate-500">
        ◇ {item.name ?? item.agentId} → <span className="text-slate-400">{item.status}</span>
      </div>
    );
  }
  // tool
  if (item.phase === "end") {
    if (item.status && item.status !== "success" && item.status !== "completed") {
      return <div className="pl-4 text-rose-400">✗ {item.toolName.replace(/_/g, " ")} {item.status}</div>;
    }
    return null;
  }
  const p = toolPresentation(item);
  return (
    <div className={`mt-1 ${p.cls}`}>
      <span className="select-none">{p.icon} </span>
      <span className="font-medium">{p.prefix}</span>
      {p.detail ? <span className="text-slate-300"> {p.detail}</span> : null}
    </div>
  );
}

/**
 * Strix-CLI-style live console. Renders the structured agent feed (thinking,
 * tool calls, agent lifecycle) when available, with a toggle to the raw engine
 * output. Falls back to the raw log automatically when no structured feed has
 * arrived (simulations, or an engine build that predates events.jsonl).
 */
export function LiveConsole({
  feed,
  logs,
  height = "h-[28rem]",
}: {
  feed: FeedItem[];
  logs: LiveLog[];
  height?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [q, setQ] = useState("");
  const [raw, setRaw] = useState(false);

  const useRaw = raw || feed.length === 0;

  const filteredLogs = logs.filter((l) => !q || l.message.toLowerCase().includes(q.toLowerCase()));
  const filteredFeed = q
    ? feed.filter((f) => JSON.stringify(f).toLowerCase().includes(q.toLowerCase()))
    : feed;

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [useRaw ? filteredLogs.length : filteredFeed.length, useRaw]);

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter console…" className="h-9 pl-8" />
        </div>
        <button
          type="button"
          onClick={() => setRaw((v) => !v)}
          disabled={feed.length === 0}
          className="h-9 rounded-md border border-input bg-background px-3 text-xs disabled:opacity-40"
          title="Toggle between the structured agent view and raw engine output"
        >
          {useRaw ? "Raw output" : "Agent view"}
        </button>
      </div>
      <div ref={ref} className={`${height} overflow-auto rounded-md bg-slate-950 p-3 font-mono text-xs leading-relaxed`}>
        {useRaw ? (
          filteredLogs.length === 0 ? (
            <p className="text-slate-500">Waiting for output…</p>
          ) : (
            filteredLogs.map((l, i) => (
              <div key={i} className="flex gap-2">
                <span className="shrink-0 text-slate-600">{l.created_at ? new Date(l.created_at).toLocaleTimeString() : ""}</span>
                <span className={`shrink-0 uppercase ${LOG_TONE[l.level] ?? "text-slate-400"}`}>{l.level}</span>
                <span className="break-all text-slate-300">{l.message}</span>
              </div>
            ))
          )
        ) : filteredFeed.length === 0 ? (
          <p className="text-slate-500">Waiting for output…</p>
        ) : (
          filteredFeed.map((item, i) => <FeedRow key={i} item={item} />)
        )}
      </div>
    </div>
  );
}
