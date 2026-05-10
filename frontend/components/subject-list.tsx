"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Subject } from "@/lib/types";

export function SubjectList() {
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await api<Subject[]>("/subjects");
      setSubjects(rows);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api<Subject>("/subjects", {
        method: "POST",
        body: JSON.stringify({ title, brief }),
      });
      setTitle("");
      setBrief("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    }
  }

  async function onArchive(id: number) {
    await api<Subject>(`/subjects/${id}/archive`, { method: "POST" });
    await refresh();
  }

  const active = subjects.filter((s) => s.status === "active");
  const archived = subjects.filter((s) => s.status === "archived");

  return (
    <div className="space-y-8">
      <section>
        <h2 className="text-lg font-medium mb-2">Active subjects ({active.length}/3)</h2>
        {loading ? (
          <p className="text-sm text-neutral-500">Loading…</p>
        ) : active.length === 0 ? (
          <p className="text-sm text-neutral-500">No active subjects yet.</p>
        ) : (
          <ul className="divide-y divide-neutral-200 rounded border border-neutral-200">
            {active.map((s) => (
              <li key={s.id} className="flex items-center justify-between p-3">
                <Link href={`/subject/?id=${s.id}`} className="flex-1 hover:underline">
                  <div className="font-medium">{s.title}</div>
                  {s.brief && <div className="text-sm text-neutral-600">{s.brief}</div>}
                </Link>
                <button
                  onClick={() => onArchive(s.id)}
                  className="ml-3 text-sm text-neutral-600 hover:text-neutral-900"
                >
                  Archive
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="text-lg font-medium mb-2">New subject</h2>
        <form onSubmit={onCreate} className="space-y-3">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title"
            required
            className="w-full rounded border border-neutral-300 px-3 py-2"
          />
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Brief (your framing of the project)"
            className="w-full rounded border border-neutral-300 px-3 py-2"
            rows={3}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={active.length >= 3 || !title.trim()}
            className="rounded bg-neutral-900 px-4 py-2 text-white disabled:opacity-50"
          >
            Create
          </button>
        </form>
      </section>

      {archived.length > 0 && (
        <section>
          <h2 className="text-lg font-medium mb-2">Archived</h2>
          <ul className="divide-y divide-neutral-200 rounded border border-neutral-200 opacity-70">
            {archived.map((s) => (
              <li key={s.id} className="p-3">
                <div className="font-medium">{s.title}</div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
