"use client";

import { useState } from "react";
import type { Agent } from "@/lib/types";
import { AgentCard } from "./agent-card";
import { AgentSettingsPanel } from "./agent-settings-panel";

interface Props {
  agents: Agent[];
  onUpdated: () => void;
}

export function AgentGrid({ agents, onUpdated }: Props) {
  const [openId, setOpenId] = useState<number | null>(null);
  const open = agents.find((a) => a.id === openId) ?? null;

  const admin = agents.filter((a) => a.role.category === "admin");
  const experts = agents.filter((a) => a.role.category === "expert");

  return (
    <>
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-neutral-600 uppercase tracking-wide">
          Admin team
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {admin.map((a) => (
            <AgentCard key={a.id} agent={a} onClick={() => setOpenId(a.id)} />
          ))}
        </div>
      </section>

      <section className="space-y-3 mt-8">
        <h2 className="text-sm font-medium text-neutral-600 uppercase tracking-wide">
          Subject experts
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {experts.map((a) => (
            <AgentCard key={a.id} agent={a} onClick={() => setOpenId(a.id)} />
          ))}
        </div>
      </section>

      {open && (
        <AgentSettingsPanel
          agent={open}
          onClose={() => setOpenId(null)}
          onSaved={() => {
            setOpenId(null);
            onUpdated();
          }}
        />
      )}
    </>
  );
}
