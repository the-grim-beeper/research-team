import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Research Team",
  description: "Personal multi-agent research environment",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
