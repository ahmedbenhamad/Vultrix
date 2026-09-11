"use client";

import { useState } from "react";
import { useApi } from "@/lib/hooks";
import type { AuditEvent, Page } from "@/lib/types";
import { Badge, Card, Input, Table, THead, TR, TH, TD } from "@/components/ui/primitives";
import { PageHeader, EmptyState } from "@/components/ui/shared";
import { formatDate } from "@/lib/utils";

export default function AuditPage() {
  const [q, setQ] = useState("");
  const { data, loading } = useApi<Page<AuditEvent>>(
    `/audit?page=1&page_size=100${q ? `&q=${encodeURIComponent(q)}` : ""}`,
    [q],
  );

  return (
    <div>
      <PageHeader title="Audit Trail" description="Immutable record of security-relevant actions." />

      <div className="mb-4">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by actor email…" className="max-w-xs" />
      </div>

      <Card>
        {loading && !data ? (
          <div className="p-10 text-center text-sm text-muted-foreground">Loading…</div>
        ) : !data || data.items.length === 0 ? (
          <div className="p-6"><EmptyState title="No audit events" /></div>
        ) : (
          <Table>
            <THead>
              <TR><TH>Time</TH><TH>Actor</TH><TH>Action</TH><TH>Resource</TH><TH>IP</TH><TH>Result</TH></TR>
            </THead>
            <tbody>
              {data.items.map((e) => (
                <TR key={e.id}>
                  <TD className="whitespace-nowrap text-xs text-muted-foreground">{formatDate(e.created_at)}</TD>
                  <TD className="text-sm">{e.actor_email || "—"}</TD>
                  <TD><span className="font-mono text-xs">{e.action}</span></TD>
                  <TD className="text-xs text-muted-foreground">
                    {e.resource_type ? `${e.resource_type}${e.resource_id ? ` #${e.resource_id}` : ""}` : "—"}
                  </TD>
                  <TD className="font-mono text-xs text-muted-foreground">{e.ip_address || "—"}</TD>
                  <TD>
                    <Badge tone={e.status === "success" ? "success" : "critical"}>{e.status}</Badge>
                  </TD>
                </TR>
              ))}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}
