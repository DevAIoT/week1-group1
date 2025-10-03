/**
 * Raw turbidity reading from sensor - can be voltage or NTU
 */
export interface TurbidityReading {
  /** Raw voltage reading from sensor (if voltage-based sensor) */
  voltage?: number;
  /** Direct NTU reading (if NTU sensor or pre-converted) */
  ntu?: number;
}

export interface SpectrumReading {
  sensorType?: string;
  channels: Record<string, number>;
  average?: number | null;
  readingsCount?: number | null;
}

export interface WaterQualityData {
  timestamp: string;
  location: string;
  turbidity?: TurbidityReading | null;
  pH?: number | null;
  spectrum?: SpectrumReading | null;
}

export interface WaterQualityStatus {
  status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
  issues: string[];
  score: number;
  /** Computed turbidity in NTU (converted from voltage if needed) */
  turbidityNTU?: number | null;
  /** Raw voltage reading (for display purposes) */
  turbidityVoltage?: number | null;
}

export interface HistoricalDataPoint {
  time: string;
  turbidity: number | null;
  turbidityVoltage?: number | null;
  pH?: number | null;
  spectrumAverage?: number | null;
}
