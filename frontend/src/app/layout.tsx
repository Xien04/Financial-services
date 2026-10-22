import type { Metadata } from "next";
import "./globals.css";

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
