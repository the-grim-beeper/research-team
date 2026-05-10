"use client";

import type { Agent, Artifact } from "@/lib/types";

interface Props {
  briefing: Artifact | null;
  agentsById: Record<number, Agent>;
}

export function BriefingCard({ briefing, agentsById }: Props) {
  if (!briefing) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 bg-white p-6 text-center text-sm text-neutral-500">
        No briefing yet — press <span className="font-medium">Run standup</span> to have
        the Editor produce one.
      </div>
    );
  }
  const author =
    briefing.author_id != null ? agentsById[briefing.author_id]?.display_name ?? "Editor" : "Editor";
  return (
    <article className="rounded-lg border border-neutral-300 bg-white p-6 shadow-sm">
      <header className="mb-3 flex items-center justify-between text-xs text-neutral-500">
        <span>
          <span className="font-medium uppercase tracking-wide text-neutral-700">
            Briefing
          </span>{" "}
          · {author}
        </span>
        <span>{new Date(briefing.created_at).toLocaleString()}</span>
      </header>
      <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-800">
        {briefing.body_md}
      </pre>
    </article>
  );
}
