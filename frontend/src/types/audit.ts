export interface AuditLogEntry {
  id: number;
  actor_id: number | null;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: number | null;
  payload: Record<string, unknown>;
  created_at: string;
}
