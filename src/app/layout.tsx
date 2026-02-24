import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nanoclaw Air-Gapped Dashboard",
  description: "Air-gapped multi-agent dashboard scaffold with secure API routing."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
