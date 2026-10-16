import { useQuery } from "@tanstack/react-query";

import { listAuditLogs } from "../api/audit.ts";

export function useAuditLogs() {
  return useQuery({ queryKey: ["audit"] as const, queryFn: listAuditLogs });
}
