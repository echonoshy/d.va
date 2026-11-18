export type Role = 'A' | 'B';
export type Segment = { role: Role; text: string };
export type DraftSegment = Segment & { id: number };
export type Voice = { id: string; name: string; language: string; engine: string };
export type VoiceSelection = Record<Role, Voice['id']>;
export type Busy = '' | 'script' | 'render';
export type Output = { url: string; signature: string; music: File | null };

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isRole(value: unknown): value is Role {
  return value === 'A' || value === 'B';
}

export function isSegment(value: unknown): value is Segment {
  return isRecord(value) && isRole(value.role) &&
    typeof value.text === 'string' && Boolean(value.text.trim());
}

export function isVoice(value: unknown): value is Voice {
  return isRecord(value) && typeof value.id === 'string' && typeof value.name === 'string' &&
    typeof value.language === 'string' && typeof value.engine === 'string';
}
