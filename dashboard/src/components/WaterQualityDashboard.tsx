'use client';

import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Droplets, AlertTriangle, CheckCircle2, Wifi, WifiOff, BarChart3, Activity, Info } from 'lucide-react';
import { useMQTTWaterQuality } from '@/hooks/useMQTTWaterQuality';
import {
    analyzeWaterQuality,
    getStatusColor,
    getStatusLabel,
    TURBIDITY_CLEAN,
    TURBIDITY_MODERATE,
} from '@/lib/water-quality-analyzer';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { ConfettiSideCannons } from '@/components/ui/confetti';
import {
    Tooltip as UITooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from '@/components/ui/tooltip';
import type { HistoricalDataPoint, WaterQualityStatus } from '@/types/water-quality';

const BAD_STATUSES = new Set<WaterQualityStatus['status']>(['poor', 'critical']);
const GOOD_STATUSES = new Set<WaterQualityStatus['status']>(['good', 'excellent']);
const BAD_DURATION_MS = 15_000;
const MIN_BAD_SAMPLES = 3;

/**
 * Get information about a spectral channel based on wavelength
 */
function getChannelInfo(channel: string): { description: string; importance: string } {
    const channelLower = channel.toLowerCase();

    // UV region (200-400 nm)
    if (channelLower.includes('254') || channelLower.includes('uv')) {
        return {
            description: 'UV Light (254 nm)',
            importance: 'Primary indicator of organic matter and dissolved organic carbon (DOC). Lower absorption means cleaner water.'
        };
    }

    // Visible region - Violet/Blue (400-500 nm)
    if (channelLower.includes('450') || channelLower.includes('blue') || channelLower.includes('violet')) {
        return {
            description: 'Blue Light (450 nm)',
            importance: 'Detects suspended particles and color compounds. Useful for identifying algae and other contaminants.'
        };
    }

    // Visible region - Green (500-570 nm)
    if (channelLower.includes('500') || channelLower.includes('550') || channelLower.includes('green')) {
        return {
            description: 'Green Light (500-550 nm)',
            importance: 'Sensitive to chlorophyll and algae presence. Important for detecting biological contamination.'
        };
    }

    // Visible region - Orange/Red (580-650 nm)
    if (channelLower.includes('580') || channelLower.includes('610') || channelLower.includes('red') || channelLower.includes('orange')) {
        return {
            description: 'Red/Orange Light (580-650 nm)',
            importance: 'Critical for bacterial contamination and particle detection. Key wavelength for water quality monitoring.'
        };
    }

    // NIR region (700-1000 nm)
    if (channelLower.includes('860') || channelLower.includes('nir') || channelLower.includes('infrared')) {
        return {
            description: 'Near-Infrared (860 nm)',
            importance: 'Supplementary contamination indicator. Helps detect organic and inorganic particles.'
        };
    }

    // Generic fallback
    return {
        description: channel,
        importance: 'Spectral measurement for water quality analysis. Higher values generally indicate better light transmission through water.'
    };
}

export function WaterQualityDashboard() {
    const { latestData, historicalData, connected, mqttConnected, error } = useMQTTWaterQuality();
    const [celebrationKey, setCelebrationKey] = useState(0);
    const recoveryStateRef = useRef({
        badSince: null as number | null,
        badSamples: 0,
        awaitingRecovery: false,
        lastProcessedTimestamp: null as string | null,
    });

    // Run analysis to get computed values - ALL business logic is in the analyzer
    const analysis = latestData ? analyzeWaterQuality(latestData) : null;

    // Extract display values from analyzed data
    const turbidityValue = analysis?.turbidityNTU ?? null;
    const turbidityVoltage = analysis?.turbidityVoltage ?? null;
    const pHValue = typeof latestData?.pH === 'number' ? latestData.pH : null;
    const spectrumAverage = typeof latestData?.spectrum?.average === 'number' ? latestData.spectrum.average : null;
    const spectrumChannels = latestData?.spectrum?.channels ?? null;
    const spectrumReadingsCount = typeof latestData?.spectrum?.readingsCount === 'number'
        ? latestData.spectrum.readingsCount
        : null;
    const spectrumSensorName = latestData?.spectrum?.sensorType ?? 'Spectral Sensor';
    const channelEntries = spectrumChannels
        ? Object.entries(spectrumChannels).sort(([a], [b]) => a.localeCompare(b))
        : [];
    const hasSpectrumChannels = channelEntries.length > 0;
    const spectralValues = channelEntries.map(([, value]) => value);
    const spectrumMin = spectralValues.length ? Math.min(...spectralValues) : null;
    const spectrumMax = spectralValues.length ? Math.max(...spectralValues) : null;

    const statusColor = analysis ? getStatusColor(analysis.status) : 'hsl(var(--muted))';
    const statusLabel = analysis ? getStatusLabel(analysis.status) : 'No Data';
    const status = analysis?.status ?? null;
    const latestTimestamp = latestData?.timestamp ?? null;

    useEffect(() => {
        if (!status || !latestTimestamp) {
            return;
        }

        const state = recoveryStateRef.current;
        if (state.lastProcessedTimestamp === latestTimestamp) {
            return;
        }

        state.lastProcessedTimestamp = latestTimestamp;

        const readingTime = new Date(latestTimestamp).getTime();
        const timestampMs = Number.isFinite(readingTime) ? readingTime : Date.now();
        const isBad = BAD_STATUSES.has(status);
        const isGood = GOOD_STATUSES.has(status);

        if (isBad) {
            if (state.badSince === null) {
                state.badSince = timestampMs;
                state.badSamples = 0;
            }
            state.badSamples += 1;

            const sustainedDuration = state.badSince !== null ? timestampMs - state.badSince : 0;
            if (sustainedDuration >= BAD_DURATION_MS || state.badSamples >= MIN_BAD_SAMPLES) {
                state.awaitingRecovery = true;
            }
            return;
        }

        state.badSince = null;
        state.badSamples = 0;

        if (isGood && state.awaitingRecovery) {
            state.awaitingRecovery = false;
            setCelebrationKey((prev) => prev + 1);
        }
    }, [status, latestTimestamp]);

    // Prepare chart data - compute turbidity for each historical point
    const chartData: HistoricalDataPoint[] = historicalData.slice(-20).map((data) => {
        // Run analyzer on each historical point to get computed turbidity
        const historicalAnalysis = analyzeWaterQuality(data);
        const pHPoint = typeof data.pH === 'number' ? data.pH : null;
        const spectrumPoint = typeof data.spectrum?.average === 'number' ? data.spectrum.average : null;

        return {
            time: format(new Date(data.timestamp), 'HH:mm:ss'),
            turbidity: historicalAnalysis.turbidityNTU ?? null,
            turbidityVoltage: historicalAnalysis.turbidityVoltage ?? null,
            pH: pHPoint,
            spectrumAverage: spectrumPoint,
        };
    });

    const hasTurbidityHistory = chartData.some((point) => point.turbidity !== null);
    const hasSpectrumHistory = chartData.some((point) => point.spectrumAverage !== null);
    const hasPHHistory = chartData.some((point) => point.pH !== null);

    // Calculate progress bars and display ranges
    // Use 100 NTU as max for progress bar (anything above 100 is severely contaminated)
    const maxTurbidityForProgress = 100;
    const turbidityProgress = turbidityValue !== null ? Math.min((turbidityValue / maxTurbidityForProgress) * 100, 100) : 0;
    const isPHNormal = pHValue !== null && pHValue >= 6.5 && pHValue <= 8.5;
    const isPHOptimal = pHValue !== null && pHValue >= 7.0 && pHValue <= 8.5;
    const pHProgress = pHValue !== null ? ((pHValue - 0) / 14) * 100 : 0;

    return (
        <TooltipProvider>
            <div className="min-h-screen bg-background">
                <ConfettiSideCannons fireKey={celebrationKey} />
                <div className="w-full">
                    {/* Header */}
                    <div className="sticky top-0 z-10 flex items-center justify-between px-4 sm:px-6 py-1 sm:py-2 border-b bg-card/95 backdrop-blur-sm shadow-sm">
                        <div>
                            <h1 className="text-lg sm:text-xl font-bold tracking-tight">AquaAware</h1>
                            <p className="text-[10px] sm:text-[11px] text-muted-foreground mt-0.5 font-medium">Real-time environmental analysis</p>
                        </div>
                        <div className="flex items-center gap-2 sm:gap-3">
                            <div className="flex items-center gap-1 sm:gap-1.5">
                                {connected ? (
                                    <Wifi className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-green-500" />
                                ) : (
                                    <WifiOff className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-red-500" />
                                )}
                                <Badge
                                    variant="outline"
                                    className={cn(
                                        "text-[10px] sm:text-xs px-1.5 sm:px-2 py-0",
                                        connected
                                            ? "bg-green-500/10 text-green-700 border-green-500/20"
                                            : "bg-red-500/10 text-red-700 border-red-500/20"
                                    )}
                                >
                                    WebSocket
                                </Badge>
                            </div>
                            <div className="flex items-center gap-1 sm:gap-1.5">
                                {mqttConnected ? (
                                    <Wifi className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-green-500" />
                                ) : (
                                    <WifiOff className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-red-500" />
                                )}
                                <Badge
                                    variant="outline"
                                    className={cn(
                                        "text-[10px] sm:text-xs px-1.5 sm:px-2 py-0",
                                        mqttConnected
                                            ? "bg-green-500/10 text-green-700 border-green-500/20"
                                            : "bg-red-500/10 text-red-700 border-red-500/20"
                                    )}
                                >
                                    MQTT
                                </Badge>
                            </div>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6 space-y-2 sm:space-y-4">

                        {error && (
                            <Alert variant="destructive" className="mb-4">
                                <AlertTriangle className="h-4 w-4" />
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}

                        {/* Overall Status Card */}
                        <Card className="border-2 shadow-sm" style={{ borderColor: statusColor }}>
                            <CardHeader className="pb-2 bg-muted/20">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-xs font-bold uppercase tracking-widest">Overall Water Quality</CardTitle>
                                    {latestData && (
                                        <span className="text-xs text-muted-foreground">
                                            {format(new Date(latestData.timestamp), 'PPp')}
                                        </span>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="flex flex-col lg:flex-row items-start gap-4 lg:gap-6">
                                    <div className="flex-1 w-full">
                                        <div className="flex items-center gap-3 mb-3">
                                            {analysis?.status === 'excellent' || analysis?.status === 'good' ? (
                                                <div className="p-2 rounded-full bg-current/10" style={{ color: statusColor }}>
                                                    <CheckCircle2 className="h-5 w-5" style={{ color: statusColor }} />
                                                </div>
                                            ) : (
                                                <div className="p-2 rounded-full bg-current/10" style={{ color: statusColor }}>
                                                    <AlertTriangle className="h-5 w-5" style={{ color: statusColor }} />
                                                </div>
                                            )}
                                            <div>
                                                <div className="text-xl font-bold tracking-tight" style={{ color: statusColor }}>
                                                    {statusLabel}
                                                </div>
                                                <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
                                                    {latestData?.location || 'Unknown location'}
                                                </div>
                                            </div>
                                        </div>

                                        <div className="space-y-1.5">
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="text-muted-foreground font-medium">Quality Score</span>
                                                <span className="font-bold">{analysis?.score ?? 0}/100</span>
                                            </div>
                                            <Progress value={analysis?.score ?? 0} className="h-1.5" />
                                        </div>
                                    </div>

                                    {analysis && analysis.issues.length > 0 && (
                                        <div className="flex-1 w-full space-y-1.5">
                                            <div className="text-xs font-semibold text-muted-foreground mb-1.5">Detected Issues</div>
                                            {analysis.issues.map((issue, idx) => (
                                                <Alert key={idx} className="py-1.5">
                                                    <AlertTriangle className="h-3.5 w-3.5" />
                                                    <AlertDescription className="text-xs">{issue}</AlertDescription>
                                                </Alert>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Metrics Grid */}
                        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-2">
                            {/* Turbidity Card */}
                            <Card className="hover:shadow-md transition-shadow">
                                <CardHeader className="flex flex-row items-center justify-between pb-2 bg-muted/20">
                                    <div className="flex items-center gap-1.5">
                                        <CardTitle className="text-[10px] font-bold uppercase tracking-widest">Turbidity Level</CardTitle>
                                        <UITooltip>
                                            <TooltipTrigger asChild>
                                                <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                                            </TooltipTrigger>
                                            <TooltipContent className="max-w-xs">
                                                <p className="font-semibold mb-1">Turbidity Measurement</p>
                                                <p className="text-xs">Measures water cloudiness caused by suspended particles. Lower values indicate clearer, safer water. WHO guideline: &lt; 5.0 NTU for drinking water.</p>
                                            </TooltipContent>
                                        </UITooltip>
                                    </div>
                                    <div className="p-1.5 rounded-md bg-blue-500/10">
                                        <Droplets className="h-3.5 w-3.5 text-blue-600" />
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        <div className="flex items-baseline gap-1.5">
                                            <div className="text-3xl font-bold tabular-nums tracking-tight">
                                                {turbidityValue !== null ? turbidityValue.toFixed(2) : '--'}
                                            </div>
                                            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">NTU</div>
                                        </div>

                                        <div className="space-y-1">
                                            {turbidityVoltage !== null && (
                                                <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wide">
                                                    Sensor Voltage: {turbidityVoltage.toFixed(3)} V
                                                </div>
                                            )}
                                            <Progress
                                                value={turbidityProgress}
                                                className="h-1"
                                            />
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* pH Level Card */}
                            {/* <Card className="hover:shadow-md transition-shadow">
                                <CardHeader className="flex flex-row items-center justify-between pb-2 bg-muted/20">
                                    <div className="flex items-center gap-1.5">
                                        <CardTitle className="text-[10px] font-bold uppercase tracking-widest">pH Level</CardTitle>
                                        <UITooltip>
                                            <TooltipTrigger asChild>
                                                <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                                            </TooltipTrigger>
                                            <TooltipContent className="max-w-xs">
                                                <p className="font-semibold mb-1">pH Measurement</p>
                                                <p className="text-xs">Measures water acidity/alkalinity on a 0-14 scale. Safe range: 6.5-8.5 (WHO standard). Optimal: 7.0-8.5 for drinking water.</p>
                                            </TooltipContent>
                                        </UITooltip>
                                    </div>
                                    <div className="p-1.5 rounded-md bg-green-500/10">
                                        <Activity className="h-3.5 w-3.5 text-green-600" />
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-2">
                                        <div className="flex items-baseline gap-1.5">
                                            <div className="text-3xl font-bold tabular-nums tracking-tight">
                                                {pHValue !== null ? pHValue.toFixed(2) : '--'}
                                            </div>
                                            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">pH</div>
                                        </div>

                                        <div className="space-y-1">
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="text-muted-foreground font-medium">Range: 6.5 - 8.5</span>
                                                <Badge
                                                    variant={pHValue === null ? "outline" : isPHNormal ? (isPHOptimal ? "outline" : "secondary") : "destructive"}
                                                    className="text-[10px] px-1.5 py-0 h-4"
                                                >
                                                    {pHValue === null ? 'No Data' : isPHNormal ? (isPHOptimal ? 'Optimal' : 'Acceptable') : 'Abnormal'}
                                                </Badge>
                                            </div>
                                            <Progress
                                                value={pHProgress}
                                                className="h-1"
                                            />
                                        </div>

                                        <Separator className="my-2" />

                                        <div className="grid grid-cols-3 gap-2 text-center">
                                            <div>
                                                <div className="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Acidic</div>
                                                <div className="text-xs font-semibold tabular-nums">&lt; 6.5</div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Optimal</div>
                                                <div className="text-xs font-semibold tabular-nums">7.0 - 8.5</div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Alkaline</div>
                                                <div className="text-xs font-semibold tabular-nums">&gt; 8.5</div>
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card> */}

                            {/* Spectral Breakdown Card */}
                            <Card className="hover:shadow-md transition-shadow">
                                <CardHeader className="flex flex-row items-center justify-between pb-2 bg-muted/20">
                                    <div className="flex items-center gap-1.5">
                                        <CardTitle className="text-[10px] font-bold uppercase tracking-widest">Spectral Breakdown</CardTitle>
                                        <UITooltip>
                                            <TooltipTrigger asChild>
                                                <Info className="h-3 w-3 text-muted-foreground cursor-help" />
                                            </TooltipTrigger>
                                            <TooltipContent className="max-w-xs">
                                                <p className="font-semibold mb-1">Spectral Analysis</p>
                                                <p className="text-xs">Measures light transmission at different wavelengths. UV (254nm) detects organic matter, visible light (450-650nm) detects particles and color, NIR (860nm) identifies contaminants. Higher transmission = cleaner water.</p>
                                            </TooltipContent>
                                        </UITooltip>
                                    </div>
                                    <div className="p-1.5 rounded-md bg-purple-500/10">
                                        <BarChart3 className="h-3.5 w-3.5 text-purple-600" />
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between text-xs">
                                            <span className="text-muted-foreground font-medium">{spectrumSensorName}</span>
                                            {spectrumReadingsCount !== null && Number.isFinite(spectrumReadingsCount) && (
                                                <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                                                    {`${Math.round(spectrumReadingsCount)} samples`}
                                                </Badge>
                                            )}
                                        </div>

                                        <div className="flex items-baseline gap-1.5">
                                            <div className="text-3xl font-bold tabular-nums tracking-tight">
                                                {spectrumAverage !== null ? spectrumAverage.toFixed(2) : '--'}
                                            </div>
                                            <div className="text-[10px] text-muted-foreground font-bold uppercase tracking-wider">avg units</div>
                                        </div>

                                        {hasSpectrumChannels ? (
                                            <div className="grid grid-cols-3 gap-2">
                                                {channelEntries.map(([channel, value]) => {
                                                    const channelInfo = getChannelInfo(channel);
                                                    return (
                                                        <UITooltip key={channel}>
                                                            <TooltipTrigger asChild>
                                                                <div className="rounded-md border px-2 py-1 text-center cursor-help hover:border-primary/50 transition-colors">
                                                                    <div className="text-[10px] text-muted-foreground uppercase tracking-wide">{channel}</div>
                                                                    <div className="text-xs font-semibold tabular-nums">{value.toFixed(2)}</div>
                                                                </div>
                                                            </TooltipTrigger>
                                                            <TooltipContent className="max-w-xs">
                                                                <p className="font-semibold mb-1">{channelInfo.description}</p>
                                                                <p className="text-xs">{channelInfo.importance}</p>
                                                                <p className="text-xs mt-1 text-muted-foreground">Current: {value.toFixed(2)} units</p>
                                                            </TooltipContent>
                                                        </UITooltip>
                                                    );
                                                })}
                                            </div>
                                        ) : (
                                            <div className="text-xs text-muted-foreground">
                                                No spectral channel readings received yet.
                                            </div>
                                        )}

                                        {(spectrumMin !== null || spectrumMax !== null) && (
                                            <div className="grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium">Min</span>
                                                    <span className="text-foreground font-semibold tabular-nums">
                                                        {spectrumMin !== null ? spectrumMin.toFixed(2) : '--'}
                                                    </span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="font-medium">Max</span>
                                                    <span className="text-foreground font-semibold tabular-nums">
                                                        {spectrumMax !== null ? spectrumMax.toFixed(2) : '--'}
                                                    </span>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Historical Data Chart */}
                        {chartData.length > 0 && (
                            <Card className="hover:shadow-md transition-shadow">
                                <CardHeader className="bg-muted/20">
                                    <CardTitle className="text-xs font-bold uppercase tracking-widest">Historical Trends</CardTitle>
                                    <p className="text-[10px] text-muted-foreground font-medium">Last 20 readings</p>
                                </CardHeader>
                                <CardContent className="pt-6">
                                    <div className="h-[300px] sm:h-[350px] w-full">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={chartData} margin={{ top: 10, right: 70, left: 20, bottom: 20 }}>
                                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                                <XAxis
                                                    dataKey="time"
                                                    className="text-xs"
                                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                                                    height={40}
                                                />
                                                <YAxis
                                                    yAxisId="left"
                                                    className="text-xs"
                                                    width={45}
                                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                                                    label={{ value: 'Turbidity', angle: -90, position: 'insideLeft', style: { fill: 'hsl(var(--muted-foreground))', fontSize: 10, textAnchor: 'middle' } }}
                                                />
                                                {hasPHHistory && (
                                                    <YAxis
                                                        yAxisId="center"
                                                        className="text-xs"
                                                        width={40}
                                                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                                                        label={{ value: 'pH', angle: -90, position: 'insideLeft', offset: 10, style: { fill: 'hsl(var(--muted-foreground))', fontSize: 10, textAnchor: 'middle' } }}
                                                        domain={[0, 14]}
                                                    />
                                                )}
                                                {hasSpectrumHistory && (
                                                    <YAxis
                                                        yAxisId="right"
                                                        orientation="right"
                                                        className="text-xs"
                                                        width={60}
                                                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                                                        label={{ value: 'Spectral', angle: 90, position: 'insideRight', style: { fill: 'hsl(var(--muted-foreground))', fontSize: 10, textAnchor: 'middle' } }}
                                                    />
                                                )}
                                                <Tooltip
                                                    contentStyle={{
                                                        backgroundColor: 'hsl(var(--card))',
                                                        border: '1px solid hsl(var(--border))',
                                                        borderRadius: '8px',
                                                    }}
                                                />
                                                <Legend />
                                                {hasTurbidityHistory && (
                                                    <Line
                                                        yAxisId="left"
                                                        type="monotone"
                                                        dataKey="turbidity"
                                                        stroke="hsl(221, 83%, 53%)"
                                                        strokeWidth={2}
                                                        name="Turbidity"
                                                        dot={{ r: 2 }}
                                                        activeDot={{ r: 4 }}
                                                    />
                                                )}
                                                {hasPHHistory && (
                                                    <Line
                                                        yAxisId="center"
                                                        type="monotone"
                                                        dataKey="pH"
                                                        stroke="hsl(142, 76%, 36%)"
                                                        strokeWidth={2}
                                                        name="pH Level"
                                                        dot={{ r: 2 }}
                                                        activeDot={{ r: 4 }}
                                                    />
                                                )}
                                                {hasSpectrumHistory && (
                                                    <Line
                                                        yAxisId="right"
                                                        type="monotone"
                                                        dataKey="spectrumAverage"
                                                        stroke="hsl(271, 76%, 65%)"
                                                        strokeWidth={2}
                                                        name="Spectral Average"
                                                        dot={{ r: 2 }}
                                                        activeDot={{ r: 4 }}
                                                    />
                                                )}
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        {/* No Data State */}
                        {!latestData && connected && (
                            <Card>
                                <CardContent className="py-8 text-center">
                                    <AlertTriangle className="h-10 w-10 text-muted-foreground mx-auto mb-3" />
                                    <div className="text-sm font-semibold mb-1">Waiting for sensor data...</div>
                                    <p className="text-xs text-muted-foreground">
                                        Make sure the sensor is publishing data to the MQTT broker.
                                    </p>
                                </CardContent>
                            </Card>
                        )}

                    </div>
                </div>
            </div>
        </TooltipProvider>
    );
}
