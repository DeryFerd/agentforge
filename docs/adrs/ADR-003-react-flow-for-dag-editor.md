# ADR-003: React Flow over Custom Canvas for DAG Editor

**Status:** Accepted
**Date:** 2026-06-11

## Context

The visual DAG editor needs: draggable nodes, edge connections, custom node rendering, minimap, zoom/pan, snap-to-grid. Building this from scratch on HTML Canvas would take weeks.

## Options Considered

### 1. React Flow (Selected)
- **Pros:** Purpose-built for node-based editors. 20K+ GitHub stars. Custom node types via React components. Built-in minimap, controls, edge routing. Active community. TypeScript support.
- **Cons:** Opinionated API. Large bundle size (~80KB gzipped). Requires React.

### 2. JointJS / Rappid
- **Pros:** More flexible. SVG-based. Framework-agnostic.
- **Cons:** Steeper learning curve. Less React-friendly. Paid commercial license for advanced features.

### 3. Custom Canvas (HTML5 Canvas/SVG)
- **Pros:** Full control. Minimal bundle size.
- **Cons:** Months of development. Need to implement hit testing, edge routing, drag-and-drop, zoom/pan from scratch.

## Decision

**React Flow** — it's the industry standard for visual graph editors in 2026. Custom node types via `AgentForgeNode` component give us full control over rendering while leveraging React Flow's interaction primitives.

## Consequences

- DAG editor was built in 1 day instead of weeks
- Custom nodes (`AgentForgeNode.tsx`) render 7 node types with icons and colors
- Edge connections use React Flow's built-in edge routing with animated edges for active connections
- Trade-off: 80KB bundle size for the editor (acceptable for a productivity tool)
