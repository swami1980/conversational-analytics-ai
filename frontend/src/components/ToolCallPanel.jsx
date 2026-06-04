import { useState } from 'react'

const TOOL_ICONS = {
  search_knowledge_base: '🔍',
  call_api: '🌐',
  call_apis_parallel: '⚡',
  search_github_issues: '🐛',
  create_github_issue: '📝',
}

const TOOL_COLORS = {
  search_knowledge_base: 'border-purple-600 bg-purple-900/20',
  call_api: 'border-blue-600 bg-blue-900/20',
  call_apis_parallel: 'border-yellow-500 bg-yellow-900/20',
  search_github_issues: 'border-green-600 bg-green-900/20',
  create_github_issue: 'border-orange-500 bg-orange-900/20',
}

function ToolCallCard({ event }) {
  const [expanded, setExpanded] = useState(false)
  const icon = TOOL_ICONS[event.tool_name] || '🔧'
  const colorClass = TOOL_COLORS[event.tool_name] || 'border-slate-600 bg-slate-800'
  const isDone = event.type === 'done'

  return (
    <div className={`border rounded-lg p-3 mb-2 transition-all ${colorClass}`}>
      <button
        className="w-full flex items-center justify-between text-left"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">{icon}</span>
          <span className="text-xs font-mono text-slate-300 font-semibold">{event.tool_name}</span>
          {isDone
            ? <span className="text-green-400 text-xs">✓ done</span>
            : <span className="text-yellow-400 text-xs animate-pulse">running...</span>
          }
        </div>
        <span className="text-slate-500 text-xs">{expanded ? '▲' : '▼'}</span>
      </button>

      {expanded && (
        <div className="mt-2 space-y-2">
          {event.tool_input && Object.keys(event.tool_input).length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-1 uppercase tracking-wide">Input</p>
              <pre className="text-xs text-slate-300 bg-black/40 rounded p-2 overflow-x-auto whitespace-pre-wrap break-words max-h-32">
                {JSON.stringify(event.tool_input, null, 2)}
              </pre>
            </div>
          )}
          {event.result && (
            <div>
              <p className="text-xs text-slate-500 mb-1 uppercase tracking-wide">Result preview</p>
              <pre className="text-xs text-slate-300 bg-black/40 rounded p-2 overflow-x-auto whitespace-pre-wrap break-words max-h-40">
                {event.result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ToolCallPanel({ events, statusMsg, isStreaming }) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex flex-col h-full bg-amazon-nav border-l border-slate-700">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <div>
          <h2 className="text-sm font-semibold text-white">Agent Reasoning</h2>
          <p className="text-xs text-slate-500">Live tool call transparency</p>
        </div>
        <button
          onClick={() => setCollapsed(c => !c)}
          className="text-slate-400 hover:text-white text-xs border border-slate-600 rounded px-2 py-1"
        >
          {collapsed ? 'Show' : 'Hide'}
        </button>
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3">
          {isStreaming && statusMsg && (
            <div className="flex items-center gap-2 text-xs text-slate-400 mb-3 px-1">
              <div className="w-2 h-2 rounded-full bg-amazon-orange animate-pulse" />
              {statusMsg}
            </div>
          )}

          {events.length === 0 && !isStreaming && (
            <p className="text-xs text-slate-600 text-center mt-8 px-4">
              Tool calls from the Strands agent will appear here in real time as it reasons through your question.
            </p>
          )}

          {events.map(evt => (
            <ToolCallCard key={evt.id} event={evt} />
          ))}
        </div>
      )}

      {!collapsed && events.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-700 text-xs text-slate-500">
          {events.length} tool call{events.length !== 1 ? 's' : ''} this turn
        </div>
      )}
    </div>
  )
}
