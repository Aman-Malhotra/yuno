import { useMemo, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { Brain, Trash2, User } from "lucide-react";

import {
  type MemoryEntry,
  type MemoryId,
  useDeleteMemory,
  useMemoriesForUser,
} from "@/entities/memory";
import type { WorkspaceId } from "@/entities/workspace";
import { Chip, SectionHeader } from "@/shared/ui";

export function WorkspaceMemoriesPage() {
  const { workspaceId } = useParams({ from: "/protected/workspaces/$workspaceId" });
  const wsId = workspaceId as WorkspaceId;

  const [userIdInput, setUserIdInput] = useState("");
  const [usernameInput, setUsernameInput] = useState("");

  const userId = userIdInput.trim();
  const username = usernameInput.trim() || undefined;

  const memories = useMemoriesForUser(wsId, userId, username, Boolean(userId));
  const deleteMemory = useDeleteMemory(wsId);

  return (
    <div className="mx-auto w-full max-w-[1180px] px-6 py-8">
      <SectionHeader
        title="Memories"
        meta="Long-term memories extracted by mem0 from Telegram conversations. Scoped per user id."
        right={memories.data ? <Chip tone="default">{memories.data.total} total</Chip> : null}
      />

      <div className="hairline-x mt-6" />

      <UserPicker
        userId={userIdInput}
        username={usernameInput}
        onUserId={setUserIdInput}
        onUsername={setUsernameInput}
      />

      <section className="mt-6">
        {!userId ? (
          <EmptyHint message="Enter a channel user id (e.g. a Telegram numeric id like 1340821010) to view memories." />
        ) : (
          <MemoryList
            entries={memories.data?.items ?? []}
            isLoading={memories.isPending}
            isError={memories.isError}
            errorMessage={memories.error?.message}
            onDelete={(id) => deleteMemory.mutate(id)}
            deletingId={deleteMemory.isPending ? (deleteMemory.variables ?? null) : null}
          />
        )}
      </section>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────── */

function UserPicker({
  userId,
  username,
  onUserId,
  onUsername,
}: {
  userId: string;
  username: string;
  onUserId: (v: string) => void;
  onUsername: (v: string) => void;
}) {
  return (
    <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-[1fr_1fr_auto]">
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-faint">User id</span>
        <input
          value={userId}
          onChange={(e) => onUserId(e.target.value)}
          placeholder="e.g. 1340821010"
          className="rounded-sm border border-canvas-rule bg-canvas-panel px-3 py-1.5 text-[13px] text-ink focus:border-sodium focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span className="font-mono text-[10px] uppercase tracking-eyebrow text-ink-faint">
          Username <span className="text-ink-faint">(optional filter)</span>
        </span>
        <input
          value={username}
          onChange={(e) => onUsername(e.target.value)}
          placeholder="e.g. AmanMalhotra18"
          className="rounded-sm border border-canvas-rule bg-canvas-panel px-3 py-1.5 text-[13px] text-ink focus:border-sodium focus:outline-none"
        />
      </label>
    </div>
  );
}

function EmptyHint({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-canvas-rule bg-canvas-panel/40 p-6 text-center text-sm text-ink-mute">
      {message}
    </div>
  );
}

function MemoryList({
  entries,
  isLoading,
  isError,
  errorMessage,
  onDelete,
  deletingId,
}: {
  entries: MemoryEntry[];
  isLoading: boolean;
  isError: boolean;
  errorMessage?: string;
  onDelete: (id: MemoryId) => void;
  deletingId: MemoryId | null;
}) {
  if (isError) {
    return (
      <div className="rounded-md border border-signal-err/40 bg-signal-err/5 p-4 text-sm text-signal-err">
        {errorMessage ?? "Couldn't load memories."}
      </div>
    );
  }

  if (isLoading && entries.length === 0) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            aria-hidden
            className="h-[68px] animate-pulse rounded-md border border-canvas-rule bg-canvas-panel/60"
          />
        ))}
      </div>
    );
  }

  if (entries.length === 0) {
    return <EmptyHint message="No memories yet for this user. Send a few messages through the bot to populate." />;
  }

  return (
    <ul className="space-y-2">
      {entries.map((m) => (
        <MemoryRow key={m.id} memory={m} onDelete={onDelete} isDeleting={deletingId === m.id} />
      ))}
    </ul>
  );
}

function MemoryRow({
  memory,
  onDelete,
  isDeleting,
}: {
  memory: MemoryEntry;
  onDelete: (id: MemoryId) => void;
  isDeleting: boolean;
}) {
  const username = useMemo(() => {
    const v = memory.metadata?.username;
    return typeof v === "string" ? v : null;
  }, [memory.metadata]);

  return (
    <li className="flex items-start gap-3 rounded-md border border-canvas-rule bg-canvas-panel px-4 py-3">
      <div className="mt-0.5 text-ink-mute">
        <Brain size={14} strokeWidth={1.6} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[13px] text-ink">{memory.memory}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-ink-mute">
          {username && (
            <span className="inline-flex items-center gap-1">
              <User size={10} />@{username}
            </span>
          )}
          {memory.createdAt && <span className="font-mono">{memory.createdAt}</span>}
          {memory.categories.length > 0 && (
            <span className="font-mono">{memory.categories.join(" · ")}</span>
          )}
        </div>
      </div>
      <button
        type="button"
        onClick={() => onDelete(memory.id)}
        disabled={isDeleting}
        className="inline-flex h-7 w-7 items-center justify-center rounded-sm text-ink-mute transition-colors hover:bg-canvas-inset hover:text-signal-err disabled:opacity-40"
        title="Forget this memory"
      >
        <Trash2 size={14} strokeWidth={1.6} />
      </button>
    </li>
  );
}
