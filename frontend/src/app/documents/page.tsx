"use client";

import { useState } from "react";
import { Upload, PlayCircle } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card, EmptyState, LoadingBar } from "@/components/ui/Card";
import { Callout, ErrorBanner, MockNotice } from "@/components/ui/Callout";
import { ConfidenceBar, ProcessingBadge } from "@/components/ui/Badge";
import { DataTable, type Column } from "@/components/ui/Table";
import { getDocuments, processDocuments, uploadDocument } from "@/lib/endpoints";
import { DOC_TYPE_LABELS, formatBytes, formatDateTime, formatInr, titleCase } from "@/lib/format";
import { useApiData } from "@/lib/useApiData";
import type { DocumentOut, DocumentsResponse, ExtractedFieldOut } from "@/lib/types";

const DOC_TYPES = [
  "GST_CERTIFICATE",
  "PAN_DOCUMENT",
  "UDYAM_CERTIFICATE",
  "OEM_AUTHORIZATION",
  "EXPERIENCE",
  "TURNOVER",
  "TECHNICAL_SPECIFICATION",
  "FINANCIAL_ELIGIBILITY",
  "OTHER",
] as const;

export default function DocumentsPage() {
  const { activeId } = useActiveCase();
  const { data, error, refresh } = useApiData<DocumentsResponse>(
    activeId,
    () => getDocuments(activeId!),
  );
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"process" | "upload" | null>(null);
  const [docType, setDocType] = useState<string>("GST_CERTIFICATE");
  const [file, setFile] = useState<File | null>(null);

  async function onUpload() {
    if (!activeId) return;
    if (!file) {
      setActionError("Choose a document to upload.");
      return;
    }
    setBusy("upload");
    setActionError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("doc_type", docType);
      form.append("label", file.name);
      const document = await uploadDocument(activeId, form);
      setNotice(
        `Uploaded "${document.label ?? document.file_name}" — it is stored under an opaque name. Run Process documents to extract its fields.`,
      );
      setFile(null);
      refresh();
    } catch (err) {
      setNotice(null);
      setActionError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function onProcess() {
    if (!activeId) return;
    setBusy("process");
    setActionError(null);
    try {
      const result = await processDocuments(activeId);
      setNotice(
        `${result.message} — ${result.documents_processed} documents, ${result.fields_extracted} fields (mode: ${result.mode}).`,
      );
      refresh();
    } catch (err) {
      setNotice(null);
      setActionError((err as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageShell
      title="Documents"
      subtitle="Bidder evidence: upload, process, and review extracted fields"
      requiresCase
      actions={
        <Button variant="primary" onClick={onProcess} loading={busy === "process"}>
          <PlayCircle size={15} aria-hidden />
          Process documents
        </Button>
      }
    >
      <div className="space-y-5">
        {error ? <ErrorBanner message={error.message} onRetry={refresh} /> : null}
        {actionError ? <ErrorBanner message={actionError} /> : null}
        {notice ? (
          <Callout tone="success" title="Uploaded">
            {notice}
          </Callout>
        ) : null}

        {data === null ? (
          <LoadingBar label="Loading documents" />
        ) : (
          <>
            {data.missing_expected.length > 0 ? (
              <Callout tone="warning" title="Expected document not submitted">
                {data.missing_expected.map((item) => (
                  <p key={item}>{item}</p>
                ))}
                <p className="mt-1">
                  Requirements backed by this document stay in review until it is supplied.
                </p>
              </Callout>
            ) : null}

            <Card title="Upload a document" padded>
              <div className="grid gap-4 sm:grid-cols-[220px_1fr_auto] sm:items-end">
                <div>
                  <label className="label" htmlFor="doc-type">
                    Document type
                  </label>
                  <select
                    id="doc-type"
                    className="field"
                    value={docType}
                    onChange={(e) => setDocType(e.target.value)}
                  >
                    {DOC_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {DOC_TYPE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="doc-file">
                    File
                  </label>
                  <input
                    id="doc-file"
                    type="file"
                    className="field h-auto py-1.5 file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-2.5 file:py-1 file:text-[12px] file:text-slate-700"
                    accept=".txt,.md,.json,.pdf,.csv,.png,.jpg,.jpeg,text/plain,application/pdf,image/png,image/jpeg"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                <Button
                  variant="primary"
                  onClick={onUpload}
                  loading={busy === "upload"}
                  disabled={!file}
                  title={file ? undefined : "Choose a file to upload first"}
                >
                  <Upload size={15} aria-hidden />
                  Upload
                </Button>
              </div>
              <p className="mt-3 text-[11px] text-slate-500">
                Uploads are validated by extension, size and content type, then stored under an
                opaque filename. Traversal and executable names are rejected.
              </p>
            </Card>

            <Card title={`Submitted documents (${data.documents.length})`} padded={false}>
              <DataTable<DocumentOut>
                columns={columns}
                rows={data.documents}
                rowKey={(row) => String(row.id)}
                tableLabel="Submitted documents"
                emptyMessage="No documents uploaded for this verification yet."
              />
              {data.documents.length === 0 ? (
                <div className="border-t border-slate-100 px-5 py-4">
                  <EmptyState
                    title="Nothing uploaded yet"
                    description="Upload a bidder document above, then run Process documents to extract its fields and continue the workflow."
                  />
                </div>
              ) : null}
            </Card>

            {data.documents.length > 0 ? (
              <Card title="Extracted fields" padded={false}>
                <DataTable<{ doc: DocumentOut; field: ExtractedFieldOut }>
                  columns={fieldColumns}
                  rows={data.documents.flatMap((doc) =>
                    doc.extracted_fields.map((field) => ({ doc, field })),
                  )}
                  rowKey={(row) => String(row.field.id)}
                  emptyMessage="No fields extracted yet. Run Process documents."
                />
              </Card>
            ) : null}

            <MockNotice
              what="Extracted values and confidences are read from seeded fixtures, so the same document always yields the same field values."
              production="Production would OCR or parse the document, return per-field confidence, and flag any field below a review threshold for manual confirmation."
            />
          </>
        )}
      </div>
    </PageShell>
  );
}

const columns: Column<DocumentOut>[] = [
  {
    key: "type",
    header: "Type",
    width: "200px",
    render: (row) => (
      <span className="font-medium text-slate-900">{DOC_TYPE_LABELS[row.doc_type] ?? row.doc_type}</span>
    ),
  },
  {
    key: "file",
    header: "File",
    render: (row) => (
      <div className="min-w-0">
        <p className="truncate text-[13px] text-slate-700">{row.label || row.file_name}</p>
        <p className="truncate font-mono text-[11px] text-slate-400">{row.file_name}</p>
      </div>
    ),
  },
  {
    key: "size",
    header: "Size",
    align: "right",
    width: "90px",
    render: (row) => <span className="numeric text-[12px]">{formatBytes(row.file_size)}</span>,
  },
  {
    key: "fields",
    header: "Fields",
    align: "center",
    width: "80px",
    render: (row) => <span className="numeric text-[12px]">{row.extracted_fields.length}</span>,
  },
  {
    key: "mode",
    header: "Mode",
    align: "center",
    width: "110px",
    render: (row) => <ProcessingBadge mode={row.processing_mode} />,
  },
  {
    key: "processed",
    header: "Processed",
    width: "150px",
    render: (row) => (
      <span className="text-[12px] text-slate-500">{formatDateTime(row.processed_at)}</span>
    ),
  },
];

const fieldColumns: Column<{ doc: DocumentOut; field: ExtractedFieldOut }>[] = [
  {
    key: "field",
    header: "Field",
    width: "180px",
    render: (row) => <span className="font-medium text-slate-900">{row.field.field_name}</span>,
  },
  {
    key: "value",
    header: "Value",
    render: (row) => {
      const value = row.field.field_value;
      const isMoney = /turnover|worth|amount|value/i.test(row.field.field_name);
      return (
        <span className="font-mono text-[12px] text-slate-700">
          {isMoney ? formatInr(value) : value}
        </span>
      );
    },
  },
  {
    key: "source",
    header: "Source",
    width: "200px",
    render: (row) => (
      <span className="text-[12px] text-slate-500">
        {row.field.document_label} · {titleCase(row.field.extraction_mode)}
      </span>
    ),
  },
  {
    key: "page",
    header: "Page",
    align: "center",
    width: "70px",
    render: (row) => <span className="numeric text-[12px]">{row.field.page_no}</span>,
  },
  {
    key: "confidence",
    header: "Confidence",
    align: "right",
    width: "130px",
    render: (row) => <ConfidenceBar value={row.field.confidence} />,
  },
];
