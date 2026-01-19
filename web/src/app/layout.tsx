import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "PolyDelta | Crypto Prediction Arbitrage",
  description: "Track real-time odds discrepancies between Polymarket and Web2 bookmakers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${geistMono.variable} font-mono antialiased bg-[#0d1117] text-[#e6edf3] min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
