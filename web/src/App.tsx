import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Login from "./screens/Login";
import Path from "./screens/Path";
import Lesson from "./screens/Lesson";
import Review from "./screens/Review";
import Drill from "./screens/Drill";
import GroupBoard from "./screens/GroupBoard";
import Comprehension from "./screens/Comprehension";
import ComprehensionSet from "./screens/ComprehensionSet";
import Writing from "./screens/Writing";
import WritingTask from "./screens/WritingTask";
import Speaking from "./screens/Speaking";
import Exam from "./screens/Exam";

export default function App() {
  const { authed, logout } = useAuth();

  if (!authed) return <Login />;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">🍁</span> TEF Prep
        </div>
        <nav className="nav">
          <NavLink to="/" end>Learn</NavLink>
          <NavLink to="/review">Review</NavLink>
          <NavLink to="/comprehension">Read &amp; Listen</NavLink>
          <NavLink to="/writing">Write</NavLink>
          <NavLink to="/speaking">Speak</NavLink>
          <NavLink to="/drill">Drill</NavLink>
          <NavLink to="/exam">Mock</NavLink>
          <NavLink to="/board">Group</NavLink>
        </nav>
        <button className="link-btn" onClick={logout}>Log out</button>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<Path />} />
          <Route path="/lesson/:id" element={<Lesson />} />
          <Route path="/review" element={<Review />} />
          <Route path="/comprehension" element={<Comprehension />} />
          <Route path="/comprehension/:id" element={<ComprehensionSet />} />
          <Route path="/writing" element={<Writing />} />
          <Route path="/writing/:id" element={<WritingTask />} />
          <Route path="/speaking" element={<Speaking />} />
          <Route path="/drill" element={<Drill />} />
          <Route path="/exam" element={<Exam />} />
          <Route path="/board" element={<GroupBoard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
