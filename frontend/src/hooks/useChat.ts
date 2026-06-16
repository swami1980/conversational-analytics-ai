import { useState, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { streamChat } from '../api/client'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  streaming?: boolean
  error?: boolean
}

export interface ToolEvent {
  id: string
  type: 'call' | 'done'
  tool_name: string
  result?: string
  timestamp: number
  [key: string]: unknown
}

export function useChat(token: string) {
  const [sessionId, setSessionId] = useState<string>(() => uuidv4())
  const [messages, setMessages] = useState<Message[]>([])
  const [toolEvents, setToolEvents] = useState<ToolEvent[]>([])
  const [followUps, setFollowUps] = useState<string[]>([])
  const [isStreaming, setIsStreaming] = useState<boolean>(false)
  const [statusMsg, setStatusMsg] = useState<string>('')
  const cancelRef = useRef<(() => void) | null>(null)

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || isStreaming) return

    const userMsg: Message = { id: uuidv4(), role: 'user', content: text, timestamp: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setToolEvents([])
    setFollowUps([])
    setIsStreaming(true)
    setStatusMsg('Connecting...')

    const assistantId = uuidv4()
    setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: '', timestamp: Date.now(), streaming: true }])

    const cancel = streamChat(token, sessionId, text, (eventType, payload) => {
      switch (eventType) {
        case 'session':
          setSessionId((payload as { session_id: string }).session_id)
          break
        case 'status':
          setStatusMsg((payload as { message: string }).message)
          break
        case 'tool_call':
          setToolEvents(prev => [...prev, { type: 'call', ...(payload as object), id: uuidv4(), timestamp: Date.now() } as ToolEvent])
          break
        case 'tool_result':
          setToolEvents(prev => prev.map(e =>
            e.tool_name === (payload as { tool_name: string }).tool_name && e.type === 'call' && !e.result
              ? { ...e, result: (payload as { result_preview: string }).result_preview, type: 'done' as const }
              : e
          ))
          break
        case 'final_answer':
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, content: (payload as { content: string }).content, streaming: false } : m
          ))
          setStatusMsg('')
          break
        case 'follow_up_questions':
          setFollowUps((payload as { questions: string[] }).questions || [])
          break
        case 'done':
          setIsStreaming(false)
          setStatusMsg('')
          break
        case 'error':
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: `Error: ${(payload as { message: string }).message}`, streaming: false, error: true }
              : m
          ))
          setIsStreaming(false)
          setStatusMsg('')
          break
      }
    })
    cancelRef.current = cancel
  }, [token, sessionId, isStreaming])

  const newSession = useCallback(() => {
    if (cancelRef.current) cancelRef.current()
    setSessionId(uuidv4())
    setMessages([])
    setToolEvents([])
    setFollowUps([])
    setIsStreaming(false)
    setStatusMsg('')
  }, [])

  return { sessionId, messages, toolEvents, followUps, isStreaming, statusMsg, sendMessage, newSession }
}
