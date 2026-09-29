"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, FileUp } from "lucide-react";
import { PageShell } from "@/components/shell/PageShell";
import { useActiveCase } from "@/components/shell/CaseProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Callout, ErrorBanner, MockNotice } from "@/components/ui/Callout";
import { analyseTender, createVerification, uploadTender } from "@/lib/endpoints";

/**
 * Creates the case, attaches the tender and extracts requirements — the first
 * three stages of the workflow in one form.
 */
export default function NewVerificationPage() {
  const router = useRouter();
  const { setActiveId } = useActiveCase();

  const [title, setTitle] = useState("");
  const [tenderReference, setTenderReference] = useState("");
  const [tenderer, setTenderer] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (title.trim().length < 3) {
      setError("Give the verification a title of at least 3 characters.");
      return;
    }
    if (!file) {
      setError("Attach the tender document (.txt, .md, .json, .pdf).");
      return;
    }

    setBusy(true);
    try {
      setProgress("Creating verification…");
      const created = await createVerification({
        title: title.trim(),
        tender_reference: tenderReference.trim(),
        tenderer: tenderer.trim(),
      });

      setProgress("Uploading tender…");
      const form = new FormData();
      form.append("file", file);
      form.append("reference_no", tenderReference.trim());
      form.append("title", title.trim());
      await uploadTender(created.id, form);

      setProgress("Extracting requirements…");
      const analysed = await analyseTender(created.id);

      setActiveId(created.id);
      router.push(`/verification/${created.id}?created=${encodeURIComponent(analysed.message)}`);
    } catch (err) {
      setError((err as Error).message);
      setProgress(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell
      title="New Verification"
      subtitle="Attach a tender and extract its eligibility requirements"
    >
      <div className="grid gap-5 lg:grid-cols-3">
        <Card title="Tender details" className="lg:col-span-2">
          <form onSubmit={onSubmit} className="space-y-4">
            {error ? <ErrorBanner message={error} /> : null}

            <div>
              <label className="label" htmlFor="title">
                Verification title *
              </label>
              <input
                id="title"
                className="field"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Medical Equipment Supply — ABC Technologies"
                required
                minLength={3}
                maxLength={255}
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="label" htmlFor="reference">
                  Tender reference
                </label>
                <input
                  id="reference"
                  className="field"
                  value={tenderReference}
                  onChange={(e) => setTenderReference(e.target.value)}
                  placeholder="TND/2026/001"
                  maxLength={64}
                />
              </div>
              <div>
                <label className="label" htmlFor="tenderer">
                  Tenderer
                </label>
                <input
                  id="tenderer"
                  className="field"
                  value={tenderer}
                  onChange={(e) => setTenderer(e.target.value)}
                  placeholder="Bidder organisation name"
                  maxLength={255}
                />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="tender-file">
                Tender document *
              </label>
              <input
                id="tender-file"
                type="file"
                className="field h-auto py-1.5 file:mr-3 file:rounded file:border-0 file:bg-slate-100 file:px-2.5 file:py-1 file:text-[12px] file:text-slate-700"
                accept=".txt,.md,.json,.pdf,text/plain,application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                required
              />
              <p className="mt-1.5 text-[11px] text-slate-500">
                Accepted: .txt, .md, .json, .pdf · max 10 MB. The stored file is renamed to an
                opaque name; the original filename is only kept as a label.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-1">
              <Button type="submit" variant="primary" loading={busy}>
                <FileUp size={15} aria-hidden />
                Create and extract requirements
              </Button>
              <Button variant="ghost" onClick={() => router.back()} disabled={busy}>
                Cancel
              </Button>
            </div>

            {progress ? (
              <Callout tone="info">
                <span className="font-medium">{progress}</span>
              </Callout>
            ) : null}
          </form>
        </Card>

        <div className="space-y-5">
          <MockNotice
            what="Requirement extraction reads the tender text and maps it against a seeded requirement catalogue. It always produces the same eligibility criteria, which is what makes the demo repeatable."
            production="Production would parse the real PDF with an LLM extraction service, return per-requirement confidence, and let an officer accept or edit each item before verification starts."
          />
          <Card title="What happens next">
            <ol className="space-y-2.5 text-[13px] text-slate-600">
              {[
                "A verification ID is created and becomes the active case.",
                "The tender file is stored and its text extracted.",
                "Eligibility requirements are listed for review.",
                "You upload bidder documents on the Documents stage.",
              ].map((step, index) => (
                <li key={step} className="flex gap-2.5">
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-brand-50 text-[11px] font-semibold text-brand-800 numeric">
                    {index + 1}
                  </span>
                  <span className="pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
            <p className="mt-4 flex items-center gap-1.5 text-[11px] text-slate-400">
              <ArrowRight size={12} aria-hidden />
              Then continue to the Documents stage.
            </p>
          </Card>
        </div>
      </div>
    </PageShell>
  );
}
