import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { listApplications, rescoreJob, retryApplication } from "../api/applications.ts";
import type { ApplicationFilters, ApplicationList } from "../types/application.ts";
import { jobKeys } from "./useJobs.ts";

/** F7d: işlenen kayıt varken 5 sn'de bir yenile; kalmayınca dur. */
export const AUTO_REFRESH_MS = 5000;

export function refetchIntervalFor(data: ApplicationList | undefined): number | false {
  return data !== undefined && data.processing_count > 0 ? AUTO_REFRESH_MS : false;
}

// jobKeys.all altında: CV yükleme ve ilan güncellemesi listeyi de geçersiz kılar.
export const applicationKeys = {
  list: (jobId: number, filters: ApplicationFilters, page: number) =>
    [...jobKeys.all, "applications", jobId, filters, page] as const,
  byJob: (jobId: number) => [...jobKeys.all, "applications", jobId] as const,
};

export function useApplications(jobId: number, filters: ApplicationFilters, page: number) {
  return useQuery({
    queryKey: applicationKeys.list(jobId, filters, page),
    queryFn: () => listApplications(jobId, filters, page),
    // Filtre değişirken tablo boşalıp titremesin.
    placeholderData: keepPreviousData,
    refetchInterval: (query) => refetchIntervalFor(query.state.data),
  });
}

export function useRetryApplication(jobId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: retryApplication,
    onSettled: () => queryClient.invalidateQueries({ queryKey: applicationKeys.byJob(jobId) }),
  });
}

export function useRescoreJob(jobId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => rescoreJob(jobId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}
