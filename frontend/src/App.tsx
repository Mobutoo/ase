import { Routes, Route } from "react-router-dom";
import { lazy, Suspense } from "react";
import { AppShell } from "./components/Layout/AppShell";
import { Home } from "./pages/Home";
const Tasks = lazy(() => import("./pages/Tasks").then((m) => ({ default: m.Tasks })));
const Analytics = lazy(() => import("./pages/Analytics").then((m) => ({ default: m.Analytics })));
const Leaderboard = lazy(() => import("./pages/Leaderboard").then((m) => ({ default: m.Leaderboard })));
const Settings = lazy(() => import("./pages/Settings").then((m) => ({ default: m.Settings })));
const AICopilotPanel = lazy(() => import("./components/AI/AICopilotPanel").then((m) => ({ default: m.AICopilotPanel })));
const CalendarPage = lazy(() => import("./pages/CalendarPage").then((m) => ({ default: m.CalendarPage })));
const CirclePage = lazy(() => import("./pages/CirclePage").then((m) => ({ default: m.CirclePage })));
const InvitePage = lazy(() => import("./pages/InvitePage").then((m) => ({ default: m.InvitePage })));

function App() {
  return (
    <AppShell>
      <Suspense fallback={<p role="status" className="p-6 text-ase-muted">Loading…</p>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/calendar" element={<CalendarPage />} />
        <Route path="/circle" element={<CirclePage />} />
        <Route path="/invite" element={<InvitePage />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/ai" element={<AICopilotPanel />} />
      </Routes>
      </Suspense>
    </AppShell>
  );
}

export default App;
