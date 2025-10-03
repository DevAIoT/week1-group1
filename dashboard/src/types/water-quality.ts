export interface SpectrumReading {
  sensorType?: string;
  channels: Record<string, number>;
  average?: number | null;
  readingsCount?: number | null;
}

export interface WaterQualityData {
  timestamp: string;
  location: string;
  turbidity?: number | null;
  spectrum?: SpectrumReading | null;
}

export interface WaterQualityStatus {
  status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
  issues: string[];
  score: number;
}

export interface HistoricalDataPoint {
  time: string;
  turbidity: number | null;
  spectrumAverage?: number | null;
}
