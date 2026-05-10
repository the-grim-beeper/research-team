"use client";

import { Suspense, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { LibraryView } from "@/components/library-view";

function Inner() {
  const params = useSearchParams();
  const idParam = params.get("id");
  const id = idParam ? Number(idParam) : null;

  if (id == null || Number.isNaN(id)) {
    return <p className="text-sm text-red-600">Missing or invalid subject id</p>;
  }
  return (
    <>
      <div className="mb-6">
        <Link
          href={`/subject/?id=${id}`}
          className="text-sm text-neutral-500 hover:text-neutral-900"
        >
          ← Back to subject
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">Library</h1>
      </div>
      <LibraryView subjectId={id} />
    </>
  );
}

export default function LibraryPage() {
  const { me, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading || !me) return null;

  return (
    <main className="mx-auto max-w-6xl p-8">
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
        <Inner />
      </Suspense>
    </main>
  );
}
