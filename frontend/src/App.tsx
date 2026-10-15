import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router";

import { createQueryClient } from "./lib/queryClient.ts";
import { router } from "./router.tsx";

const queryClient = createQueryClient();

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
