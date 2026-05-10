"use client";

import type { Agent } from "@/lib/types";
import { modelLabel } from "@/lib/models";

interface Props {
  agent: Agent;
  onClick: () => void;
}

const CYCLE_LABEL: Record<Agent["cycle"], string> = {
  off: "Off",
  on_demand: "On demand",
  hourly: "Hourly",
  every_4h: "Every 4h",
  daily: "Daily",
};

export function AgentCard({ agent, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="text-left rounded-lg border border-neutral-200 bg-white p-4 hover:border-neutral-400 hover:shadow-sm transition"
    >
      <div className="flex items-start justify-between mb-2">
        <h3 className="font-medium">{agent.display_name}</h3>
        <span className="text-xs text-neutral-500 uppercase tracking-wide">
          {agent.role.category}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5 text-xs">
        <span className="rounded bg-neutral-100 px-2 py-0.5 text-neutral-700">
          {modelLabel(agent.model)}
        </span>
        <span className="rounded bg-neutral-100 px-2 py-0.5 text-neutral-700">
          {CYCLE_LABEL[agent.cycle]}
        </span>
        <span className="rounded bg-neutral-100 px-2 py-0.5 text-neutral-700">
          ${agent.daily_budget_usd}/day
        </span>
      </div>
      <p className="mt-2 text-xs text-neutral-500">
        {agent.last_run_at
          ? `Last run: ${new Date(agent.last_run_at).toLocaleString()}`
          : "Not run yet"}
      </p>
    </button>
  );
}
