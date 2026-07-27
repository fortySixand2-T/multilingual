import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { LevelProvider, LevelSwitcher } from "./level";
import Login from "./screens/Login";
import Path from "./screens/Path";
import Lesson from "./screens/Lesson";
import Review from "./screens/Review";
import Decks from "./screens/Decks";
import Deck from "./screens/Deck";
import Drill from "./screens/Drill";
import GroupBoard from "./screens/GroupBoard";
import Comprehension from "./screens/Comprehension";
import ComprehensionSet from "./screens/ComprehensionSet";
import Writing from "./screens/Writing";
import WritingTask from "./screens/WritingTask";
import Speaking from "./screens/Speaking";
import Exam from "./screens/Exam";
import Grammar from "./screens/Grammar";
import Readiness from "./screens/Readiness";
import WeakSpots from "./screens/WeakSpots";

export default function App() {
  const { authed, logout } = useAuth();

  if (!authed) return <Login />;

  return (
    <LevelProvider>
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">🍁</span> TEF Prep
        </div>
        <nav className="nav">
          <NavLink to="/" end>Learn</NavLink>
          <NavLink to="/review">Review</NavLink>
          <NavLink to="/exam">Mock</NavLink>
          <NavLink to="/board">Group</NavLink>
        </nav>
        <div className="topbar-right">
          <LevelSwitcher />
          <button className="link-btn" onClick={logout}>Log out</button>
        </div>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<Path />} />
          <Route path="/lesson/:id" element={<Lesson />} />
          <Route path="/review" element={<Review />} />
          <Route path="/weak-spots" element={<WeakSpots />} />
          <Route path="/grammar" element={<Grammar />} />
          <Route path="/vocab" element={<Decks />} />
          <Route path="/vocab/:level/:tag" element={<Deck />} />
          <Route path="/comprehension" element={<Comprehension />} />
          <Route path="/comprehension/:id" element={<ComprehensionSet />} />
          <Route path="/writing" element={<Writing />} />
          <Route path="/writing/:id" element={<WritingTask />} />
          <Route path="/speaking" element={<Speaking />} />
          <Route path="/drill" element={<Drill />} />
          <Route path="/exam" element={<Exam />} />
          <Route path="/readiness" element={<Readiness />} />
          <Route path="/board" element={<GroupBoard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
    </LevelProvider>
  );
}
