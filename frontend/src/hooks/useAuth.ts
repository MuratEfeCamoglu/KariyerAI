import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getMe, login, logout, register } from "../api/auth.ts";

export const authKeys = {
  me: ["auth", "me"] as const,
};

export function useCurrentUser() {
  return useQuery({ queryKey: authKeys.me, queryFn: getMe, staleTime: Infinity });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: login,
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: register,
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      // Önceki kullanıcının verisi önbellekte kalıp bir sonraki oturumda görünmesin.
      queryClient.clear();
      queryClient.setQueryData(authKeys.me, null);
    },
  });
}
