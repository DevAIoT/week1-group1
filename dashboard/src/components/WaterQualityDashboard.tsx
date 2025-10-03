'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Droplets, AlertTriangle, CheckCircle2, Wifi, WifiOff, BarChart3 } from 'lucide-react';
import { useMQTTWaterQuality } from '@/hooks/useMQTTWaterQuality';
import { analyzeWaterQuality, getStatusColor, getStatusLabel } from '@/lib/water-quality-analyzer';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { HistoricalDataPoint } from '@/types/water-quality';

export function WaterQualityDashboard() {
    const { latestData, historicalData, connected, mqttConnected, error } = useMQTTWaterQuality();

    const turbidityValue = typeof latestData?.turbidity === 'number' ? latestData.turbidity : null;
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

    const analysis = latestData ? analyzeWaterQuality(latestData) : null;
    const statusColor = analysis ? getStatusColor(analysis.status) : 'hsl(var(--muted))';
    const statusLabel = analysis ? getStatusLabel(analysis.status) : 'No Data';

    // Prepare chart data
    const chartData: HistoricalDataPoint[] = historicalData.slice(-20).map((data) => {
        const turbidityPoint = typeof data.turbidity === 'number' ? data.turbidity : null;
        const spectrumPoint = typeof data.spectrum?.average === 'number' ? data.spectrum.average : null;

        return {
            time: format(new Date(data.timestamp), 'HH:mm:ss'),
            turbidity: turbidityPoint,
            spectrumAverage: spectrumPoint,
        };
    });
    const hasSpectrumHistory = chartData.some((point) => point.spectrumAverage !== null);

    const isTurbidityNormal = turbidityValue !== null && turbidityValue <= 5.0;
    const turbidityProgress = turbidityValue !== null ? Math.min((turbidityValue / 10) * 100, 100) : 0;

    return (
        <div className="h-screen bg-background flex items-center justify-center overflow-hidden">
            <div className="w-full max-w-7xl mx-auto flex flex-col max-h-screen">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b bg-card/50 backdrop-blur-sm">
                    <div>
                        <h1 className="text-xl font-bold tracking-tight">Water Quality Monitor</h1>
                        <p className="text-[11px] text-muted-foreground mt-0.5 font-medium">Real-time environmental analysis</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5">
                            {connected ? (
                                <Wifi className="h-4 w-4 text-green-500" />
                            ) : (
                                <WifiOff className="h-4 w-4 text-red-500" />
                            )}
                            <Badge
                                variant="outline"
                                className={cn(
                                    "text-xs px-2 py-0",
                                    connected
                                        ? "bg-green-500/10 text-green-700 border-green-500/20"
                                        : "bg-red-500/10 text-red-700 border-red-500/20"
                                )}
                            >
                                WebSocket
                            </Badge>
                        </div>
                        <div className="flex items-center gap-1.5">
                            {mqttConnected ? (
                                <Wifi className="h-4 w-4 text-green-500" />
                            ) : (
                                <WifiOff className="h-4 w-4 text-red-500" />
                            )}
                            <Badge
                                variant="outline"
                                className={cn(
                                    "text-xs px-2 py-0",
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

                {/* Scrollable Content */}
                <div className="flex-1 overflow-auto">
                    <div className="h-full p-6 space-y-4">

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
                                <div className="flex items-start gap-6">
                                    <div className="flex-1">
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
                                        <div className="flex-1 space-y-1.5">
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
                                    <CardTitle className="text-[10px] font-bold uppercase tracking-widest">Turbidity Level</CardTitle>
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
                                            <div className="flex items-center justify-between text-xs">
                                                <span className="text-muted-foreground font-medium">Threshold: 5.0 NTU</span>
                                                <Badge
                                                    variant={turbidityValue === null ? "outline" : isTurbidityNormal ? "outline" : "destructive"}
                                                    className="text-[10px] px-1.5 py-0 h-4"
                                                >
                                                    {turbidityValue === null ? 'No Data' : isTurbidityNormal ? 'Normal' : 'High'}
                                                </Badge>
                                            </div>
                                            <Progress
                                                value={turbidityProgress}
                                                className="h-1"
                                            />
                                        </div>

                                        <Separator className="my-2" />

                                        <div className="grid grid-cols-3 gap-2 text-center">
                                            <div>
                                                <div className="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Clean</div>
                                                <div className="text-xs font-semibold tabular-nums">&lt; 1.0</div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Moderate</div>
                                                <div className="text-xs font-semibold tabular-nums">1.0 - 5.0</div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-muted-foreground mb-0.5 uppercase tracking-wide">Dirty</div>
                                                <div className="text-xs font-semibold tabular-nums">&gt; 5.0</div>
                                            </div>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Spectral Breakdown Card */}
                            <Card className="hover:shadow-md transition-shadow">
                                <CardHeader className="flex flex-row items-center justify-between pb-2 bg-muted/20">
                                    <CardTitle className="text-[10px] font-bold uppercase tracking-widest">Spectral Breakdown</CardTitle>
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
                                                {channelEntries.map(([channel, value]) => (
                                                    <div key={channel} className="rounded-md border px-2 py-1 text-center">
                                                        <div className="text-[10px] text-muted-foreground uppercase tracking-wide">{channel}</div>
                                                        <div className="text-xs font-semibold tabular-nums">{value.toFixed(2)}</div>
                                                    </div>
                                                ))}
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
                                <CardContent>
                                    <div className="h-[280px]">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                                                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                                                <XAxis
                                                    dataKey="time"
                                                    className="text-xs"
                                                    tick={{ fill: 'hsl(var(--muted-foreground))' }}
                                                />
                                                <YAxis
                                                    yAxisId="left"
                                                    className="text-xs"
                                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                                                    label={{ value: 'Turbidity (NTU)', angle: -90, position: 'insideLeft', style: { fill: 'hsl(var(--muted-foreground))', fontSize: 11 } }}
                                                />
                                                <YAxis
                                                    yAxisId="right"
                                                    orientation="right"
                                                    className="text-xs"
                                                    tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                                                    label={{ value: 'Spectral Intensity', angle: 90, position: 'insideRight', style: { fill: 'hsl(var(--muted-foreground))', fontSize: 11 } }}
                                                />
                                                <Tooltip
                                                    contentStyle={{
                                                        backgroundColor: 'hsl(var(--card))',
                                                        border: '1px solid hsl(var(--border))',
                                                        borderRadius: '8px',
                                                    }}
                                                />
                                                <Legend />
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
        </div>
    );
}
