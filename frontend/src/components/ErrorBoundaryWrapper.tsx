/** Server-component wrapper that renders the client-side ErrorBoundary. */

import ErrorBoundary from "./ErrorBoundary";

export default function ErrorBoundaryWrapper({ children }: { children: React.ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}
