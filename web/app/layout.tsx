import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "rekipedia — AI Codebase Intelligence",
  description: "Browse codebase wikis, explore module dependency graphs, and chat with your codebase using hybrid RAG.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
