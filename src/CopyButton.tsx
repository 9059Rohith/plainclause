import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return <button className="icon-button" title={copied ? 'Copied' : 'Copy text'} aria-label={copied ? 'Copied' : 'Copy text'} onClick={async () => { try { await navigator.clipboard.writeText(text); setCopied(true); window.setTimeout(() => setCopied(false), 2000) } catch { setCopied(false) } }}>{copied ? <Check size={16} /> : <Copy size={16} />}</button>
}
