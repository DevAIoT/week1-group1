'use client';

import { useEffect, useRef, useState } from 'react';
import type { SpectrumReading, WaterQualityData } from '@/types/water-quality';

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

function parseSpectrumChannels(raw: unknown): Record<string, number> | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }

  const result: Record<string, number> = {};
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    const numeric = numericOrNull(value);
    if (numeric !== null) {
      result[key] = numeric;
    }
  }

  return Object.keys(result).length ? result : null;
}

function mergeSpectrumReadings(
  previous?: SpectrumReading | null,
  incoming?: SpectrumReading | null,
): SpectrumReading | null | undefined {
  if (!previous && !incoming) {
    return undefined;
  }
  if (!previous) {
    return incoming ?? undefined;
  }
  if (!incoming) {
    return previous ?? undefined;
  }

  const channels: Record<string, number> = { ...previous.channels };
  for (const [key, value] of Object.entries(incoming.channels)) {
    channels[key] = value;
  }

  return {
    sensorType: incoming.sensorType ?? previous.sensorType,
    channels,
    average: incoming.average ?? previous.average ?? null,
    readingsCount: incoming.readingsCount ?? previous.readingsCount ?? null,
  };
}

function mergeWaterQualityEntries(
  current: WaterQualityData | undefined,
  incoming: WaterQualityData,
): WaterQualityData {
  if (!current) {
    return incoming;
  }

  const mergedTimestamp =
    new Date(incoming.timestamp).getTime() >= new Date(current.timestamp).getTime()
      ? incoming.timestamp
      : current.timestamp;

  return {
    ...current,
    ...incoming,
    timestamp: mergedTimestamp,
    location: incoming.location !== 'unknown' ? incoming.location : current.location,
    turbidity: incoming.turbidity ?? current.turbidity,
    spectrum:
      mergeSpectrumReadings(current.spectrum, incoming.spectrum) ??
      current.spectrum ??
      incoming.spectrum,
  };
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
  const spectrumObject =
    typeof data.spectrum === 'object' && data.spectrum !== null
      ? (data.spectrum as Record<string, unknown>)
      : typeof data.spectrum_sensor === 'object' && data.spectrum_sensor !== null
        ? (data.spectrum_sensor as Record<string, unknown>)
        : typeof data.spectrumSensor === 'object' && data.spectrumSensor !== null
          ? (data.spectrumSensor as Record<string, unknown>)
          : undefined;
  const spectrumChannels = parseSpectrumChannels(
    data.channels ?? spectrumObject?.channels ?? spectrumObject?.Channels,
  );
  const spectrumAverage = numericOrNull(
    data.spectrum_average ??
    data.spectrumAverage ??
    spectrumObject?.average ??
    spectrumObject?.avg ??
    spectrumObject?.mean,
  );
  const spectrumReadingsCount = numericOrNull(
    data.readings_count ??
    data.readingsCount ??
    spectrumObject?.readings_count ??
    spectrumObject?.readingsCount ??
    spectrumObject?.count ??
    spectrumObject?.samples,
  );
  const sensorType = typeof data.sensor_type === 'string'
    ? data.sensor_type
    : typeof data.sensorType === 'string'
      ? data.sensorType
      : typeof spectrumObject?.sensor_type === 'string'
        ? (spectrumObject.sensor_type as string)
        : typeof spectrumObject?.sensorType === 'string'
          ? (spectrumObject.sensorType as string)
          : undefined;

  if (!timestampValue) {
    return null;
  }

  const timestamp = normalizeTimestamp(timestampValue);
  if (!timestamp) {
    return null;
  }

  const turbidity = numericOrNull(turbidityValue);

  const location = typeof data.location === 'string' ? data.location : 'unknown';

  const hasTurbidity = turbidity !== null;
  const hasSpectrum =
    !!spectrumChannels || spectrumAverage !== null || spectrumReadingsCount !== null;

  if (!hasTurbidity && !hasSpectrum) {
    return null;
  }

  const normalized: WaterQualityData = {
    timestamp,
    location,
  };

  if (turbidity !== null) {
    normalized.turbidity = turbidity;
  }

  if (hasSpectrum) {
    const channelValues = spectrumChannels ? Object.values(spectrumChannels) : [];
    const derivedAverage = channelValues.length
      ? channelValues.reduce((acc, value) => acc + value, 0) / channelValues.length
      : null;

    normalized.spectrum = {
      sensorType,
      channels: spectrumChannels ?? {},
      average: spectrumAverage ?? derivedAverage,
      readingsCount: spectrumReadingsCount,
    };
  }

  return normalized;
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
    const existing = map.get(entry.timestamp);
    map.set(entry.timestamp, mergeWaterQualityEntries(existing, entry));
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

            setLatestData((prev) => {
              if (!prev) {
                return normalized;
              }

              const incomingTime = new Date(normalized.timestamp).getTime();
              const previousTime = new Date(prev.timestamp).getTime();

              if (incomingTime >= previousTime) {
                return mergeWaterQualityEntries(prev, normalized);
              }

              return prev;
            });
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
