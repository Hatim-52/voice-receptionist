import type { TranscriptItem } from '../types';

export type TranscriptEventInput =
  | {
      type: 'transcript';
      role: 'user' | 'assistant';
      text: string;
      isFinal?: boolean;
      timestamp?: string;
    }
  | {
      type: 'agent_turn_end';
    };

let seqCounter = 0;

function nextTranscriptId(): string {
  seqCounter += 1;
  return `t-${Date.now()}-${seqCounter}`;
}

function stripTrailingPunct(text: string): string {
  return text.trim().replace(/[-.,!?]+$/, '').trim();
}

function isSameOrContinuation(prevText: string, nextText: string): boolean {
  const a = prevText.trim();
  const b = nextText.trim();
  if (!a || !b) return false;
  if (b === a || b.startsWith(a)) return true;
  const aBase = stripTrailingPunct(a);
  return aBase.length > 0 && b.startsWith(aBase);
}

/**
 * Merge streamed LLM/TTS text chunks into a single coherent agent turn bubble.
 */
export function mergeAgentChunks(existing: string, incoming: string): string {
  const aTrim = existing.trim();
  const bTrim = incoming.trim();
  if (!aTrim) return bTrim;
  if (!bTrim) return aTrim;

  if (aTrim === bTrim || aTrim.endsWith(bTrim)) {
    return aTrim;
  }
  if (bTrim.startsWith(aTrim)) {
    return bTrim;
  }

  // Respect explicit leading/trailing whitespace on raw streaming tokens
  if (/\s$/.test(existing) || /^\s/.test(incoming)) {
    return `${existing}${incoming}`.trim();
  }

  // Attach punctuation directly (e.g. "Hello" + "!")
  if (/^[.,!?;:)'"\]]/.test(bTrim)) {
    return `${aTrim}${bTrim}`;
  }

  // Default: join sentence/phrase chunks (e.g. "Dr." + "Priya Sharma...") with a single space
  return `${aTrim} ${bTrim}`;
}

function finalizeOpenAssistant(items: TranscriptItem[]): TranscriptItem[] {
  const last = items[items.length - 1];
  if (!last || last.role !== 'assistant' || last.isFinal !== false) {
    return items;
  }
  return [...items.slice(0, -1), { ...last, isFinal: true }];
}

/**
 * Pure reducer for phone-call transcript bubbles:
 * - Interim caller transcripts update the active caller bubble in place; final commits it.
 * - Duplicate/prefix-matching caller messages replace the previous caller bubble.
 * - Agent text chunks accumulate into a single bubble per turn until agent_turn_end or next caller turn.
 */
export function reduceTranscript(
  prev: TranscriptItem[],
  event: TranscriptEventInput
): TranscriptItem[] {
  if (event.type === 'agent_turn_end') {
    return finalizeOpenAssistant(prev);
  }

  const trimmed = event.text.trim();
  if (!trimmed) {
    return prev;
  }

  const nowTs = event.timestamp || new Date().toLocaleTimeString();

  if (event.role === 'user') {
    const isFinal = event.isFinal ?? true;
    const base = finalizeOpenAssistant(prev);
    const last = base[base.length - 1];

    if (last && last.role === 'user') {
      if (last.isFinal === false || isSameOrContinuation(last.text, trimmed)) {
        return [
          ...base.slice(0, -1),
          {
            ...last,
            text: trimmed,
            isFinal: last.isFinal === true ? true : isFinal,
            timestamp: event.timestamp || last.timestamp,
          },
        ];
      }
    }

    return [
      ...base,
      {
        id: nextTranscriptId(),
        role: 'user',
        text: trimmed,
        timestamp: nowTs,
        isFinal,
      },
    ];
  }

  // Agent ('assistant') speech accumulation
  const isFinal = event.isFinal ?? false;
  const last = prev[prev.length - 1];

  if (last && last.role === 'assistant') {
    if (last.isFinal === false) {
      return [
        ...prev.slice(0, -1),
        {
          ...last,
          text: mergeAgentChunks(last.text, event.text),
          isFinal,
          timestamp: event.timestamp || last.timestamp,
        },
      ];
    }

    // Committed assistant turn: de-duplicate exact/substring SSE echoes
    const lastTrim = last.text.trim();
    if (lastTrim === trimmed || lastTrim.includes(trimmed) || trimmed.startsWith(lastTrim)) {
      return [
        ...prev.slice(0, -1),
        {
          ...last,
          text: mergeAgentChunks(last.text, event.text),
          isFinal: true,
          timestamp: event.timestamp || last.timestamp,
        },
      ];
    }
  }

  return [
    ...prev,
    {
      id: nextTranscriptId(),
      role: 'assistant',
      text: trimmed,
      timestamp: nowTs,
      isFinal,
    },
  ];
}
