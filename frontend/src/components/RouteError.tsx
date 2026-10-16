import { isRouteErrorResponse, Link, useRouteError } from "react-router";

/** Beklenmeyen bir hatada boş ekran yerine anlaşılır mesaj (ISKELET Aşama 7). */
export function RouteError() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-canvas p-8 text-center">
      <h1 className="text-2xl font-semibold text-ink">
        {notFound ? "Sayfa bulunamadı" : "Beklenmeyen bir hata oluştu"}
      </h1>
      <p className="max-w-md text-sm text-ink-muted">
        {notFound
          ? "Aradığınız sayfa taşınmış ya da silinmiş olabilir."
          : "Sayfayı yenilemeyi deneyin. Sorun sürerse sistem yöneticinize bildirin."}
      </p>
      <div className="flex gap-3">
        <button
          type="button"
          onClick={() => {
            window.location.reload();
          }}
          className="h-10 rounded-md border border-line-strong bg-surface px-4 text-sm font-medium text-ink hover:bg-fill-muted"
        >
          Sayfayı yenile
        </button>
        <Link
          to="/jobs"
          className="inline-flex h-10 items-center rounded-md bg-brand-700 px-4 text-sm font-medium text-white hover:bg-brand-600"
        >
          İlanlara dön
        </Link>
      </div>
    </main>
  );
}
