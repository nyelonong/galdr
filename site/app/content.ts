export interface MethodStage {
  id: "route" | "shape" | "plan" | "waves" | "verify" | "memory";
  state: string;
  name: string;
  description: string;
  output: string;
}

export interface RouteExample {
  id: "flaky-checkout" | "new-export" | "api-architecture" | "documentation";
  request: string;
  route: "debug" | "shape-synthesis" | "rearchitect" | "answer";
  reason: string;
  next: string;
}

export interface RuntimeInstall {
  id: "claude" | "codex" | "antigravity";
  label: string;
  install: readonly string[];
  enable: string;
}

export const METHOD_STAGES: readonly MethodStage[] = [
  { id: "route", state: "Orient", name: "Route", description: "Match the request to the smallest useful workflow.", output: "A clear starting point" },
  { id: "shape", state: "Frame", name: "Shape", description: "Turn an uncertain idea into a decision-ready brief.", output: "A bounded problem" },
  { id: "plan", state: "Commit", name: "Plan", description: "Make the work executable before changing the system.", output: "A tested path" },
  { id: "waves", state: "Build", name: "Waves", description: "Deliver independent slices with visible evidence.", output: "Working increments" },
  { id: "verify", state: "Prove", name: "Verify", description: "Check the outcome against the promise and the code.", output: "Proof of completion" },
  { id: "memory", state: "Learn", name: "Memory", description: "Keep the decisions that make the next request sharper.", output: "Durable context" },
] satisfies readonly MethodStage[];

export const ROUTE_EXAMPLES: readonly RouteExample[] = [
  { id: "flaky-checkout", request: "Our checkout test flakes after a deploy.", route: "debug", reason: "A failure needs evidence before a fix.", next: "Reproduce, isolate, and verify the cause." },
  { id: "new-export", request: "We need to export a new customer report.", route: "shape-synthesis", reason: "The desired outcome needs a useful boundary.", next: "Shape the workflow before implementation." },
  { id: "api-architecture", request: "Our API has outgrown its original service boundary.", route: "rearchitect", reason: "The system structure is now the constraint.", next: "Map the deployment and ownership seams." },
  { id: "documentation", request: "What does this release process require?", route: "answer", reason: "The information is already available.", next: "Answer directly and cite the source of truth." },
] satisfies readonly RouteExample[];

export const RUNTIME_INSTALLS: readonly RuntimeInstall[] = [
  { id: "claude", label: "Claude Code", install: ["/plugin marketplace add nyelonong/galdr", "/plugin install galdr@nyelonong"], enable: "/galdr:core install claude" },
  { id: "codex", label: "Codex", install: ["npx skills add nyelonong/galdr"], enable: "/galdr:core install codex" },
  { id: "antigravity", label: "Antigravity", install: ["npx skills add nyelonong/galdr"], enable: "/galdr:core install antigravity" },
] satisfies readonly RuntimeInstall[];
