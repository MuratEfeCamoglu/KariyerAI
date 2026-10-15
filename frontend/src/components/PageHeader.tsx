import type { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  actions?: ReactNode;
}

export function PageHeader({ title, actions }: PageHeaderProps) {
  return (
    <header className="mb-6 flex items-center justify-between gap-4">
      <h1 className="text-[1.75rem] leading-9 font-semibold text-ink">{title}</h1>
      {actions}
    </header>
  );
}
