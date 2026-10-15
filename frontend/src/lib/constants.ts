import type { UserRole } from "../types/user.ts";

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  recruiter: "İK Uzmanı",
};

export const ROLE_OPTIONS: UserRole[] = ["recruiter", "admin"];

export const MIN_PASSWORD_LENGTH = 10;
