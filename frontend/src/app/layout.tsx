import type { Metadata } from "next";
import "./globals.css";

// Per-request CSP nonces must also be present on Next.js's generated scripts.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Financial Services",
  description: "A private place to understand your money.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">Skip to content</a>
        <header><span className="brand">Financial Services</span></header>
        <main id="main">{children}</main>
      </body>
    </html>
  );
}
