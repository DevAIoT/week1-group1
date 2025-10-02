'use client';

import { useEffect, useRef, useState } from 'react';
import type { WaterQualityData } from '@/types/water-quality';

// WebSocket bridge server URL
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
const HISTORY_LIMIT = 100;
const HISTORY_URL = deriveHistoryUrl(WS_URL);

type HistoryMessage = {
  type: 'history';
  data?: unknown;
};

function deriveHistoryUrl(wsUrl: string): string | null {
  try {
    const url = new URL(wsUrl);
    url.protocol = url.protocol === 'wss:' ? 'https:' : 'http:';
    url.pathname = '/history';
    url.search = '';
    url.hash = '';
    return url.toString();
  } catch (err) {
    console.warn('Invalid WebSocket URL, cannot derive history endpoint', err);
    return null;
  }
}

function numericOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function normalizeTimestamp(value: unknown): string | null {
  const toISOString = (input: Date): string | null => {
    if (Number.isNaN(input.getTime())) {
      return null;
    }
    try {
      return input.toISOString();
    } catch {
      return null;
    }
  };

  if (value instanceof Date) {
    return toISOString(value);
  }

  if (typeof value === 'number') {
    return toISOString(new Date(value));
  }

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) {
      return null;
    }
    return toISOString(new Date(trimmed));
  }

  return null;
}

function normalizeWaterQualityData(raw: unknown): WaterQualityData | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const data = raw as Record<string, unknown>;
  const timestampValue = data.timestamp ?? data.time;
  const turbidityValue = data.turbidity;
  const lightValue = data.light_intensity ?? data.lightIntensity ?? data.light;

  if (!timestampValue) {
    return null;
  }

  const timestamp = normalizeTimestamp(timestampValue);
  if (!timestamp) {
    return null;
  }

  const turbidity = numericOrNull(turbidityValue);
  const light_intensity = numericOrNull(lightValue);

  if (turbidity === null || light_intensity === null) {
    return null;
  }

  const location = typeof data.location === 'string' ? data.location : 'unknown';

  return {
    timestamp,
    turbidity,
    light_intensity,
    location,
  };
}

function mergeByTimestamp(
  current: WaterQualityData[],
  incoming: WaterQualityData[],
  limit = HISTORY_LIMIT,
): WaterQualityData[] {
  if (!incoming.length) {
    return current;
  }

  const map = new Map<string, WaterQualityData>();
  for (const entry of current) {
    map.set(entry.timestamp, entry);
  }
  for (const entry of incoming) {
    map.set(entry.timestamp, entry);
  }

  return Array.from(map.values())
    .sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )
    .slice(-limit);
}

export function useMQTTWaterQuality() {
  const [latestData, setLatestData] = useState<WaterQualityData | null>(null);
  const [historicalData, setHistoricalData] = useState<WaterQualityData[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const historyFetchStateRef = useRef<'idle' | 'pending' | 'done'>('idle');

  useEffect(() => {
    let mounted = true;

    const applyHistory = (entries: WaterQualityData[]) => {
      if (!mounted || !entries.length) {
        return;
      }

      const historyLatest = entries[entries.length - 1];

      setHistoricalData((prev) => mergeByTimestamp(prev, entries));
      setLatestData((prev) => {
        if (!prev) {
          return historyLatest;
        }

        const prevTime = new Date(prev.timestamp).getTime();
        const newTime = new Date(historyLatest.timestamp).getTime();

        return newTime >= prevTime ? historyLatest : prev;
      });

      historyFetchStateRef.current = 'done';
    };

    const fetchInitialHistory = async () => {
      if (!HISTORY_URL) {
        historyFetchStateRef.current = 'done';
        return;
      }

      if (historyFetchStateRef.current === 'pending' || historyFetchStateRef.current === 'done') {
        return;
      }

      historyFetchStateRef.current = 'pending';

      try {
        const response = await fetch(HISTORY_URL, { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`History request failed with status ${response.status}`);
        }
        const payload = await response.json();
        if (!mounted) {
          return;
        }

        const rawEntries = Array.isArray(payload?.data) ? payload.data : [];
        const normalized = rawEntries
          .map(normalizeWaterQualityData)
          .filter((item: WaterQualityData | null): item is WaterQualityData => item !== null);

        if (normalized.length) {
          applyHistory(normalized);
        }

        historyFetchStateRef.current = 'done';
      } catch (err) {
        console.error('Failed to fetch history:', err);
        historyFetchStateRef.current = 'idle';
      }
    };

    const connect = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!mounted) return;
          console.log('Connected to WebSocket bridge');
          setConnected(true);
          setError(null);
          void fetchInitialHistory();
        };

        ws.onmessage = (event) => {
          if (!mounted) return;
          try {
            const message = JSON.parse(event.data) as
              | HistoryMessage
              | Record<string, unknown>;

            if (message && typeof message === 'object' && 'type' in message) {
              if (message.type === 'history' && Array.isArray(message.data)) {
                const normalized = (message.data as unknown[])
                  .map(normalizeWaterQualityData)
                  .filter(
                    (item: WaterQualityData | null): item is WaterQualityData => item !== null,
                  );
                if (normalized.length) {
                  applyHistory(normalized);
                } else {
                  historyFetchStateRef.current = 'done';
                }
              }
              return;
            }

            const normalized = normalizeWaterQualityData(message);
            if (!normalized) {
              console.warn('Received invalid water quality payload:', message);
              return;
            }

            setLatestData(normalized);
            setHistoricalData((prev) =>
              mergeByTimestamp(prev, [normalized]),
            );
          } catch (err) {
            console.error('Error parsing message:', err);
          }
        };

        ws.onerror = (event) => {
          if (!mounted) return;
          console.error('WebSocket error:', event);
          setError('WebSocket connection error');
          setConnected(false);
        };

        ws.onclose = () => {
          if (!mounted) return;
          console.log('WebSocket disconnected');
          setConnected(false);

          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mounted) {
              console.log('Attempting to reconnect...');
              connect();
            }
          }, 5000);
        };

      } catch (err) {
        console.error('Failed to connect to WebSocket:', err);
        setError('Failed to connect to WebSocket bridge');

        // Retry connection
        reconnectTimeoutRef.current = setTimeout(() => {
          if (mounted) {
            connect();
          }
        }, 5000);
      }
    };

    connect();

    return () => {
      mounted = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { latestData, historicalData, connected, error };
}
