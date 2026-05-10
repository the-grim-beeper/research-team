"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { CYCLE_OPTIONS, MODEL_OPTIONS } from "@/lib/models";
import type { Agent, AgentUpdate, Artifact } from "@/lib/types";

interface Props {
  agent: Agent;
  onClose: () => void;
  onSaved: () => void;
}

export function AgentSettingsPanel({ agent, onClose, onSaved }: Props) {
  const [model, setModel] = useState(agent.model);
  const [cycle, setCycle] = useState<Agent["cycle"]>(agent.cycle);
  const [budget, setBudget] = useState(agent.daily_budget_usd);
  const [addendum, setAddendum] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [instruction, setInstruction] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Artifact | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body: AgentUpdate = { model, cycle, daily_budget_usd: budget };
      if (addendum.trim()) body.system_prompt_addendum = addendum.trim();
      await api<Agent>(`/agents/${agent.id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function onRun() {
    setRunning(true);
    setRunError(null);
    setResult(null);
    try {
      const art = await api<Artifact>(`/agents/${agent.id}/execute`, {
        method: "POST",
        body: JSON.stringify({ instruction: instruction.trim() || null }),
      });
      setResult(art);
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setRunError("Daily budget exhausted for this agent. Raise the cap and try again.");
      } else {
        setRunError(err instanceof Error ? err.message : "Run failed");
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <aside className="relative h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold">{agent.display_name}</h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-neutral-900">
            Close
          </button>
        </div>

        <section className="space-y-3 mb-8 rounded-lg border border-neutral-200 p-4 bg-neutral-50">
          <h3 className="text-sm font-medium">Run now (one-shot)</h3>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Optional instruction (leave blank to use the agent's default cycle prompt)"
            rows={2}
            className="w-full rounded border border-neutral-300 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="w-full rounded bg-neutral-900 py-2 text-sm text-white disabled:opacity-50"
          >
            {running ? "Running…" : "Run now"}
          </button>
          {runError && <p className="text-xs text-red-600">{runError}</p>}
          {result && (
            <details open className="text-sm">
              <summary className="cursor-pointer text-neutral-600 mb-1">
                Result
              </summary>
              <pre className="whitespace-pre-wrap rounded bg-white p-3 text-xs">
                {result.body_md}
              </pre>
            </details>
          )}
        </section>

        <form onSubmit={onSave} className="space-y-5">
          <div>
            <label className="block text-sm font-medium mb-1">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full rounded border border-neutral-300 px-3 py-2"
            >
              {MODEL_OPTIONS.map((m) => (
                <option key={m.slug} value={m.slug}>
                  {m.label} ({m.tier})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Cycle</label>
            <select
              value={cycle}
              onChange={(e) => setCycle(e.target.value as Agent["cycle"])}
              className="w-full rounded border border-neutral-300 px-3 py-2"
            >
              {CYCLE_OPTIONS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              Daily budget cap (USD)
            </label>
            <input
              type="number"
              min={0}
              step={0.05}
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="w-full rounded border border-neutral-300 px-3 py-2"
            />
            <p className="mt-1 text-xs text-neutral-500">
              Spent today: ${agent.spent_today_usd}
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              System-prompt addendum
            </label>
            <textarea
              value={addendum}
              onChange={(e) => setAddendum(e.target.value)}
              rows={5}
              placeholder="Persistent extra instruction for this agent (appended to its base role prompt)"
              className="w-full rounded border border-neutral-300 px-3 py-2 font-mono text-xs"
            />
          </div>

          <details className="text-sm">
            <summary className="cursor-pointer text-neutral-600">
              Current effective system prompt
            </summary>
            <pre className="mt-2 whitespace-pre-wrap rounded bg-neutral-50 p-3 font-mono text-xs">
              {agent.system_prompt}
            </pre>
          </details>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded bg-neutral-900 py-2 text-white disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </form>
      </aside>
    </div>
  );
}
