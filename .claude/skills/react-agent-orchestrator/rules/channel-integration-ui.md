---
title: Channel Integration UI
impact: HIGH
impactDescription: Yuno mandates at least one external channel (WhatsApp/Telegram/Slack) — the UI side is config + transcript, the wire side stays backend
tags: channels, whatsapp, telegram, slack, integration
---

## Channel Integration UI

Frontend handles channel **configuration** and **transcript display**. The backend owns webhooks, signature verification, and message delivery.

### Channel types

```ts
// entities/channel/model/channel.types.ts
export type ChannelKind = "whatsapp" | "telegram" | "slack";

export type ChannelStatus = "disconnected" | "connecting" | "connected" | "error";

export type Channel = {
  id: ChannelId;
  kind: ChannelKind;
  displayName: string;
  status: ChannelStatus;
  config: ChannelConfig;
  lastError?: string;
  connectedAt?: string;
};

export type ChannelConfig =
  | { kind: "whatsapp"; phoneNumberId: string; businessAccountId: string }
  | { kind: "telegram"; botUsername: string }
  | { kind: "slack"; teamId: string; botUserId: string };
```

Secrets (API tokens, app secrets, webhook secrets) are never in this type — they live encrypted backend-side and are submitted via dedicated `POST /channels/:id/credentials` calls.

### Module: `modules/channel-registry/`

```txt
modules/channel-registry/
  ui/
    ChannelRegistryPage.tsx
    ChannelList.tsx
    ConnectChannelDialog.tsx       # picks kind, then mounts the right form
    WhatsappConfigForm.tsx
    TelegramConfigForm.tsx
    SlackConfigForm.tsx
    ChannelStatusBadge.tsx
    ChannelTranscript.tsx          # backed by channel events from runs
  model/
    channel-registry.store.ts
  index.ts
```

### Feature: `features/connect-channel/`

Reused inside the agent stepper (step 6) and agent editor (channels panel). Lists available channels for selection — does not create channels itself.

### Transcript view

The Yuno spec requires persisted, visible message history. Combine two sources:

1. **Historical messages** — `GET /channels/:id/messages?cursor=...` (TanStack Query, infinite query)
2. **Live messages** — `channel.inbound` / `channel.outbound` events from the active run stream ([[realtime-run-events]])

```tsx
const messages = useChannelMessages(channelId);     // paginated history
useRunEventStream(activeRunId);                     // pushes new events into cache

// Render combined list, sorted by `at`
```

### Connect flow

```
[ Connect Channel ] → pick kind → fill provider-specific form → POST /channels
                                                                ↓
                                              backend returns webhook URL
                                                                ↓
                                  user pastes URL into Meta / Telegram / Slack
                                                                ↓
                                       webhook verification ping
                                                                ↓
                              backend marks channel "connected", FE polls/queries
```

### Demo wiring rule

For the Yuno demo, at least one agent in the workflow has `channelIds` including the connected channel. The runtime must route `agent.message` events with channel scope through `channel.outbound`. This is backend-controlled; the frontend just verifies the transcript reflects both sides of the conversation.

See: [[realtime-run-events]], [[agent-editor-layout]]
