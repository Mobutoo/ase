import type { CircleMember } from "./circle";

export interface CalendarEvent {
  id: string;
  uid: string;
  calendarId: string;
  parentEventId?: string;
  title: string;
  description: string;
  location: string;
  startAt: string; // ISO 8601
  endAt: string;
  allDay: boolean;
  eventType: 'event' | 'recurring' | 'background' | 'task' | 'dependent';
  displayMode: 'normal' | 'background' | 'private' | 'shared';
  visibility: 'family' | 'adults_only' | 'private' | 'custom';
  recurrenceRule?: string;
  members: CircleMember[];
  linkedTaskId?: string;
  dependentType?: 'transport' | 'meal' | 'accompany' | 'break';
  bookingRef?: { provider: string; bookingId: string; amount: number; currency: string };
  validatedBy?: CircleMember;
  validatedAt?: string;
  reminders: EventReminder[];
}

export interface Calendar {
  id: string;
  ownerId: string;
  name: string;
  color: string;
  icon: string;
  visibility: string;
  caldavEnabled: boolean;
}

export interface EventReminder {
  id: string;
  offsetMinutes: number;
  channel: 'push' | 'telegram' | 'email';
}

export type CalendarView = 'day' | 'week' | 'month' | 'agenda';
