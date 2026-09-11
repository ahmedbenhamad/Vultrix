"use client";

import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import Link from "next/link";
import { Activity, ShieldCheck, Bug, Users as UsersIcon, ArrowRight } from "lucide-react";
import { useApi } from "@/lib/hooks";
import type { DashboardStats, Assessment, Page } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Skeleton } from "@/components/ui/primitives";
import { PageHeader, StatusBadge } from "@/components/ui/shared";
import { relativeTime } from "@/lib/utils";

const SEV_COLORS: Record<string, string> = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#d97706",
  low: "#2563eb",
  info: "#64748b",
};

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: number | string;
  icon: typeof Activity;
  accent: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center justify-between p-5">
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg ${accent}`}>
          <Icon className="h-5 w-5" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, loading } = useApi<DashboardStats>("/stats/dashboard", [], 10000);
  const { data: recent } = useApi<Page<Assessment>>("/assessments?page=1&page_size=6", [], 10000);

  const sevData = data
    ? Object.entries(data.severity_breakdown)
        .filter(([, v]) => v > 0)
        .map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div>
      <PageHeader title="Dashboard" description="Live overview of assessments, findings and activity." />

      {loading && !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total assessments" value={data?.total_assessments ?? 0} icon={ShieldCheck} accent="bg-primary/10 text-primary" />
            <StatCard label="Running now" value={data?.running_assessments ?? 0} icon={Activity} accent="bg-success/15 text-success" />
            <StatCard label="Total findings" value={data?.total_findings ?? 0} icon={Bug} accent="bg-critical/15 text-critical" />
            <StatCard label="Users" value={data?.total_users ?? 0} icon={UsersIcon} accent="bg-info/15 text-info" />
          </div>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Activity — last 14 days</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={data?.recent_activity ?? []}>
                    <defs>
                      <linearGradient id="ga" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gf" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#dc2626" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="#dc2626" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} tickFormatter={(d) => d.slice(5)} stroke="#94a3b8" />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} stroke="#94a3b8" width={28} />
                    <Tooltip />
                    <Area type="monotone" dataKey="assessments" stroke="#2563eb" fill="url(#ga)" strokeWidth={2} />
                    <Area type="monotone" dataKey="findings" stroke="#dc2626" fill="url(#gf)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Findings by severity</CardTitle>
              </CardHeader>
              <CardContent>
                {sevData.length === 0 ? (
                  <p className="py-16 text-center text-sm text-muted-foreground">No findings yet</p>
                ) : (
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={sevData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                        {sevData.map((s) => (
                          <Cell key={s.name} fill={SEV_COLORS[s.name] ?? "#64748b"} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                )}
                <div className="mt-3 flex flex-wrap justify-center gap-3">
                  {sevData.map((s) => (
                    <span key={s.name} className="flex items-center gap-1.5 text-xs">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: SEV_COLORS[s.name] }} />
                      <span className="capitalize">{s.name}</span>
                      <span className="font-semibold">{s.value}</span>
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="mt-4">
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Recent assessments</CardTitle>
              <Link href="/assessments" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </CardHeader>
            <CardContent>
              {!recent || recent.items.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">No assessments yet.</p>
              ) : (
                <div className="divide-y">
                  {recent.items.map((a) => (
                    <Link
                      key={a.id}
                      href={`/assessments/${a.id}`}
                      className="flex items-center gap-4 py-3 transition-colors hover:bg-muted/40"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{a.name}</p>
                        <p className="truncate font-mono text-xs text-muted-foreground">{a.target}</p>
                      </div>
                      <div className="hidden w-28 sm:block">
                        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                          <div className="h-full bg-primary" style={{ width: `${a.progress}%` }} />
                        </div>
                      </div>
                      <span className="w-16 text-right text-xs tabular-nums text-muted-foreground">{a.findings_count} finds</span>
                      <StatusBadge status={a.status} />
                      <span className="hidden w-20 text-right text-xs text-muted-foreground md:block">{relativeTime(a.created_at)}</span>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
