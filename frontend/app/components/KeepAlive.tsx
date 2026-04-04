"use client";
import { useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function KeepAlive() {
  useEffect(() => {
    // Ping backend every 14 minutes to prevent Render free tier sleep
    const ping = () => fetch(`${API}/`).catch(() => {});
    ping();
    const interval = setInterval(ping, 14 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);
  return null;
}
