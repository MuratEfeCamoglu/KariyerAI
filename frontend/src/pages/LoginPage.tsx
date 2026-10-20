import { useState, type SubmitEvent } from "react";
import { Link, Navigate, useLocation } from "react-router";

import { ApiError } from "../api/client.ts";
import { Button } from "../components/Button.tsx";
import { TextField } from "../components/TextField.tsx";
import { useCurrentUser, useLogin } from "../hooks/useAuth.ts";
import { homePathFor } from "../lib/constants.ts";
import type { UserRole } from "../types/user.ts";

function redirectTarget(state: unknown, role: UserRole): string {
  if (typeof state === "object" && state !== null && "from" in state) {
    const { from } = state;
    if (typeof from === "string" && from.startsWith("/") && from !== "/login") {
      return from;
    }
  }
  return homePathFor(role);
}

export function LoginPage() {
  const { data: user } = useCurrentUser();
  const login = useLogin();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (user) {
    return <Navigate to={redirectTarget(location.state, user.role)} replace />;
  }

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    login.mutate({ email: email.trim(), password });
  };

  const errorMessage =
    login.error instanceof ApiError && login.error.status !== 422
      ? login.error.message
      : login.error
        ? "E-posta veya şifre hatalı"
        : null;

  return (
    <main className="flex min-h-screen bg-canvas">
      <section className="hidden w-1/2 flex-col justify-between bg-brand-700 p-12 text-white lg:flex">
        <p className="text-xl font-semibold">KariyerAI</p>
        <div>
          <h2 className="text-3xl font-semibold">CV değerlendirmede kanıtlı, tutarlı öneriler</h2>
          <p className="mt-4 max-w-md text-base text-brand-100">
            İş arayanlar CV'lerini hedefledikleri işe göre geliştirir; işverenler adayları gerekçeli
            bir uyum puanıyla sıralar. Son karar her zaman insanındır.
          </p>
        </div>
        <p className="text-sm text-brand-100">
          AI çıktısı öneridir; kanıtı doğrulanamayan kalem karşılanmamış sayılır.
        </p>
      </section>

      <section className="flex flex-1 items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold text-ink">Giriş yap</h1>
          <p className="mt-1 text-sm text-ink-muted">KariyerAI hesabınızla devam edin.</p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit} noValidate>
            {errorMessage && (
              <div
                role="alert"
                className="rounded-md border border-danger/20 bg-danger-bg px-3 py-2 text-sm text-danger"
              >
                {errorMessage}
              </div>
            )}
            <TextField
              label="E-posta"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => {
                setEmail(event.target.value);
              }}
            />
            <TextField
              label="Şifre"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => {
                setPassword(event.target.value);
              }}
            />
            <Button
              type="submit"
              className="w-full"
              loading={login.isPending}
              disabled={email.trim() === "" || password === ""}
            >
              Giriş yap
            </Button>
          </form>

          <p className="mt-6 text-sm text-ink-muted">
            Hesabın yok mu?{" "}
            <Link to="/register" className="font-medium text-accent-700 hover:underline">
              Kayıt ol
            </Link>
          </p>
          <p className="mt-2 text-sm text-ink-subtle">
            İK uzmanları da kaydolabilir; hesaplar yönetici onayıyla açılır.
          </p>
          <p className="mt-2 text-sm text-ink-subtle">
            Şifrenizi mi unuttunuz? Yöneticinize başvurun.
          </p>
        </div>
      </section>
    </main>
  );
}
