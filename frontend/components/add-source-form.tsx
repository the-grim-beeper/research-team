"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { Source, SourceKind } from "@/lib/types";

interface Props {
  subjectId: number;
  onAdded: () => void;
}

const KINDS: { value: SourceKind; label: string; configHint: string }[] = [
  { value: "rss", label: "RSS feed", configHint: "Feed URL" },
  { value: "arxiv", label: "arXiv query", configHint: "Search query (e.g. cat:cs.LG ti:transformer)" },
  { value: "url", label: "Single URL", configHint: "Page URL (fetched once on ingest)" },
];

export function AddSourceForm({ subjectId, onAdded }: Props) {
  const [kind, setKind] = useState<SourceKind>("rss");
  const [displayName, setDisplayName] = useState("");
  const [value, setValue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const config: Record<string, string> =
        kind === "arxiv" ? { query: value } : { url: value };
      await api<Source>(`/subjects/${subjectId}/sources`, {
        method: "POST",
        body: JSON.stringify({
          kind,
          display_name: displayName || value.slice(0, 60),
          config,
        }),
      });
      setValue("");
      setDisplayName("");
      onAdded();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add source");
    } finally {
      setSubmitting(false);
    }
  }

  const cfg = KINDS.find((k) => k.value === kind)!;

  return (
    <form onSubmit={onSubmit} className="rounded-lg border border-neutral-200 bg-white p-4 space-y-3">
      <div className="grid grid-cols-3 gap-3">
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as SourceKind)}
          className="rounded border border-neutral-300 px-2 py-2 text-sm"
        >
          {KINDS.map((k) => (
            <option key={k.value} value={k.value}>{k.label}</option>
          ))}
        </select>
        <input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          placeholder="Display name (optional)"
          className="rounded border border-neutral-300 px-2 py-2 text-sm col-span-2"
        />
      </div>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={cfg.configHint}
        required
        className="w-full rounded border border-neutral-300 px-2 py-2 text-sm"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <button
        type="submit"
        disabled={submitting || !value.trim()}
        className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {submitting ? "Adding…" : "Add source"}
      </button>
    </form>
  );
}
