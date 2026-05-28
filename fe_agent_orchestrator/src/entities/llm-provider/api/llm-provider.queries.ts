import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { agentQueryKeys } from "@/entities/agent";
import { llmProviderApi } from "./llm-provider.service";
import type { SetLlmCredentialsInput } from "../model/llm-provider.types";

export const llmProviderQueryKeys = {
  all: ["llm-providers"] as const,
  list: () => [...llmProviderQueryKeys.all, "list"] as const,
  status: (providerKey: string) => [...llmProviderQueryKeys.all, "status", providerKey] as const,
} as const;

export function useLlmProviderCredentials() {
  return useQuery({
    queryKey: llmProviderQueryKeys.list(),
    queryFn: () => llmProviderApi.list(),
    staleTime: 60_000,
  });
}

export function useLlmProviderStatus(providerKey: string, enabled = true) {
  return useQuery({
    queryKey: llmProviderQueryKeys.status(providerKey),
    queryFn: () => llmProviderApi.getStatus(providerKey),
    enabled: enabled && Boolean(providerKey),
  });
}

type RegisterArgs = { providerKey: string } & SetLlmCredentialsInput;

export function useRegisterProviderCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ providerKey, ...input }: RegisterArgs) => llmProviderApi.registerCredential(providerKey, input),
    onSuccess: (_, vars) => {
      // Flip `isConfigured` true in capabilities + refresh both lists.
      qc.invalidateQueries({ queryKey: agentQueryKeys.capabilities() });
      qc.invalidateQueries({ queryKey: llmProviderQueryKeys.list() });
      qc.invalidateQueries({ queryKey: llmProviderQueryKeys.status(vars.providerKey) });
    },
  });
}

export function useDeleteProviderCredential() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (providerKey: string) => llmProviderApi.deleteCredential(providerKey),
    onSuccess: (_, providerKey) => {
      qc.invalidateQueries({ queryKey: agentQueryKeys.capabilities() });
      qc.invalidateQueries({ queryKey: llmProviderQueryKeys.list() });
      qc.invalidateQueries({ queryKey: llmProviderQueryKeys.status(providerKey) });
    },
  });
}
