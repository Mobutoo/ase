import { ReactNode, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Timer,
  ListTodo,
  BarChart3,
  Trophy,
  Settings,
  Sparkles,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { MiniPlayer } from "../Music/MiniPlayer";
import { YouTubeEmbed } from "../Music/YouTubeEmbed";
import { useTimerStore } from "../../hooks/useTimer";

const MAIN_NAV = [
  { path: "/", labelKey: "nav.focus", icon: Timer },
  { path: "/tasks", labelKey: "nav.tasks", icon: ListTodo },
  { path: "/analytics", labelKey: "nav.analytics", icon: BarChart3 },
  { path: "/leaderboard", labelKey: "nav.board", icon: Trophy },
];

const BOTTOM_NAV = [
  { path: "/ai", labelKey: "nav.ai", icon: Sparkles },
  { path: "/settings", labelKey: "nav.settings", icon: Settings },
];

const USER_INITIALS = "A";
const USER_NAME = "Admin";

function NavItem({
  path,
  labelKey,
  icon: Icon,
  isActive,
  collapsed,
}: {
  path: string;
  labelKey: string;
  icon: React.ElementType;
  isActive: boolean;
  collapsed: boolean;
}) {
  const { t } = useTranslation();
  const label = t(labelKey);
  return (
    <Link
      to={path}
      title={collapsed ? label : undefined}
      className={[
        "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg",
        "transition-all duration-200",
        isActive
          ? "text-[#f59e0b]"
          : "text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200",
      ].join(" ")}
      style={
        isActive
          ? {
              background:
                "linear-gradient(to right, rgba(245,158,11,0.10), transparent)",
            }
          : undefined
      }
    >
      {/* Active left bar */}
      {isActive && (
        <div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] rounded-full"
          style={{
            height: "20px",
            backgroundColor: "#f59e0b",
            boxShadow: "0 0 8px rgba(245, 158, 11, 0.5)",
          }}
        />
      )}

      <Icon
        className={[
          "w-[18px] h-[18px] flex-shrink-0 transition-transform duration-200",
          isActive ? "" : "group-hover:scale-110",
        ].join(" ")}
      />

      {!collapsed && (
        <span className="text-sm font-medium animate-fade-in whitespace-nowrap overflow-hidden">
          {label}
        </span>
      )}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  // Focus immersive mode: sidebar hides when timer is active on Focus page
  const timerPhase = useTimerStore((s) => s.phase);
  const isImmersive = location.pathname === "/" && timerPhase !== "idle";

  // Effective sidebar pixel width
  const sidebarWidth = isImmersive ? 0 : collapsed ? 72 : 220;

  return (
    <div className="min-h-screen bg-[#09090b] flex">
      {/* Sidebar */}
      <nav
        className={[
          "bg-[#09090b]",
          "border-r border-zinc-800/50",
          "flex flex-col",
          "transition-all duration-300 ease-out",
          "relative z-10",
          "h-screen sticky top-0",
          "overflow-hidden flex-shrink-0",
          isImmersive ? "opacity-0 pointer-events-none" : "opacity-100",
        ].join(" ")}
        style={{ width: `${sidebarWidth}px` }}
      >
        {/* Logo + collapse toggle (top) */}
        <div className="h-16 flex items-center gap-2 px-3 border-b border-zinc-800/50 flex-shrink-0">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            {/* Gold dot with glow */}
            <div
              className="w-2.5 h-2.5 rounded-full flex-shrink-0"
              style={{
                backgroundColor: "#f59e0b",
                boxShadow:
                  "0 0 8px rgba(245, 158, 11, 0.6), 0 0 16px rgba(245, 158, 11, 0.3)",
              }}
            />

            {!collapsed && (
              <div className="animate-fade-in overflow-hidden">
                <h1 className="text-sm font-mono font-bold text-zinc-50 leading-tight tracking-tight">
                  {t("app.name")}
                </h1>
                <p className="text-xs text-zinc-500 leading-none">
                  {t("app.tagline")}
                </p>
              </div>
            )}
          </div>

          <button
            onClick={() => setCollapsed(!collapsed)}
            title={collapsed ? t("sidebar.expand") : t("sidebar.collapse")}
            className="flex items-center justify-center w-7 h-7 rounded-lg text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 transition-all duration-200 flex-shrink-0"
          >
            {collapsed ? (
              <PanelLeft className="w-3.5 h-3.5" />
            ) : (
              <PanelLeftClose className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* Main nav */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 space-y-1">
          {MAIN_NAV.map((item) => (
            <NavItem
              key={item.path}
              path={item.path}
              labelKey={item.labelKey}
              icon={item.icon}
              isActive={location.pathname === item.path}
              collapsed={collapsed}
            />
          ))}
        </div>

        {/* Bottom section separator */}
        <div className="border-t border-zinc-800/50" />

        {/* Bottom nav items */}
        <div className="p-2 space-y-1">
          {BOTTOM_NAV.map((item) => (
            <NavItem
              key={item.path}
              path={item.path}
              labelKey={item.labelKey}
              icon={item.icon}
              isActive={location.pathname === item.path}
              collapsed={collapsed}
            />
          ))}
        </div>

        {/* User info section separator */}
        <div className="border-t border-zinc-800/50" />

        {/* User info */}
        <div className="px-3 py-3 flex items-center gap-2.5 flex-shrink-0">
          {/* Avatar */}
          <div className="relative flex-shrink-0">
            <div className="h-8 w-8 rounded-full bg-zinc-800 flex items-center justify-center">
              <span className="text-xs font-semibold text-zinc-300">
                {USER_INITIALS}
              </span>
            </div>
            {/* Online dot */}
            <span
              className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-[#09090b]"
            />
          </div>

          {!collapsed && (
            <div className="animate-fade-in overflow-hidden">
              <p className="text-sm font-medium text-zinc-200 leading-tight truncate">
                {USER_NAME}
              </p>
              <p className="text-xs text-zinc-500 leading-none">{t("sidebar.online")}</p>
            </div>
          )}
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto pb-16">{children}</main>

      {/* Global music player — persists across all pages */}
      <YouTubeEmbed />
      <MiniPlayer leftOffset={sidebarWidth} dimmed={isImmersive} />
    </div>
  );
}
