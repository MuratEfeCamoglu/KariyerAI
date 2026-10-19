export function FieldMessage({ error }: { error: string | undefined }) {
  return error === undefined ? null : <p className="mt-1 text-xs text-danger">{error}</p>;
}
