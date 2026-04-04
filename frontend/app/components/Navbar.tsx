"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const HomeIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
    <polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
);

const ChatIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);

const ChartIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
    <line x1="2" y1="20" x2="22" y2="20"/>
  </svg>
);

const SignalIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 20h.01M7 20v-4M12 20v-8M17 20V8M22 4v16"/>
  </svg>
);

const links = [
  { href: "/",        label: "Home",               Icon: HomeIcon  },
  { href: "/live",    label: "Live Scores",         Icon: SignalIcon, live: true },
  { href: "/chat",    label: "Football Assistant",  Icon: ChatIcon  },
  { href: "/matches", label: "Match Analysis",      Icon: ChartIcon },
];

export default function Navbar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/30 backdrop-blur-md border-b border-white/10 text-white">
      <div className="px-4 sm:px-6 py-3 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-1 font-bold text-lg tracking-tight">
          <div className="w-9 h-9 overflow-hidden flex-shrink-0">
            <img src="/logo.png" alt="KickSync" className="w-full h-full object-cover scale-150" />
          </div>
          <span>KickSync</span>
        </div>

        {/* Desktop links */}
        <div className="hidden sm:flex gap-1">
          {links.map(({ href, label, Icon, live }) => {
            const active = pathname === href;
            return (
              <Link key={href} href={href}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active ? "bg-white/15 text-white font-semibold" : "text-gray-300 hover:text-white hover:bg-white/10"
                }`}>
                <Icon />{label}
                {live && <span className="relative flex h-1.5 w-1.5 ml-0.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500" />
                </span>}
              </Link>
            );
          })}
        </div>

        {/* Mobile hamburger */}
        <button className="sm:hidden p-2 rounded-lg hover:bg-white/10 transition" onClick={() => setOpen(o => !o)} aria-label="Menu">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            {open
              ? <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              : <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />}
          </svg>
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="sm:hidden border-t border-white/10 bg-black/60 backdrop-blur-md px-4 py-3 flex flex-col gap-1">
          {links.map(({ href, label, Icon, live }) => {
            const active = pathname === href;
            return (
              <Link key={href} href={href} onClick={() => setOpen(false)}
                className={`flex items-center gap-3 px-3 py-3 rounded-lg text-sm transition-colors ${
                  active ? "bg-white/15 text-white font-semibold" : "text-gray-300 hover:text-white hover:bg-white/10"
                }`}>
                <Icon />{label}
                {live && <span className="relative flex h-1.5 w-1.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-green-500" />
                </span>}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
}
