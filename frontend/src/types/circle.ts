export type CirclePreset = 'family' | 'colocation' | 'team' | 'club' | 'custom';
export type MembershipType = 'local' | 'federated';

export interface Circle {
  id: string;
  name: string;
  preset: CirclePreset;
  tenantId: string;
  isPrimary: boolean;
  timezone: string;
  agentEnabled: boolean;
  agentBudgetLimit: number;
}

export interface CircleMember {
  id: string;
  userId: string;
  circleId: string;
  role: string;
  displayName: string;
  avatarColor: string;
  avatarEmoji: string;
  membershipType: MembershipType;
  inviteAcceptedAt?: string;
}
