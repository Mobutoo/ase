import { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Focus", icon: "~" },
  { path: "/tasks", label: "Tasks", icon: "#" },
  { path: "/analytics", label: "Analytics", icon: "%" },
  { path: "/leaderboard", label: "Board", icon: "*" },
  { path: "/settings", label: "Settings", icon: "@" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-ase-bg flex">
      {/* Sidebar */}
      <nav className="w-16 lg:w-56 bg-ase-surface border-r border-ase-border flex flex-col py-6">
        <div className="px-4 mb-8">
          <h1 className="text-ase-gold font-bold text-xl hidden lg:block">
            Ase
          </h1>
          <span className="text-ase-gold font-bold text-xl lg:hidden block text-center">
            A
          </span>
        </div>

        <div className="flex flex-col gap-1 px-2">
          {NAV_ITEMS.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive
                    ? "bg-ase-gold/10 text-ase-gold"
                    : "text-ase-muted hover:text-ase-text hover:bg-ase-border/50"
                }`}
              >
                <span className="font-mono text-sm w-5 text-center">
                  {item.icon}
                </span>
                <span className="hidden lg:block text-sm font-medium">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 p-6 lg:p-10 overflow-auto">{children}</main>
    </div>
  );
}
