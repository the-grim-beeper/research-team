"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { SubjectList } from "@/components/subject-list";

export default function Home() {
  const { me, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !me) router.replace("/login");
  }, [loading, me, router]);

  if (loading || !me) return null;

  return (
    <main className="mx-auto max-w-3xl p-8">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Research Team</h1>
        <div className="flex items-center gap-4 text-sm text-neutral-600">
          <span>{me.email}</span>
          <button onClick={logout} className="hover:text-neutral-900">
            Sign out
          </button>
        </div>
      </header>
      <SubjectList />
    </main>
  );
}
