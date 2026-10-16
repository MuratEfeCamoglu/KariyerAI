import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  addNote,
  changeStatus,
  deleteCandidate,
  deleteNote,
  getApplication,
  listApplications,
  rescoreJob,
  retryApplication,
} from "../api/applications.ts";
import type {
  ApplicationDetail,
  ApplicationFilters,
  ApplicationList,
  ApplicationStatus,
} from "../types/application.ts";
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

export function useRetryApplication() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: retryApplication,
    onSettled: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}

export function useRescoreJob(jobId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => rescoreJob(jobId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}

export const detailKey = (id: number) => [...jobKeys.all, "application", id] as const;

function isActive(detail: ApplicationDetail | undefined): boolean {
  if (detail === undefined) return false;
  const active = (status: string) => status === "pending" || status === "processing";
  return active(detail.candidate.parse_status) || active(detail.score_status);
}

export function useApplication(id: number) {
  return useQuery({
    queryKey: detailKey(id),
    queryFn: () => getApplication(id),
    // Ayrıştırma/puanlama sürerken detay da kendini yeniler (F7d ile aynı kural).
    refetchInterval: (query) => (isActive(query.state.data) ? AUTO_REFRESH_MS : false),
  });
}

export function useChangeStatus(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (status: ApplicationStatus) => changeStatus(id, status),
    onSuccess: (detail) => {
      queryClient.setQueryData(detailKey(id), detail);
      return queryClient.invalidateQueries({ queryKey: applicationKeys.byJob(detail.job.id) });
    },
  });
}

export function useAddNote(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: string) => addNote(applicationId, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: detailKey(applicationId) }),
  });
}

export function useDeleteNote(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteNote,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: detailKey(applicationId) }),
  });
}

export function useDeleteCandidate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteCandidate,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}
