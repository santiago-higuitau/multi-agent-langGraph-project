/**
 * Lightweight inline markdown renderer — no external dependencies.
 * Handles: **bold**, *italic*, `code`, bullet lists (- item), numbered lists, line breaks.
 */
export default function Md({ children, className = '' }) {
  const text = typeof children === 'string' ? children : children == null ? '' : String(children)
  if (!text) return null

  const lines = text.split('\n')
  const elements = []
  let listItems = []
  let listType = null

  const flushList = () => {
    if (listItems.length > 0) {
      const Tag = listType === 'ol' ? 'ol' : 'ul'
      const cls = listType === 'ol' ? 'list-decimal' : 'list-disc'
      elements.push(
        <Tag key={`list-${elements.length}`} className={`${cls} pl-4 my-1 space-y-0.5`}>
          {listItems.map((li, j) => <li key={j}>{inlineParse(li)}</li>)}
        </Tag>
      )
      listItems = []
      listType = null
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const ulMatch = line.match(/^[\s]*[-*]\s+(.+)/)
    const olMatch = line.match(/^[\s]*\d+[.)]\s+(.+)/)
    if (ulMatch) { if (listType === 'ol') flushList(); listType = 'ul'; listItems.push(ulMatch[1]) }
    else if (olMatch) { if (listType === 'ul') flushList(); listType = 'ol'; listItems.push(olMatch[1]) }
    else { flushList(); if (line.trim() !== '') elements.push(<p key={`p-${i}`} className="my-0.5">{inlineParse(line)}</p>) }
  }
  flushList()

  return <div className={`text-inherit leading-relaxed ${className}`}>{elements}</div>
}

function inlineParse(text) {
  const parts = []
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g
  let lastIndex = 0
  let match
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index))
    if (match[2]) parts.push(<strong key={match.index} className="font-semibold text-[#111827]">{match[2]}</strong>)
    else if (match[3]) parts.push(<em key={match.index} className="italic">{match[3]}</em>)
    else if (match[4]) parts.push(<code key={match.index} className="text-[#059669] bg-[#ECFDF5] px-1 py-0.5 rounded text-[0.85em]">{match[4]}</code>)
    lastIndex = regex.lastIndex
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex))
  return parts.length > 0 ? parts : text
}
