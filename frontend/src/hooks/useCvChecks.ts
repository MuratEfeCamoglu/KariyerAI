import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCvCheck,
  deleteCvCheck,
  getCvCheck,
  listCvChecks,
  retryCvCheck,
} from "../api/cvChecks.ts";
import type { CvCheckListItem } from "../types/cvCheck.ts";
import { AUTO_REFRESH_MS } from "./useApplications.ts";

export const cvCheckKeys = {
  all: ["cv-checks"] as const,
  list: () => [...cvCheckKeys.all, "list"] as const,
  detail: (id: number) => [...cvCheckKeys.all, "detail", id] as const,
};

export function isProcessing(check: Pick<CvCheckListItem, "parse_status" | "score_status">) {
  const active = (status: string) => status === "pending" || status === "processing";
  return (
    active(check.parse_status) || (check.parse_status === "done" && active(check.score_status))
  );
}

export function useCvChecks() {
  return useQuery({
    queryKey: cvCheckKeys.list(),
    queryFn: listCvChecks,
    refetchInterval: (query) =>
      query.state.data?.some(isProcessing) === true ? AUTO_REFRESH_MS : false,
  });
}

export function useCvCheck(id: number) {
  return useQuery({
    queryKey: cvCheckKeys.detail(id),
    queryFn: () => getCvCheck(id),
    refetchInterval: (query) =>
      query.state.data !== undefined && isProcessing(query.state.data) ? AUTO_REFRESH_MS : false,
  });
}

export function useCreateCvCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createCvCheck,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cvCheckKeys.list() }),
  });
}

export function useRetryCvCheck(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => retryCvCheck(id),
    onSettled: () => queryClient.invalidateQueries({ queryKey: cvCheckKeys.all }),
  });
}

export function useDeleteCvCheck() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCvCheck,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: cvCheckKeys.list() }),
  });
}
