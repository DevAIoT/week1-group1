export interface WaterQualityData {
  timestamp: string;
  turbidity: number;
  light_intensity: number;
  location: string;
}

export interface WaterQualityStatus {
  status: 'excellent' | 'good' | 'fair' | 'poor' | 'critical';
  issues: string[];
  score: number;
}

export interface HistoricalDataPoint {
  time: string;
  turbidity: number;
  lightIntensity: number;
}
