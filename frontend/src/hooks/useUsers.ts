import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createUser, listUsers, updateUser } from "../api/users.ts";
import type { UserUpdate } from "../types/user.ts";

export const userKeys = {
  all: ["users"] as const,
};

export function useUsers() {
  return useQuery({ queryKey: userKeys.all, queryFn: listUsers });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.all }),
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UserUpdate }) => updateUser(id, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: userKeys.all }),
  });
}
