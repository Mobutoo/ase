import { Routes, Route } from "react-router-dom";
import { AppShell } from "./components/Layout/AppShell";
import { Home } from "./pages/Home";
import { Tasks } from "./pages/Tasks";
import { Analytics } from "./pages/Analytics";
import { Leaderboard } from "./pages/Leaderboard";
import { Settings } from "./pages/Settings";
import { AICopilotPanel } from "./components/AI/AICopilotPanel";

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tasks" element={<Tasks />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/ai" element={<AICopilotPanel />} />
      </Routes>
    </AppShell>
  );
}

export default App;
