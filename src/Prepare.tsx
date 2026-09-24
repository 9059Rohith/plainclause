import { useEffect, useState } from 'react'
import { Check, Download } from 'lucide-react'
import { api } from './api'
import { exportPrep, prepMarkdown } from './export'
import type { Document, Prep } from './types'
import CopyButton from './CopyButton'

export default function Prepare({ doc }: { doc: Document }) {
  const [prep, setPrep] = useState<Prep | null>(null)
  const [error, setError] = useState('')
  const [goals, setGoals] = useState(() => sessionStorage.getItem(`plainclause-goals-${doc.id}`) || '')
  useEffect(() => { api.prepare(doc.id).then(setPrep).catch(err => setError(err instanceof Error ? err.message : 'Could not prepare this sheet.')) }, [doc.id])
  const sheet = prep ? { ...prep, user_goals: goals } : null
  return <div className="feature-page">
    <div className="result-head"><div><h2>Prepare for a conversation.</h2><p className="feature-subtitle">A source-linked checklist and talking points you can bring to a lawyer or the other party.</p></div>{sheet && <div className="export-actions"><CopyButton text={prepMarkdown(sheet)} /><button className="outline-button" onClick={() => exportPrep(sheet)}><Download size={16} /> Markdown</button><button className="outline-button" onClick={() => window.print()}>Print / PDF</button></div>}</div>
    {error && <p className="error-text" role="alert">{error}</p>}
    {!prep && !error && <p role="status">Preparing from the document text…</p>}
    {prep && <div className="prep-sheet"><section><h3>My goals and context</h3><label htmlFor="prep-goals">What do you want to understand or resolve? Add facts you want to bring to a professional.</label><textarea id="prep-goals" className="prep-goals" value={goals} maxLength={3000} onChange={event => { setGoals(event.target.value); sessionStorage.setItem(`plainclause-goals-${doc.id}`, event.target.value) }} placeholder="For example: I want to understand whether the renewal date affects my plans." /></section><section><h3>Key passages to bring</h3><p>Exact excerpts from the document; read each complete section before relying on it.</p>{prep.facts.length ? <ol>{prep.facts.map(item => <li key={item.chunk_id}><strong>{item.source} · page {item.page}</strong><small>{item.excerpt}</small></li>)}</ol> : <p>No common clause category was detected. Inspect the full document.</p>}</section><section><h3>Before you decide</h3><ul className="checklist">{prep.checklist.map(item => <li key={item}><Check size={17} />{item}</li>)}</ul></section>
      <section><h3>Questions worth bringing</h3>{prep.questions.length ? <ol>{prep.questions.map((item, i) => <li key={i}>{item.question}<small>Source: {item.source}</small></li>)}</ol> : <p>No automatic review signals were found. You can still bring any section you find unclear.</p>}</section>
      <section><h3>Dates & periods to verify</h3>{prep.deadlines.length ? <ul className="date-list">{prep.deadlines.map((item, i) => <li key={i}><strong>{item.text}</strong><span>{item.source}</span></li>)}</ul> : <p>No date or notice period was detected automatically. Check the original document.</p>}</section><section><h3>Types of help to consider</h3><p>Availability and rules vary by location.</p><ul>{prep.resources.map(item => <li key={item}>{item}</li>)}</ul></section><p className="disclaimer-line">{prep.disclaimer}</p></div>}
  </div>
}
