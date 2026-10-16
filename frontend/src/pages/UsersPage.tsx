import { KeyRound, UserPlus } from "lucide-react";
import { useState, type SubmitEvent } from "react";

import { ApiError, getFieldError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { Modal } from "../components/Modal.tsx";
import { PageHeader } from "../components/PageHeader.tsx";
import { TextField } from "../components/TextField.tsx";
import { useCurrentUser } from "../hooks/useAuth.ts";
import { useCreateUser, useUpdateUser, useUsers } from "../hooks/useUsers.ts";
import { MIN_PASSWORD_LENGTH, ROLE_LABELS, ROLE_OPTIONS } from "../lib/constants.ts";
import type { User, UserRole } from "../types/user.ts";

function formError(error: unknown): string | null {
  if (!error) {
    return null;
  }
  return error instanceof ApiError ? error.message : "Beklenmeyen bir hata oluştu.";
}

function ErrorBanner({ message }: { message: string | null }) {
  if (message === null) {
    return null;
  }
  return (
    <div
      role="alert"
      className="mb-4 rounded-md border border-danger/20 bg-danger-bg px-3 py-2 text-sm text-danger"
    >
      {message}
    </div>
  );
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const createUser = useCreateUser();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("recruiter");

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    createUser.mutate(
      { full_name: fullName.trim(), email: email.trim(), password, role },
      { onSuccess: onClose },
    );
  };

  return (
    <Modal title="Kullanıcı ekle" onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        <ErrorBanner message={formError(createUser.error)} />
        <TextField
          label="Ad soyad"
          value={fullName}
          error={getFieldError(createUser.error, "full_name")}
          onChange={(event) => {
            setFullName(event.target.value);
          }}
        />
        <TextField
          label="E-posta"
          type="email"
          value={email}
          error={getFieldError(createUser.error, "email")}
          onChange={(event) => {
            setEmail(event.target.value);
          }}
        />
        <TextField
          label="Geçici şifre"
          type="password"
          autoComplete="new-password"
          value={password}
          hint={`En az ${String(MIN_PASSWORD_LENGTH)} karakter. Kullanıcıya siz iletin.`}
          error={getFieldError(createUser.error, "password")}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
        <div>
          <label htmlFor="new-user-role" className="mb-1 block text-sm font-medium text-ink">
            Rol
          </label>
          <select
            id="new-user-role"
            value={role}
            onChange={(event) => {
              setRole(event.target.value as UserRole);
            }}
            className="h-10 w-full rounded-md border border-line-strong bg-surface px-3 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
          >
            {ROLE_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {ROLE_LABELS[option]}
              </option>
            ))}
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Vazgeç
          </Button>
          <Button type="submit" loading={createUser.isPending}>
            Kullanıcı ekle
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function SetPasswordModal({ user, onClose }: { user: User; onClose: () => void }) {
  const updateUser = useUpdateUser();
  const [password, setPassword] = useState("");

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    updateUser.mutate({ id: user.id, body: { password } }, { onSuccess: onClose });
  };

  return (
    <Modal title={`Şifre belirle: ${user.full_name}`} onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        <ErrorBanner message={formError(updateUser.error)} />
        <TextField
          label="Yeni şifre"
          type="password"
          autoComplete="new-password"
          value={password}
          hint={`En az ${String(MIN_PASSWORD_LENGTH)} karakter.`}
          error={getFieldError(updateUser.error, "password")}
          onChange={(event) => {
            setPassword(event.target.value);
          }}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Vazgeç
          </Button>
          <Button type="submit" loading={updateUser.isPending}>
            Kaydet
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export function UsersPage() {
  const { data: currentUser } = useCurrentUser();
  const users = useUsers();
  const updateUser = useUpdateUser();
  const [creating, setCreating] = useState(false);
  const [passwordFor, setPasswordFor] = useState<User | null>(null);

  return (
    <>
      <PageHeader
        title="Kullanıcılar"
        actions={
          <Button
            onClick={() => {
              setCreating(true);
            }}
          >
            <UserPlus size={16} strokeWidth={1.75} aria-hidden="true" />
            Kullanıcı ekle
          </Button>
        }
      />

      <ErrorBanner message={formError(updateUser.error)} />

      <div className="overflow-x-auto rounded-lg border border-line bg-surface shadow-xs">
        {users.isPending ? (
          <p className="p-6 text-sm text-ink-muted">Yükleniyor…</p>
        ) : users.isError ? (
          <p className="p-6 text-sm text-ink-muted">Kullanıcılar yüklenemedi.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-fill-muted text-xs font-medium text-ink-muted">
              <tr>
                <th className="px-4 py-3">Ad soyad</th>
                <th className="px-4 py-3">E-posta</th>
                <th className="px-4 py-3">Rol</th>
                <th className="px-4 py-3">Durum</th>
                <th className="px-4 py-3">
                  <span className="sr-only">İşlemler</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.data.map((user) => {
                const isSelf = user.id === currentUser?.id;
                return (
                  <tr key={user.id} className="border-b border-line last:border-0">
                    <td className="px-4 py-3 font-medium text-ink">
                      {user.full_name}
                      {isSelf && <span className="ml-2 text-xs text-ink-subtle">(siz)</span>}
                    </td>
                    <td className="px-4 py-3 text-ink-muted">{user.email}</td>
                    <td className="px-4 py-3">
                      <select
                        aria-label={`${user.full_name} rolü`}
                        value={user.role}
                        // Kendi rolünü düşüren admin bu sayfaya erişimini kaybeder.
                        disabled={isSelf}
                        onChange={(event) => {
                          updateUser.mutate({
                            id: user.id,
                            body: { role: event.target.value as UserRole },
                          });
                        }}
                        className="h-8 rounded-md border border-line-strong bg-surface px-2 text-sm disabled:opacity-50"
                      >
                        {ROLE_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {ROLE_LABELS[option]}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        role="switch"
                        aria-checked={user.is_active}
                        aria-label={`${user.full_name} aktif`}
                        disabled={isSelf}
                        title={isSelf ? "Kendi hesabınızı pasifleştiremezsiniz" : undefined}
                        onClick={() => {
                          updateUser.mutate({
                            id: user.id,
                            body: { is_active: !user.is_active },
                          });
                        }}
                        className="inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        <span
                          className={`relative h-5 w-9 rounded-full transition-colors ${user.is_active ? "bg-accent-500" : "bg-line-strong"}`}
                        >
                          <span
                            className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-xs transition-all ${user.is_active ? "left-4.5" : "left-0.5"}`}
                          />
                        </span>
                        <span className="text-ink-muted">{user.is_active ? "Aktif" : "Pasif"}</span>
                      </button>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setPasswordFor(user);
                        }}
                      >
                        <KeyRound size={16} strokeWidth={1.75} aria-hidden="true" />
                        Şifre belirle
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {creating && (
        <CreateUserModal
          onClose={() => {
            setCreating(false);
          }}
        />
      )}
      {passwordFor && (
        <SetPasswordModal
          user={passwordFor}
          onClose={() => {
            setPasswordFor(null);
          }}
        />
      )}
    </>
  );
}
