import type { Metadata } from "next";
import "./globals.css";
import { CaseProvider } from "@/components/shell/CaseProvider";

export const metadata: Metadata = {
  title: "BIDFLUX — Tender Verification",
  description:
    "AI-assisted procurement compliance: tender, documents, verification, compliance, risk, decision, audit and evidence.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <CaseProvider>{children}</CaseProvider>
      </body>
    </html>
  );
}
