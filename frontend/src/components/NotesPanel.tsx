import { Trash2 } from "lucide-react";
import { useId, useState, type SubmitEvent } from "react";

import { ApiError, getFieldError } from "../api/client.ts";
import { useAddNote, useDeleteNote } from "../hooks/useApplications.ts";
import { formatDateTime } from "../lib/format.ts";
import type { Note } from "../types/application.ts";
import { Button } from "./Button.tsx";

const MAX_NOTE_LENGTH = 2000;

interface NotesPanelProps {
  applicationId: number;
  notes: Note[];
  currentUserId: number;
}

export function NotesPanel({ applicationId, notes, currentUserId }: NotesPanelProps) {
  const textareaId = useId();
  const [body, setBody] = useState("");
  const addNote = useAddNote(applicationId);
  const deleteNote = useDeleteNote(applicationId);

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    addNote.mutate(body, {
      onSuccess: () => {
        setBody("");
      },
    });
  };

  const addError =
    getFieldError(addNote.error, "body") ??
    (addNote.error instanceof ApiError ? addNote.error.message : null);
  const deleteError = deleteNote.error instanceof ApiError ? deleteNote.error.message : null;

  return (
    <section className="rounded-lg border border-line bg-surface p-5 shadow-xs">
      <h2 className="mb-3 text-base font-semibold text-ink">Notlar</h2>
      <form onSubmit={handleSubmit} noValidate>
        <label htmlFor={textareaId} className="sr-only">
          Not ekle
        </label>
        <textarea
          id={textareaId}
          rows={3}
          maxLength={MAX_NOTE_LENGTH}
          placeholder="Değerlendirme notu ekleyin"
          value={body}
          onChange={(event) => {
            setBody(event.target.value);
          }}
          className="w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-xs text-ink-subtle">
            {body.length}/{MAX_NOTE_LENGTH}
          </span>
          <Button type="submit" size="sm" loading={addNote.isPending} disabled={!body.trim()}>
            Not ekle
          </Button>
        </div>
        {addError && (
          <p role="alert" className="mt-1 text-xs text-danger">
            {addError}
          </p>
        )}
      </form>

      {deleteError && (
        <p role="alert" className="mt-2 text-xs text-danger">
          {deleteError}
        </p>
      )}

      {notes.length === 0 ? (
        <p className="mt-4 text-sm text-ink-muted">Henüz not yok.</p>
      ) : (
        <ul className="mt-4 divide-y divide-line">
          {notes.map((note) => (
            <li key={note.id} className="py-3">
              <div className="flex items-start justify-between gap-2">
                <p className="text-xs text-ink-subtle">
                  <span className="font-medium text-ink-muted">{note.author_name}</span> ·{" "}
                  {formatDateTime(note.created_at)}
                </p>
                {/* F10: silme yalnızca yazara görünür; sunucu da başkasına 403 döner. */}
                {note.author_id === currentUserId && (
                  <button
                    type="button"
                    aria-label="Notu sil"
                    onClick={() => {
                      deleteNote.mutate(note.id);
                    }}
                    className="rounded-md p-1 text-ink-subtle hover:bg-fill-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-accent-500"
                  >
                    <Trash2 size={16} strokeWidth={1.75} />
                  </button>
                )}
              </div>
              <p className="mt-1 text-sm whitespace-pre-line text-ink">{note.body}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
