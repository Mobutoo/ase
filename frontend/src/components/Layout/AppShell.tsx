import { ReactNode, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Timer,
  ListTodo,
  BarChart3,
  Trophy,
  Settings,
  ChevronLeft,
  ChevronRight,
  Flame,
} from "lucide-react";

const NAV_ITEMS = [
  { path: "/", label: "Focus", icon: Timer },
  { path: "/tasks", label: "Tasks", icon: ListTodo },
  { path: "/analytics", label: "Analytics", icon: BarChart3 },
  { path: "/leaderboard", label: "Board", icon: Trophy },
  { path: "/settings", label: "Settings", icon: Settings },
];

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-ase-bg flex">
      {/* Sidebar */}
      <nav
        className={`
          ${collapsed ? "w-[72px]" : "w-[220px]"}
          bg-ase-surface/80 backdrop-blur-xl
          border-r border-ase-border/50
          flex flex-col
          transition-all duration-300 ease-out
          relative z-10
        `}
      >
        {/* Logo area */}
        <div className="px-4 py-6 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-ase-gold to-ase-amber flex items-center justify-center flex-shrink-0 shadow-glow">
            <Flame className="w-5 h-5 text-ase-bg" />
          </div>
          {!collapsed && (
            <div className="animate-fade-in overflow-hidden">
              <h1 className="text-lg font-bold text-white tracking-tight">
                Asé
              </h1>
              <p className="text-[10px] text-ase-muted leading-none -mt-0.5">
                Flow Engine
              </p>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="mx-4 h-px bg-gradient-to-r from-ase-gold/20 via-ase-border to-transparent" />

        {/* Nav items */}
        <div className="flex flex-col gap-1 px-3 py-4 flex-1">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  group relative flex items-center gap-3 px-3 py-2.5 rounded-xl
                  transition-all duration-200
                  ${
                    isActive
                      ? "bg-ase-gold/10 text-ase-gold shadow-glow"
                      : "text-ase-muted hover:text-white hover:bg-white/[0.04]"
                  }
                `}
              >
                {/* Active indicator */}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-ase-gold rounded-r-full" />
                )}
                <Icon
                  className={`w-[18px] h-[18px] flex-shrink-0 transition-transform duration-200
                    ${isActive ? "" : "group-hover:scale-110"}`}
                />
                {!collapsed && (
                  <span className="text-sm font-medium animate-fade-in">
                    {item.label}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        {/* Bottom: Collapse toggle */}
        <div className="px-3 pb-4">
          <div className="mx-1 mb-3 h-px bg-gradient-to-r from-transparent via-ase-border to-transparent" />
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="
              w-full flex items-center gap-3 px-3 py-2 rounded-xl
              text-ase-subtle hover:text-ase-muted hover:bg-white/[0.03]
              transition-all duration-200 text-sm
            "
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4 flex-shrink-0" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4 flex-shrink-0" />
                <span className="animate-fade-in">Collapse</span>
              </>
            )}
          </button>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
