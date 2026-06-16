import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message as MessageType } from '../hooks/useChat'

interface Props {
  msg: MessageType
  userRole: string
}

const ROLE_LABELS: Record<string, string> = {
  recruiter: 'Recruiter',
  hiring_manager: 'Hiring Mgr',
  admin: 'Admin',
}

export default function Message({ msg, userRole }: Props) {
  const isUser = msg.role === 'user'
  const time = new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[75%]">
          <div className="flex items-center justify-end gap-2 mb-1">
            <span className="text-xs text-slate-500">{time}</span>
            <span className="text-xs text-amazon-orange font-medium">{ROLE_LABELS[userRole] ?? userRole}</span>
          </div>
          <div className="bg-amazon-blue text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed">
            {msg.content}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs text-amazon-orange font-medium">🤖 Analytics AI</span>
          <span className="text-xs text-slate-500">{time}</span>
          {msg.streaming && (
            <span className="flex gap-1">
              <span className="w-1.5 h-1.5 bg-amazon-orange rounded-full animate-pulse-dot" />
              <span className="w-1.5 h-1.5 bg-amazon-orange rounded-full animate-pulse-dot" style={{ animationDelay: '0.2s' }} />
              <span className="w-1.5 h-1.5 bg-amazon-orange rounded-full animate-pulse-dot" style={{ animationDelay: '0.4s' }} />
            </span>
          )}
        </div>
        <div className={`bg-slate-800 border rounded-2xl rounded-tl-sm px-4 py-3 text-sm ${msg.error ? 'border-red-700' : 'border-slate-700'}`}>
          {msg.content ? (
            <div className="prose-recruiting">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>
          ) : (
            <span className="text-slate-500 italic">Thinking...</span>
          )}
        </div>
      </div>
    </div>
  )
}
