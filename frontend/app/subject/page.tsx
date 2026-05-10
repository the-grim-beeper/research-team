"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { AgentGrid } from "@/components/agent-grid";
import { BriefingCard } from "@/components/briefing-card";
import { Roundtable } from "@/components/roundtable";
import { RunStandupButton } from "@/components/run-standup-button";
import type { Agent, Artifact, Subject } from "@/lib/types";

function SubjectView() {
  const params = useSearchParams();
  const idParam = params.get("id");
  const id = idParam ? Number(idParam) : null;

  const [subject, setSubject] = useState<Subject | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (id == null || Number.isNaN(id)) {
      setError("Missing or invalid subject id");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [s, a, arts] = await Promise.all([
        api<Subject>(`/subjects/${id}`),
        api<Agent[]>(`/subjects/${id}/agents`),
        api<Artifact[]>(`/subjects/${id}/artifacts?limit=100`),
      ]);
      setSubject(s);
      setAgents(a);
      setArtifacts(arts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (loading) return <p className="text-sm text-neutral-500">Loading…</p>;
  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!subject) return null;

  const agentsById: Record<number, Agent> = Object.fromEntries(
    agents.map((a) => [a.id, a]),
  );

  const briefings = artifacts
    .filter((a) => a.kind === "briefing")
    .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at));
  const latestBriefing = briefings[0] ?? null;

  return (
    <>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-sm text-neutral-500 hover:text-neutral-900">
            ← All subjects
          </Link>
          <Link
            href={`/library/?id=${subject.id}`}
            className="text-sm text-neutral-700 hover:text-neutral-900 underline"
          >
            Library →
          </Link>
        </div>
        <div className="mt-2 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{subject.title}</h1>
            {subject.brief && (
              <p className="mt-1 text-neutral-600 whitespace-pre-wrap">{subject.brief}</p>
            )}
          </div>
          <RunStandupButton subjectId={subject.id} onComplete={refresh} />
        </div>
      </div>

      <section className="mb-10">
        <BriefingCard briefing={latestBriefing} agentsById={agentsById} />
      </section>

      <section className="mb-10">
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-600 mb-3">
          Team
        </h2>
        <AgentGrid agents={agents} onUpdated={refresh} />
      </section>

      <section className="mb-10">
        <h2 className="text-sm font-medium uppercase tracking-wide text-neutral-600 mb-3">
          Roundtable
        </h2>
        <Roundtable
          artifacts={artifacts}
          agentsById={agentsById}
          subjectId={subject.id}
          onChange={refresh}
        />
      </section>
    </>
  );
}

export default function SubjectPage() {
  const { me, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading || !me) return null;

  return (
    <main className="mx-auto max-w-5xl p-8">
      <header className="mb-6 flex items-center justify-between">
        <Link href="/" className="text-2xl font-semibold hover:underline">
          Research Team
        </Link>
        <div className="flex items-center gap-4 text-sm text-neutral-600">
          <span>{me.email}</span>
          <button onClick={logout} className="hover:text-neutral-900">
            Sign out
          </button>
        </div>
      </header>
      <Suspense fallback={<p className="text-sm text-neutral-500">Loading…</p>}>
        <SubjectView />
      </Suspense>
    </main>
  );
}
