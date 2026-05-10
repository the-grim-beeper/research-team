"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BibliographyEntry, Source } from "@/lib/types";
import { AddSourceForm } from "./add-source-form";
import { QuickInput } from "./quick-input";

interface Props {
  subjectId: number;
}

export function LibraryView({ subjectId }: Props) {
  const [sources, setSources] = useState<Source[]>([]);
  const [bibliography, setBibliography] = useState<BibliographyEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busySourceId, setBusySourceId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, b] = await Promise.all([
        api<Source[]>(`/subjects/${subjectId}/sources`),
        api<BibliographyEntry[]>(`/subjects/${subjectId}/bibliography`),
      ]);
      setSources(s);
      setBibliography(b);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [subjectId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function ingestSource(sourceId: number) {
    setBusySourceId(sourceId);
    setError(null);
    try {
      await api<unknown>(`/subjects/${subjectId}/sources/${sourceId}/ingest`, {
        method: "POST",
      });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingest failed");
    } finally {
      setBusySourceId(null);
    }
  }

  async function deleteSource(sourceId: number) {
    await api<unknown>(`/sources/${sourceId}`, { method: "DELETE" });
    await refresh();
  }

  return (
    <div className="grid gap-8 lg:grid-cols-2">
      <section className="space-y-4">
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-600">
          Sources
        </h2>
        <AddSourceForm subjectId={subjectId} onAdded={refresh} />
        <QuickInput subjectId={subjectId} onAdded={refresh} />
        {loading ? (
          <p className="text-sm text-neutral-500">Loading…</p>
        ) : sources.length === 0 ? (
          <p className="text-sm text-neutral-500">No registered sources yet.</p>
        ) : (
          <ul className="rounded-lg border border-neutral-200 divide-y divide-neutral-200 bg-white">
            {sources.map((s) => (
              <li key={s.id} className="flex items-center justify-between p-3 text-sm">
                <div>
                  <div className="font-medium">{s.display_name}</div>
                  <div className="text-xs text-neutral-500 uppercase">{s.kind}</div>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => ingestSource(s.id)}
                    disabled={busySourceId === s.id}
                    className="text-neutral-700 hover:text-neutral-900 disabled:opacity-50"
                  >
                    {busySourceId === s.id ? "Ingesting…" : "Ingest"}
                  </button>
                  <button
                    onClick={() => deleteSource(s.id)}
                    className="text-neutral-500 hover:text-red-600"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-600">
          Bibliography
        </h2>
        {error && <p className="text-sm text-red-600">{error}</p>}
        {bibliography.length === 0 ? (
          <p className="text-sm text-neutral-500">
            Empty. Register a source and ingest, or add a quick note.
          </p>
        ) : (
          <ul className="space-y-3">
            {bibliography.map((b) => (
              <li
                key={b.id}
                className="rounded-lg border border-neutral-200 bg-white p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-medium">
                    {b.url ? (
                      <a
                        href={b.url}
                        target="_blank"
                        rel="noreferrer"
                        className="hover:underline"
                      >
                        {b.title}
                      </a>
                    ) : (
                      b.title
                    )}
                  </h3>
                  {b.importance != null && (
                    <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700 shrink-0">
                      ★ {b.importance}/5
                    </span>
                  )}
                </div>
                {b.summary && (
                  <p className="mt-1 text-sm text-neutral-700 whitespace-pre-wrap">
                    {b.summary}
                  </p>
                )}
                {b.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {b.tags.map((t, i) => (
                      <span
                        key={i}
                        className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-700"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
                {b.comments && (
                  <pre className="mt-2 whitespace-pre-wrap font-sans text-xs text-neutral-600">
                    {b.comments}
                  </pre>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
