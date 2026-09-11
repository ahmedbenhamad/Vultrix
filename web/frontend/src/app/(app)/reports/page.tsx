"use client";

import { FileText, FileDown, FileJson, Sheet, FileCode } from "lucide-react";
import { downloadExport } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/toast";
import type { Page, Report } from "@/lib/types";
import { Button, Card, CardContent } from "@/components/ui/primitives";
import { PageHeader, EmptyState } from "@/components/ui/shared";
import { formatDate } from "@/lib/utils";

export default function ReportsPage() {
  const { can } = useAuth();
  const toast = useToast();
  const { data, loading } = useApi<Page<Report>>("/reports?page=1&page_size=100", []);
  const handleExport = async (id: number, fmt: "pdf" | "csv" | "json" | "md") => {
    try {
      await downloadExport(id, fmt);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    }
  };

  return (
    <div>
      <PageHeader title="Reports" description="Generated assessment reports. 'Strix report' downloads the exact engine-generated markdown; also exportable to PDF, CSV or JSON." />

      {loading && !data ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : !data || data.items.length === 0 ? (
        <EmptyState title="No reports" hint="Reports are generated when assessments complete." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.items.map((r) => (
            <Card key={r.id}>
              <CardContent className="p-5">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FileText className="h-5 w-5" />
                </div>
                <p className="font-medium leading-snug">{r.title}</p>
                <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{r.summary}</p>
                <p className="mt-2 text-xs text-muted-foreground">{formatDate(r.created_at)}</p>
                {can("report:export") && r.assessment_id && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleExport(r.assessment_id!, "md")}>
                      <FileCode className="h-3.5 w-3.5" /> Strix report
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleExport(r.assessment_id!, "pdf")}>
                      <FileDown className="h-3.5 w-3.5" /> PDF
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleExport(r.assessment_id!, "csv")}>
                      <Sheet className="h-3.5 w-3.5" /> CSV
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleExport(r.assessment_id!, "json")}>
                      <FileJson className="h-3.5 w-3.5" /> JSON
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
