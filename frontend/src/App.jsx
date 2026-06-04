import { useState } from 'react'
import LoginModal from './components/LoginModal'
import ChatWindow from './components/ChatWindow'
import ToolCallPanel from './components/ToolCallPanel'
import { useChat } from './hooks/useChat'

const ROLE_BADGE = {
  recruiter: { label: 'Recruiter', color: 'bg-blue-700' },
  hiring_manager: { label: 'Hiring Mgr', color: 'bg-purple-700' },
  admin: { label: 'Admin', color: 'bg-red-700' },
}

export default function App() {
  const [auth, setAuth] = useState(null)

  function handleLogin(data) {
    setAuth({ token: data.access_token, user: data.user })
  }

  function handleLogout() {
    setAuth(null)
  }

  if (!auth) return <LoginModal onLogin={handleLogin} />

  return <Dashboard auth={auth} onLogout={handleLogout} />
}

function Dashboard({ auth, onLogout }) {
  const { token, user } = auth
  const { messages, toolEvents, followUps, isStreaming, statusMsg, sendMessage, newSession } = useChat(token)
  const badge = ROLE_BADGE[user.role] || { label: user.role, color: 'bg-slate-600' }

  return (
    <div className="flex flex-col h-screen bg-amazon-dark">
      {/* Top nav */}
      <header className="bg-amazon-nav border-b border-slate-700 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🤖</span>
          <div>
            <h1 className="text-white font-bold text-base leading-tight">Recruiting Analytics AI</h1>
            <p className="text-slate-500 text-xs">Amazon internal · Strands SDK prototype</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={newSession}
            className="text-xs border border-slate-600 hover:border-amazon-orange text-slate-400 hover:text-white rounded-lg px-3 py-1.5 transition-colors"
          >
            + New Session
          </button>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-medium px-2 py-1 rounded-full ${badge.color} text-white`}>
              {badge.label}
            </span>
            <span className="text-slate-300 text-sm">{user.full_name}</span>
          </div>
          <button
            onClick={onLogout}
            className="text-xs text-slate-500 hover:text-white transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main content — chat left (65%) + tool panel right (35%) */}
      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 flex flex-col min-w-0" style={{ flex: '0 0 65%' }}>
          <ChatWindow
            messages={messages}
            followUps={followUps}
            isStreaming={isStreaming}
            statusMsg={statusMsg}
            onSend={sendMessage}
            userRole={user.role}
          />
        </div>
        <div className="flex flex-col min-w-0 overflow-hidden" style={{ flex: '0 0 35%' }}>
          <ToolCallPanel events={toolEvents} statusMsg={statusMsg} isStreaming={isStreaming} />
        </div>
      </div>
    </div>
  )
}
