import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";

import { ApiError } from "../api/client.ts";

const ME_KEY = ["auth", "me"] as const;

export function createQueryClient(): QueryClient {
  // Oturum süresi (8 saat) herhangi bir istekte dolarsa kullanıcıyı giriş sayfasına düşürür.
  const handleError = (error: unknown) => {
    if (error instanceof ApiError && error.status === 401) {
      queryClient.setQueryData(ME_KEY, null);
    }
  };

  const queryClient: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: handleError }),
    mutationCache: new MutationCache({ onError: handleError }),
    defaultOptions: {
      queries: {
        // 4xx yanıtları tekrar denemek sonucu değiştirmez; yalnızca ağ/sunucu hatası denenir.
        retry: (failureCount, error) =>
          !(error instanceof ApiError && error.status < 500) && failureCount < 2,
        refetchOnWindowFocus: false,
      },
    },
  });
  return queryClient;
}
