"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Agent, Artifact } from "@/lib/types";

interface Props {
  artifacts: Artifact[];
  agentsById: Record<number, Agent>;
  subjectId: number;
  onChange: () => void;
}

const ROUNDTABLE_KINDS = new Set([
  "critique",
  "roundtable_post",
  "open_question",
  "instruction",
]);

const KIND_LABEL: Record<string, string> = {
  critique: "Critique",
  roundtable_post: "Roundtable",
  open_question: "Open question",
  instruction: "Instruction",
};


function authorOf(artifact: Artifact, agentsById: Record<number, Agent>): string {
  if (artifact.author_type === "user") return "You";
  if (artifact.author_id != null) {
    return agentsById[artifact.author_id]?.display_name ?? `Agent #${artifact.author_id}`;
  }
  return "agent";
}


export function Roundtable({ artifacts, agentsById, subjectId, onChange }: Props) {
  const threads = artifacts.filter(
    (a) => ROUNDTABLE_KINDS.has(a.kind) && a.parent_id == null,
  );
  const repliesByParent: Record<number, Artifact[]> = {};
  for (const a of artifacts) {
    if (a.parent_id != null) {
      (repliesByParent[a.parent_id] ??= []).push(a);
    }
  }

  if (threads.length === 0) {
    return (
      <p className="text-sm text-neutral-500">
        No roundtable threads yet. Run a standup or post an instruction.
      </p>
    );
  }

  return (
    <ul className="space-y-4">
      {threads
        .slice()
        .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at))
        .map((thread) => (
          <Thread
            key={thread.id}
            thread={thread}
            replies={(repliesByParent[thread.id] ?? []).sort(
              (a, b) => +new Date(a.created_at) - +new Date(b.created_at),
            )}
            agentsById={agentsById}
            subjectId={subjectId}
            onChange={onChange}
          />
        ))}
    </ul>
  );
}


function Thread({
  thread,
  replies,
  agentsById,
  subjectId,
  onChange,
}: {
  thread: Artifact;
  replies: Artifact[];
  agentsById: Record<number, Agent>;
  subjectId: number;
  onChange: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function reply(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api<Artifact>(`/subjects/${subjectId}/artifacts`, {
        method: "POST",
        body: JSON.stringify({
          kind: "roundtable_post",
          body_md: body,
          parent_id: thread.id,
        }),
      });
      setBody("");
      setOpen(false);
      onChange();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <li className="rounded-lg border border-neutral-200 bg-white p-4">
      <header className="mb-2 flex items-center justify-between text-xs text-neutral-500">
        <span>
          <span className="font-medium uppercase tracking-wide text-neutral-700">
            {KIND_LABEL[thread.kind] ?? thread.kind}
          </span>{" "}
          · {authorOf(thread, agentsById)}
        </span>
        <span>{new Date(thread.created_at).toLocaleString()}</span>
      </header>
      <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-800">
        {thread.body_md}
      </pre>

      {replies.length > 0 && (
        <ul className="mt-4 space-y-3 border-l-2 border-neutral-200 pl-4">
          {replies.map((r) => (
            <li key={r.id}>
              <div className="text-xs text-neutral-500 mb-1">
                <span className="font-medium text-neutral-700">{authorOf(r, agentsById)}</span>{" "}
                · {new Date(r.created_at).toLocaleString()}
              </div>
              <pre className="whitespace-pre-wrap font-sans text-sm text-neutral-800">
                {r.body_md}
              </pre>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3">
        {!open ? (
          <button
            onClick={() => setOpen(true)}
            className="text-xs text-neutral-600 hover:text-neutral-900"
          >
            Reply
          </button>
        ) : (
          <form onSubmit={reply} className="space-y-2">
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={3}
              required
              placeholder="Reply…"
              className="w-full rounded border border-neutral-300 px-3 py-2 text-sm"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={submitting || !body.trim()}
                className="rounded bg-neutral-900 px-3 py-1 text-xs text-white disabled:opacity-50"
              >
                Post reply
              </button>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setBody("");
                }}
                className="rounded bg-neutral-100 px-3 py-1 text-xs text-neutral-700"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </li>
  );
}
