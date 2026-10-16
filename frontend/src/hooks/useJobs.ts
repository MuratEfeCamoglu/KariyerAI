import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createJob, deleteJob, getJob, listJobs, updateJob } from "../api/jobs.ts";
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
    onSuccess: (job) => {
      queryClient.setQueryData(jobKeys.detail(job.id), job);
      return queryClient.invalidateQueries({ queryKey: jobKeys.list() });
    },
  });
}

export function useUpdateJob(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Partial<JobInput>) => updateJob(id, body),
    onSuccess: (job) => {
      queryClient.setQueryData(jobKeys.detail(id), job);
      return queryClient.invalidateQueries({ queryKey: jobKeys.list() });
    },
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
