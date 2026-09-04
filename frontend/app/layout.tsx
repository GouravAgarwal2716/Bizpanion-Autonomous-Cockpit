import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Bizpanion — Autonomous Business Cockpit',
  description: 'AI-powered business intelligence for rural and semi-urban micro-entrepreneurs. Real-time alerts, voice briefings, and autonomous data analysis.',
  keywords: ['business intelligence', 'rural entrepreneur', 'AI', 'market prices', 'WhatsApp alerts'],
  openGraph: {
    title: 'Bizpanion — Autonomous Business Cockpit',
    description: 'Zero-prompt, voice-first business cockpit for rural entrepreneurs',
    type: 'website',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
