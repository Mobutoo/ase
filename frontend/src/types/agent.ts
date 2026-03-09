export type AgentActionStatus = 'pending' | 'approved' | 'rejected' | 'executed' | 'failed';
export type AgentActionKind =
  | 'create_event'
  | 'update_event'
  | 'delete_event'
  | 'send_notification'
  | 'book_transport'
  | 'set_reminder';

export interface AgentAction {
  id: string;
  circleId: string;
  kind: AgentActionKind;
  status: AgentActionStatus;
  payload: Record<string, unknown>;
  summary: string;
  createdAt: string;
  resolvedAt?: string;
  resolvedBy?: string;
}

export interface MemberPreference {
  userId: string;
  circleId: string;
  agentAutoApprove: boolean;
  quietHoursStart?: string; // HH:MM
  quietHoursEnd?: string;   // HH:MM
  preferredReminderChannel: 'push' | 'telegram' | 'email';
  defaultEventVisibility: 'family' | 'adults_only' | 'private';
}

export interface NotificationPreference {
  id: string;
  userId: string;
  channel: 'push' | 'telegram' | 'email';
  enabled: boolean;
  eventTypes: string[];
  advanceMinutes: number;
}
