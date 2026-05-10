"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { Artifact } from "@/lib/types";

interface Props {
  subjectId: number;
  onComplete: () => void;
}

export function RunStandupButton({ subjectId, onComplete }: Props) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onClick() {
    setRunning(true);
    setError(null);
    try {
      await api<Artifact[]>(`/subjects/${subjectId}/standup`, { method: "POST" });
      onComplete();
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        setError("OpenRouter call failed. Check OPENROUTER_API_KEY and budgets.");
      } else {
        setError(err instanceof Error ? err.message : "Standup failed");
      }
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={onClick}
        disabled={running}
        className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {running ? "Running standup…" : "Run standup"}
      </button>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
