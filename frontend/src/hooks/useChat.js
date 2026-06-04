import { useState, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { streamChat } from '../api/client'

export function useChat(token) {
  const [sessionId, setSessionId] = useState(() => uuidv4())
  const [messages, setMessages] = useState([])
  const [toolEvents, setToolEvents] = useState([])
  const [followUps, setFollowUps] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const cancelRef = useRef(null)

  const sendMessage = useCallback((text) => {
    if (!text.trim() || isStreaming) return

    const userMsg = { id: uuidv4(), role: 'user', content: text, timestamp: Date.now() }
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
          setSessionId(payload.session_id)
          break
        case 'status':
          setStatusMsg(payload.message)
          break
        case 'tool_call':
          setToolEvents(prev => [...prev, { type: 'call', ...payload, id: uuidv4(), timestamp: Date.now() }])
          break
        case 'tool_result':
          setToolEvents(prev => prev.map(e =>
            e.tool_name === payload.tool_name && e.type === 'call' && !e.result
              ? { ...e, result: payload.result_preview, type: 'done' }
              : e
          ))
          break
        case 'final_answer':
          setMessages(prev => prev.map(m =>
            m.id === assistantId ? { ...m, content: payload.content, streaming: false } : m
          ))
          setStatusMsg('')
          break
        case 'follow_up_questions':
          setFollowUps(payload.questions || [])
          break
        case 'done':
          setIsStreaming(false)
          setStatusMsg('')
          break
        case 'error':
          setMessages(prev => prev.map(m =>
            m.id === assistantId
              ? { ...m, content: `Error: ${payload.message}`, streaming: false, error: true }
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
