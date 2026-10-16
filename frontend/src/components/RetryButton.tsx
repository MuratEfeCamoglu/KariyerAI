import { RotateCcw } from "lucide-react";

import { ApiError } from "../api/client.ts";
import { useRetryApplication } from "../hooks/useApplications.ts";
import { Button } from "./Button.tsx";

export function RetryButton({ applicationId }: { applicationId: number }) {
  const retry = useRetryApplication();
  const error =
    retry.error instanceof ApiError
      ? retry.error.message
      : retry.error
        ? "Yeniden denenemedi"
        : null;
  return (
    <div className="flex flex-col items-start gap-1">
      <Button
        variant="secondary"
        size="sm"
        loading={retry.isPending}
        onClick={() => {
          retry.mutate(applicationId);
        }}
      >
        <RotateCcw size={14} strokeWidth={1.75} aria-hidden="true" />
        Yeniden dene
      </Button>
      {error && (
        <span role="alert" className="max-w-56 text-xs text-ink-muted">
          {error}
        </span>
      )}
    </div>
  );
}
