import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import ErrorBoundaryWrapper from "@/components/ErrorBoundaryWrapper";

// Force dynamic rendering so middleware auth guard runs before any page HTML is sent.
// Without this, static pages are served from cache before middleware can redirect.
export const dynamic = "force-dynamic";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgentForge — Multi-Agent Workflow Orchestrator",
  description:
    "Design, execute, and monitor multi-agent AI workflows with a visual DAG editor, LangGraph execution engine, and full observability.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Dark mode: apply .dark class to body before paint
              try {
                if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.body.classList.add('dark');
                }
              } catch (_) {}

              // Bfcache fix: if page is restored from Chrome's back-forward cache,
              // reload to ensure middleware auth check runs (prevents stale HTML flash)
              window.addEventListener('pageshow', function(event) {
                if (event.persisted) {
                  window.location.reload();
                }
              });
            `,
          }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors">
        <ErrorBoundaryWrapper>{children}</ErrorBoundaryWrapper>
      </body>
    </html>
  );
}
