// Requêtes du chatbot IA (phase 8). L'historique est personnel et calculé par
// le backend ; une question renvoie la question et la réponse enregistrées, on
// les ajoute au cache plutôt que de relire tout l'historique.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from '../api/client.ts'
import type { ChatMessage } from '../api/types.ts'

const CHAT_PATH = '/api/v1/organizations/{organization_id}/chat/messages' as const

export const chatKeys = {
  history: (organizationId: string) => ['chat', organizationId] as const,
}

export function useChatHistory(organizationId: string | null) {
  return useQuery({
    queryKey: chatKeys.history(organizationId ?? ''),
    queryFn: () =>
      unwrap(api.GET(CHAT_PATH, { params: { path: { organization_id: organizationId as string } } })),
    enabled: Boolean(organizationId),
    retry: false,
    refetchOnWindowFocus: false,
  })
}

export function useAskAssistant(organizationId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (content: string) =>
      unwrap(
        api.POST(CHAT_PATH, {
          params: { path: { organization_id: organizationId } },
          body: { content },
        }),
      ),
    onSuccess: (saved) =>
      queryClient.setQueryData<ChatMessage[]>(chatKeys.history(organizationId), (previous) => [
        ...(previous ?? []),
        ...saved,
      ]),
  })
}
