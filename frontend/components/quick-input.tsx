"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { BibliographyEntry } from "@/lib/types";

interface Props {
  subjectId: number;
  onAdded: () => void;
}

export function QuickInput({ subjectId, onAdded }: Props) {
  const [mode, setMode] = useState<"note" | "url">("note");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (mode === "note") {
        await api<BibliographyEntry[]>(`/subjects/${subjectId}/notes`, {
          method: "POST",
          body: JSON.stringify({ title, text: body }),
        });
      } else {
        await api<BibliographyEntry[]>(`/subjects/${subjectId}/url`, {
          method: "POST",
          body: JSON.stringify({ url: body }),
        });
      }
      setTitle("");
      setBody("");
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Add failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="rounded-lg border border-neutral-200 bg-white p-4 space-y-3">
      <div className="flex gap-2 text-sm">
        <button
          type="button"
          onClick={() => setMode("note")}
          className={`rounded px-3 py-1 ${mode === "note" ? "bg-neutral-900 text-white" : "bg-neutral-100"}`}
        >
          Note
        </button>
        <button
          type="button"
          onClick={() => setMode("url")}
          className={`rounded px-3 py-1 ${mode === "url" ? "bg-neutral-900 text-white" : "bg-neutral-100"}`}
        >
          Fetch URL
        </button>
      </div>
      {mode === "note" && (
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title (optional)"
          className="w-full rounded border border-neutral-300 px-3 py-2 text-sm"
        />
      )}
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={mode === "note" ? "Your note (any length)" : "https://…"}
        rows={mode === "note" ? 4 : 1}
        required
        className="w-full rounded border border-neutral-300 px-3 py-2 text-sm"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !body.trim()}
        className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {submitting ? "Processing…" : mode === "note" ? "Add note" : "Fetch & process"}
      </button>
    </form>
  );
}
