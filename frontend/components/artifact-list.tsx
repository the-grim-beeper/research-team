"use client";

import type { Agent, Artifact } from "@/lib/types";

interface Props {
  artifacts: Artifact[];
  agentsById: Record<number, Agent>;
}

export function ArtifactList({ artifacts, agentsById }: Props) {
  if (artifacts.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        No artifacts yet. Run an agent from the panel above to produce one.
      </p>
    );
  }
  return (
    <ul className="space-y-3">
      {artifacts.map((a) => {
        const author =
          a.author_type === "agent" && a.author_id != null
            ? agentsById[a.author_id]?.display_name ?? `Agent #${a.author_id}`
            : "You";
        return (
          <li
            key={a.id}
            className="rounded-lg border border-neutral-200 bg-white p-4"
          >
            <div className="flex items-center justify-between mb-2 text-xs text-neutral-500">
              <span>
                <span className="font-medium text-neutral-700">{author}</span>
                {" — "}
                <span className="uppercase tracking-wide">{a.kind}</span>
              </span>
              <span>{new Date(a.created_at).toLocaleString()}</span>
            </div>
            {a.title && <h3 className="font-medium mb-1">{a.title}</h3>}
            <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-800">
              {a.body_md}
            </pre>
          </li>
        );
      })}
    </ul>
  );
}
