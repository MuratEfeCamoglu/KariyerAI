export type UserRole = "admin" | "recruiter" | "seeker";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_approved: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserCreate {
  email: string;
  full_name: string;
  password: string;
  role: UserRole;
}

export interface UserUpdate {
  full_name?: string;
  role?: UserRole;
  is_active?: boolean;
  password?: string;
}

export type AccountType = "seeker" | "recruiter";

export interface RegisterRequest {
  email: string;
  full_name: string;
  password: string;
  account_type: AccountType;
}

export interface PendingApproval {
  status: "pending_approval";
}

/** İş arayan kaydı oturum açar (User); İK kaydı yönetici onayını bekler. */
export type RegisterResult = User | PendingApproval;

export function isPendingApproval(result: RegisterResult): result is PendingApproval {
  return "status" in result;
}
