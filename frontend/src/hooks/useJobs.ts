import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createJob, deleteJob, getJob, listJobs, updateJob, uploadCvs } from "../api/jobs.ts";
import type { JobInput } from "../types/job.ts";

export const jobKeys = {
  all: ["jobs"] as const,
  list: () => [...jobKeys.all, "list"] as const,
  detail: (id: number) => [...jobKeys.all, "detail", id] as const,
};

export function useJobs() {
  return useQuery({ queryKey: jobKeys.list(), queryFn: listJobs });
}

export function useJob(id: number) {
  return useQuery({ queryKey: jobKeys.detail(id), queryFn: () => getJob(id) });
}

export function useCreateJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobKeys.list() }),
  });
}

export function useUpdateJob(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<JobInput>) => updateJob(id, body),
    // Detay yanıtı başvuru istatistiklerini de içerir; güncelleme yanıtı içermez, yeniden çekilir.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}

export function useDeleteJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteJob,
    onSuccess: (_data, id) => {
      queryClient.removeQueries({ queryKey: jobKeys.detail(id) });
      return queryClient.invalidateQueries({ queryKey: jobKeys.list() });
    },
  });
}

export function useUploadCvs(jobId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      files,
      onProgress,
    }: {
      files: File[];
      onProgress?: (percent: number) => void;
    }) => uploadCvs(jobId, files, onProgress),
    onSettled: () => queryClient.invalidateQueries({ queryKey: jobKeys.all }),
  });
}
