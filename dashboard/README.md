# Water Quality Monitoring Dashboard

A modern, real-time water quality monitoring dashboard built with Next.js 15, shadcn/ui, and MQTT.

## Features

- **Real-time Monitoring**: Live water quality data via MQTT WebSocket connection
- **Visual Status Indicators**: Color-coded status (Green = Good, Red = Bad)
- **Detailed Metrics**: Turbidity and light transmission measurements
- **Historical Charts**: Visual trends for the last 20 readings
- **Information Dense UI**: Compact, professional design using shadcn/ui design tokens
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

1. **MQTT Broker with WebSocket Support**
   - Your MQTT broker needs to support WebSocket connections
   - Default port for WebSocket is usually 9001
   
   For Mosquitto, add this to your `mosquitto.conf`:
   ```
   listener 1883
   protocol mqtt
   
   listener 9001
   protocol websockets
   ```

2. **Node.js** (v18 or higher)

## Setup Instructions

### 1. Install Dependencies

```bash
cd dashboard
npm install
```

### 2. Configure Environment Variables

Update `.env.local` with your MQTT broker details:

```env
NEXT_PUBLIC_MQTT_BROKER=ws://192.168.1.103:9001
NEXT_PUBLIC_MQTT_TOPIC=group1/water_quality
```

**Important**: Use the WebSocket URL (`ws://`) not the regular MQTT URL (`mqtt://`).

### 3. Run the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production

```bash
npm run build
npm start
```

## Dashboard Components

### Overall Status Card
- Shows overall water quality status (Excellent, Good, Fair, Poor, Critical)
- Color-coded border and indicators
- Quality score (0-100)
- Lists detected issues

### Turbidity Card
- Current turbidity reading in NTU
- Visual progress bar
- Threshold indicator (5.0 NTU)
- Reference ranges (Clean, Moderate, Dirty)

### Light Transmission Card
- Current light intensity reading
- Visual progress bar
- Normal range indicator (50-800)
- Reference ranges (Low, Optimal, High)

### Historical Trends Chart
- Dual-axis line chart
- Last 20 readings
- Real-time updates

## Status Colors

- **Green (Excellent/Good)**: Water quality is optimal
- **Yellow (Fair)**: Minor issues detected
- **Orange (Poor)**: Significant issues
- **Red (Critical)**: Severe water quality problems

## Testing

Use the `simulate_sensor_data.py` script from your project to send test data:

```bash
# From your Project directory
python3 simulate_sensor_data.py
```

Then select option 1 (good) or 2 (bad) to see the dashboard update in real-time.

## Technology Stack

- **Framework**: Next.js 15 (App Router)
- **UI Components**: shadcn/ui
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **MQTT Client**: mqtt.js
- **Icons**: Lucide React
- **Type Safety**: TypeScript

## Troubleshooting

### Dashboard shows "Disconnected"

1. Check that your MQTT broker is running
2. Verify WebSocket is enabled on port 9001
3. Check the broker IP in `.env.local`
4. Ensure no firewall is blocking port 9001

### No data appearing

1. Verify your sensors are publishing to the correct topic
2. Check the topic name matches in `.env.local`
3. Use MQTT Explorer to confirm messages are being published

### Browser console errors

1. Open browser DevTools (F12)
2. Check Console tab for errors
3. Verify WebSocket connection in Network tab

## Project Structure

```
dashboard/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx             # Home page
│   │   └── globals.css          # Global styles
│   ├── components/
│   │   ├── ui/                  # shadcn/ui components
│   │   └── WaterQualityDashboard.tsx  # Main dashboard
│   ├── hooks/
│   │   └── useMQTTWaterQuality.ts     # MQTT connection hook
│   ├── lib/
│   │   ├── utils.ts             # Utility functions
│   │   └── water-quality-analyzer.ts  # Analysis logic
│   └── types/
│       └── water-quality.ts     # TypeScript types
├── .env.local                   # Environment configuration
└── package.json
```

## Contributing

This dashboard is part of the Water Quality Monitoring project (Group 1, FYP).

## License

MIT

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
