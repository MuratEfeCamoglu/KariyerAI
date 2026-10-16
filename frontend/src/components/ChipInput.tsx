import { X } from "lucide-react";
import { useId, useState, type KeyboardEvent } from "react";

import { foldText } from "../lib/format.ts";

interface ChipInputProps {
  label: string;
  value: string[];
  onChange: (value: string[]) => void;
  max: number;
  error?: string | undefined;
  placeholder?: string;
}

export function ChipInput({ label, value, onChange, max, error, placeholder }: ChipInputProps) {
  const id = useId();
  const messageId = `${id}-message`;
  const [draft, setDraft] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const full = value.length >= max;

  const commit = () => {
    const chip = draft.trim();
    if (chip === "") {
      return;
    }
    if (value.some((existing) => foldText(existing) === foldText(chip))) {
      setLocalError(`"${chip}" zaten ekli`);
      return;
    }
    onChange([...value, chip]);
    setDraft("");
    setLocalError(null);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commit();
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  const message = localError ?? error;

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </label>
        <span className="text-xs text-ink-subtle">
          {value.length}/{max}
        </span>
      </div>
      <div
        className={`flex min-h-10 flex-wrap items-center gap-2 rounded-md border bg-surface px-2 py-1.5 focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-accent-500 ${message === undefined ? "border-line-strong" : "border-danger"}`}
      >
        {value.map((chip) => (
          <span
            key={chip}
            className="inline-flex items-center gap-1 rounded-full bg-brand-50 py-0.5 pr-1 pl-2.5 text-sm text-brand-700"
          >
            {chip}
            <button
              type="button"
              aria-label={`${chip} kaldır`}
              onClick={() => {
                onChange(value.filter((item) => item !== chip));
              }}
              className="rounded-full p-0.5 hover:bg-brand-100 focus-visible:outline-2 focus-visible:outline-accent-500"
            >
              <X size={14} strokeWidth={1.75} />
            </button>
          </span>
        ))}
        <input
          id={id}
          value={draft}
          disabled={full}
          placeholder={full ? `En fazla ${String(max)}` : placeholder}
          aria-invalid={message !== undefined}
          aria-describedby={message ? messageId : undefined}
          onChange={(event) => {
            setDraft(event.target.value);
            setLocalError(null);
          }}
          onKeyDown={handleKeyDown}
          onBlur={commit}
          className="h-7 min-w-32 flex-1 bg-transparent text-sm text-ink outline-none placeholder:text-ink-subtle disabled:cursor-not-allowed"
        />
      </div>
      {message ? (
        <p id={messageId} className="mt-1 text-xs text-danger">
          {message}
        </p>
      ) : (
        <p className="mt-1 text-xs text-ink-subtle">Enter ile ekleyin.</p>
      )}
    </div>
  );
}
