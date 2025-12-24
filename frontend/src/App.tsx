import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import ChatPage from './pages/ChatPage';
import FilesPage from './pages/FilesPage';
import ImagesPage from './pages/ImagesPage';
import SummaryPage from './pages/SummaryPage';
import SettingsPage from './pages/SettingsPage';
import { ToastProvider } from './components/ToastProvider';

const navItems = [
  { path: '/chat', label: '聊天', emoji: '💬' },
  { path: '/files', label: '文件', emoji: '📄' },
  { path: '/images', label: '图片', emoji: '🖼️' },
  { path: '/summary', label: '摘要', emoji: '🧠' },
  { path: '/settings', label: '设置', emoji: '⚙️' },
];

function App() {
  return (
    <ToastProvider>
      <div className="app-shell">
        <nav className="nav">
          <div className="brand">
            <span style={{ fontSize: 22 }}>🐧</span>
            <div>
              <h1>Agent-Penguin</h1>
              <div className="brand-pill">QQ 风格控制台</div>
            </div>
          </div>
          <div className="nav-links">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                <span>{item.emoji}</span>
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
        <main className="main">
          <Routes>
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/files" element={<FilesPage />} />
            <Route path="/images" element={<ImagesPage />} />
            <Route path="/summary" element={<SummaryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/chat" replace />} />
          </Routes>
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;
