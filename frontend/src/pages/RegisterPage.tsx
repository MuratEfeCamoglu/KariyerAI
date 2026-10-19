import { useState, type SubmitEvent } from "react";
import { Link, Navigate } from "react-router";

import { ApiError, getFieldError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { TextField } from "../components/TextField.tsx";
import { useCurrentUser, useRegister } from "../hooks/useAuth.ts";
import { homePathFor, MIN_PASSWORD_LENGTH } from "../lib/constants.ts";

/** Herkese açık kayıt; açılan hesap her zaman iş arayan hesabıdır. */
export function RegisterPage() {
  const { data: user } = useCurrentUser();
  const register = useRegister();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (user) {
    return <Navigate to={homePathFor(user.role)} replace />;
  }

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    register.mutate({ full_name: fullName.trim(), email: email.trim(), password });
  };

  const error = register.error;
  const summary =
    error instanceof ApiError && Object.keys(error.fieldErrors).length === 0
      ? error.message
      : error && !(error instanceof ApiError)
        ? "Beklenmeyen bir hata oluştu. Lütfen tekrar deneyin."
        : null;

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas p-8">
      <div className="w-full max-w-sm">
        <p className="text-lg font-semibold text-brand-700">KariyerAI</p>
        <h1 className="mt-6 text-2xl font-semibold text-ink">Kayıt ol</h1>
        <p className="mt-1 text-sm text-ink-muted">
          CV'ni hedeflediğin işe göre değerlendir, eksiklerini gör.
        </p>

        <form className="mt-8 space-y-4" onSubmit={handleSubmit} noValidate>
          {summary && (
            <div
              role="alert"
              className="rounded-md border border-danger/20 bg-danger-bg px-3 py-2 text-sm text-danger"
            >
              {summary}
            </div>
          )}
          <TextField
            label="Ad soyad"
            autoComplete="name"
            required
            value={fullName}
            error={getFieldError(error, "full_name")}
            onChange={(event) => {
              setFullName(event.target.value);
            }}
          />
          <TextField
            label="E-posta"
            type="email"
            autoComplete="email"
            required
            value={email}
            error={getFieldError(error, "email")}
            onChange={(event) => {
              setEmail(event.target.value);
            }}
          />
          <TextField
            label="Şifre"
            type="password"
            autoComplete="new-password"
            required
            hint={`En az ${String(MIN_PASSWORD_LENGTH)} karakter`}
            value={password}
            error={getFieldError(error, "password")}
            onChange={(event) => {
              setPassword(event.target.value);
            }}
          />
          <Button
            type="submit"
            className="w-full"
            loading={register.isPending}
            disabled={fullName.trim() === "" || email.trim() === "" || password === ""}
          >
            Hesap oluştur
          </Button>
        </form>

        <p className="mt-6 text-sm text-ink-muted">
          Zaten hesabın var mı?{" "}
          <Link to="/login" className="font-medium text-accent-700 hover:underline">
            Giriş yap
          </Link>
        </p>
      </div>
    </main>
  );
}
