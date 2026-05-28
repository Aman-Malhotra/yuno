export type AuthMode = "signin" | "signup";

export const loginCopy = {
  productMarker: "Mission control",
  productTitle: "Yuno Orchestrator",
  productTagline: "Build, wire and observe collaborative agents from a single console.",
  bullets: [
    "Spin up agents on real runtimes — LangGraph, CrewAI, custom",
    "Wire workflows with conditions, feedback loops, human approvals",
    "Stream tokens, costs and inter-agent messages in real time",
  ],
  signinTitle: "Sign in",
  signinSubtitle: "Use your email and password to access the console.",
  signupTitle: "Create an account",
  signupSubtitle: "Spin up your workspace in seconds — no credit card required.",
  footnote: "Console for the Yuno AI Agent Orchestration Platform.",
} as const;
