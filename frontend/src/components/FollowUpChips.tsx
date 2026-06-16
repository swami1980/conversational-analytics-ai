interface Props {
  questions: string[]
  onSelect: (question: string) => void
  disabled: boolean
}

export default function FollowUpChips({ questions, onSelect, disabled }: Props) {
  if (questions.length === 0) return null
  return (
    <div className="px-4 py-3 border-t border-slate-800">
      <p className="text-xs text-slate-500 mb-2">Suggested follow-ups</p>
      <div className="flex flex-wrap gap-2">
        {questions.map((q, i) => (
          <button
            key={i}
            onClick={() => onSelect(q)}
            disabled={disabled}
            className="text-xs bg-slate-800 hover:bg-slate-700 border border-slate-600 hover:border-amazon-orange text-slate-300 hover:text-white rounded-full px-3 py-1.5 transition-colors disabled:opacity-40 text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
