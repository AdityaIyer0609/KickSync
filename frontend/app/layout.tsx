import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "./components/Navbar";
import KeepAlive from "./components/KeepAlive";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "KickSync",
  description: "AI-powered football intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <head>
        <link rel="icon" type="image/png" href="/logo1.png?v=4" />
        <link rel="shortcut icon" href="/logo1.png?v=4" />
        <link rel="apple-touch-icon" href="/logo1.png?v=4" />
      </head>
      <body className="min-h-screen bg-gray-950 text-white flex flex-col">
        <Navbar />
        <KeepAlive />
        <main className="flex-1 pt-16">{children}</main>
      </body>
    </html>
  );
}
