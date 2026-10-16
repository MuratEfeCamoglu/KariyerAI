import { useId, useState } from "react";

import { ApiError } from "../api/client.ts";
import { Button } from "./Button.tsx";
import { Modal } from "./Modal.tsx";

interface ConfirmDeleteModalProps {
  candidateId: number;
  pending: boolean;
  error: unknown;
  onConfirm: () => void;
  onClose: () => void;
}

/** F11: geri alınamaz silme; yanlışlıkla tıklamayı önlemek için aday id'si yazılmalı (TASARIM §3). */
export function ConfirmDeleteModal({
  candidateId,
  pending,
  error,
  onConfirm,
  onClose,
}: ConfirmDeleteModalProps) {
  const inputId = useId();
  const [typed, setTyped] = useState("");
  const confirmed = typed.trim() === String(candidateId);
  const errorMessage =
    error instanceof ApiError ? error.message : error ? "Beklenmeyen bir hata oluştu." : null;

  return (
    <Modal title="Aday verisini kalıcı olarak sil" onClose={onClose}>
      <div className="space-y-3 text-sm text-ink-muted">
        <p>
          Bu işlem KVKK kapsamındaki silme talepleri içindir ve{" "}
          <strong className="text-ink">geri alınamaz</strong>. Adayın kaydı, tüm başvuruları,
          notları ve yüklenen CV dosyası silinir. Denetim kaydında yalnızca "aday #{candidateId}{" "}
          silindi" bilgisi kalır.
        </p>
        <label htmlFor={inputId} className="block font-medium text-ink">
          Onaylamak için aday numarasını yazın: <span className="tabular-nums">{candidateId}</span>
        </label>
        <input
          id={inputId}
          inputMode="numeric"
          autoComplete="off"
          value={typed}
          onChange={(event) => {
            setTyped(event.target.value);
          }}
          className="h-10 w-full rounded-md border border-line-strong bg-surface px-3 text-sm text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
        />
        {errorMessage && (
          <p role="alert" className="rounded-md bg-danger-bg px-3 py-2 text-danger">
            {errorMessage}
          </p>
        )}
      </div>
      <div className="mt-6 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Vazgeç
        </Button>
        <Button variant="danger" disabled={!confirmed} loading={pending} onClick={onConfirm}>
          Kalıcı olarak sil
        </Button>
      </div>
    </Modal>
  );
}
