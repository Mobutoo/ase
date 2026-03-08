import React, { useState } from "react";

export type NavItem = {
  id: string;
  label: string;
  icon: React.ReactNode;
  href: string;
};

interface Props {
  items: NavItem[];
  activeId: string;
  onNavigate: (id: string) => void;
}

// --- SVG Icon helpers ---
const HomeIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="w-5 h-5">
    <path d="M3 9.75L12 3l9 6.75V21a.75.75 0 01-.75.75H15.75V15h-7.5v6.75H3.75A.75.75 0 013 21V9.75z" strokeLinejoin="round" />
  </svg>
);

const TasksIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="w-5 h-5">
    <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
    <rect x="3" y="3" width="18" height="18" rx="3" />
  </svg>
);

const AnalyticsIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="w-5 h-5">
    <path d="M3 20l4.5-8 4 5 3.5-7L20 20" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const LeaderboardIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="w-5 h-5">
    <rect x="9" y="9" width="6" height="12" rx="1" />
    <rect x="3" y="13" width="6" height="8" rx="1" />
    <rect x="15" y="5" width="6" height="16" rx="1" />
  </svg>
);

const SettingsIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="w-5 h-5">
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" strokeLinecap="round" />
  </svg>
);

const MenuIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="w-5 h-5">
    <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
  </svg>
);

export const DEFAULT_NAV_ITEMS: NavItem[] = [
  { id: "home", label: "Home", icon: <HomeIcon />, href: "/" },
  { id: "tasks", label: "Tasks", icon: <TasksIcon />, href: "/tasks" },
  { id: "analytics", label: "Analytics", icon: <AnalyticsIcon />, href: "/analytics" },
  { id: "leaderboard", label: "Leaderboard", icon: <LeaderboardIcon />, href: "/leaderboard" },
  { id: "settings", label: "Settings", icon: <SettingsIcon />, href: "/settings" },
];

export const Sidebar: React.FC<Props> = ({ items, activeId, onNavigate }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      {/* Overlay on mobile when expanded */}
      {expanded && (
        <div
          className="fixed inset-0 bg-black/50 z-20 lg:hidden"
          onClick={() => setExpanded(false)}
        />
      )}

      <nav
        className={`
          fixed left-0 top-0 h-full z-30 flex flex-col
          bg-[#1a1a2e] border-r border-[#2a2a3e]
          transition-all duration-300
          ${expanded ? "w-64" : "w-16"}
        `}
      >
        {/* Logo + toggle */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-[#2a2a3e]">
          <div className="w-8 h-8 rounded-lg bg-[#f59e0b] flex items-center justify-center flex-shrink-0">
            <span className="text-[#0f0f0f] font-black text-sm">A</span>
          </div>
          {expanded && (
            <span className="text-gray-100 font-bold text-base truncate">Asé</span>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className={`
              ml-auto text-gray-500 hover:text-gray-200 transition-colors p-1 rounded-md hover:bg-[#2a2a3e]
              ${!expanded ? "mx-auto" : ""}
            `}
            aria-label={expanded ? "Collapse sidebar" : "Expand sidebar"}
          >
            <MenuIcon />
          </button>
        </div>

        {/* Nav items */}
        <div className="flex flex-col gap-1 p-2 flex-1 overflow-y-auto">
          {items.map((item) => {
            const isActive = item.id === activeId;
            return (
              <button
                key={item.id}
                onClick={() => { onNavigate(item.id); if (window.innerWidth < 1024) setExpanded(false); }}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 w-full text-left
                  ${isActive
                    ? "bg-[#f59e0b]/15 text-[#f59e0b] border border-[#f59e0b]/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#2a2a3e] border border-transparent"
                  }
                `}
                title={!expanded ? item.label : undefined}
              >
                <span className="flex-shrink-0">{item.icon}</span>
                {expanded && (
                  <span className="text-sm font-medium truncate">{item.label}</span>
                )}
                {isActive && !expanded && (
                  <span className="absolute left-0 w-0.5 h-6 bg-[#f59e0b] rounded-r" />
                )}
              </button>
            );
          })}
        </div>

        {/* Bottom: collapse hint */}
        {expanded && (
          <div className="p-3 border-t border-[#2a2a3e]">
            <p className="text-[10px] text-gray-600 text-center">Asé · Focus Stack</p>
          </div>
        )}
      </nav>
    </>
  );
};
