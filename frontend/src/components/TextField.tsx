import { useId, type InputHTMLAttributes } from "react";

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | undefined;
  hint?: string;
}

export function TextField({ label, error, hint, className = "", ...props }: TextFieldProps) {
  const id = useId();
  const messageId = `${id}-message`;
  const message = error ?? hint;

  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1 block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error !== undefined}
        aria-describedby={message === undefined ? undefined : messageId}
        className={`h-10 w-full rounded-md border bg-surface px-3 text-sm text-ink placeholder:text-ink-subtle focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 ${error === undefined ? "border-line-strong" : "border-danger"}`}
        {...props}
      />
      {message !== undefined && (
        <p
          id={messageId}
          className={`mt-1 text-xs ${error === undefined ? "text-ink-subtle" : "text-danger"}`}
        >
          {message}
        </p>
      )}
    </div>
  );
}
