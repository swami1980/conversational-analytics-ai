import { useState } from 'react'
import { login } from '../api/client'

const DEMO_USERS = [
  { username: 'recruiter1', password: 'password123', label: 'Recruiter', desc: 'Full pipeline view' },
  { username: 'hm_alice', password: 'password123', label: 'Hiring Manager', desc: 'Own reqs only' },
  { username: 'admin', password: 'admin123', label: 'Admin', desc: 'Full access' },
]

export default function LoginModal({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(username, password)
      onLogin(data)
    } catch {
      setError('Invalid credentials. Try the demo accounts below.')
    } finally {
      setLoading(false)
    }
  }

  async function quickLogin(user) {
    setLoading(true)
    setError('')
    try {
      const data = await login(user.username, user.password)
      onLogin(data)
    } catch {
      setError('Backend not reachable. Start the server first.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-amazon-nav border border-slate-700 rounded-xl w-full max-w-md p-8 shadow-2xl">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🤖</div>
          <h1 className="text-2xl font-bold text-white">Recruiting Analytics AI</h1>
          <p className="text-slate-400 text-sm mt-1">Multi-agent prototype · Strands SDK</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 mb-6">
          <input
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-amazon-orange"
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            autoComplete="username"
          />
          <input
            type="password"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-amazon-orange"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-amazon-orange hover:bg-amazon-orange-hover text-black font-bold py-3 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div>
          <p className="text-slate-500 text-xs text-center mb-3">— Quick demo access —</p>
          <div className="space-y-2">
            {DEMO_USERS.map(u => (
              <button
                key={u.username}
                onClick={() => quickLogin(u)}
                disabled={loading}
                className="w-full flex items-center justify-between bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg px-4 py-3 transition-colors disabled:opacity-50"
              >
                <div className="text-left">
                  <span className="text-white font-medium text-sm">{u.label}</span>
                  <span className="text-slate-500 text-xs ml-2">({u.username})</span>
                </div>
                <span className="text-slate-500 text-xs">{u.desc}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
