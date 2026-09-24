import { useEffect, useState } from 'react'
import { Columns3, Download, FileText, Printer } from 'lucide-react'
import { api } from './api'
import { comparisonMarkdown, exportComparison } from './export'
import type { Comparison, DocSummary } from './types'
import CopyButton from './CopyButton'

export default function Compare({ docs, selectedId }: { docs: DocSummary[]; selectedId: string }) {
  const [ids, setIds] = useState<string[]>([selectedId])
  const [result, setResult] = useState<Comparison | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setIds([selectedId]); setResult(null) }, [selectedId])
  function toggle(id: string) { setIds(current => current.includes(id) ? current.filter(x => x !== id) : current.length < 5 ? [...current, id] : current) }
  async function compare() {
    setBusy(true); setError('')
    try { setResult(await api.compare(ids)) }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not compare the selected documents.') }
    finally { setBusy(false) }
  }
  return <div className="feature-page">
    <h2>Compare the terms.</h2><p className="feature-subtitle">Choose two to five documents. Clauses are matched by heading, then their wording is compared. Read each original passage to judge the significance.</p>
    <div className="compare-picker" role="group" aria-label="Documents to compare">{docs.map(d => <label key={d.id}><input type="checkbox" checked={ids.includes(d.id)} onChange={() => toggle(d.id)} /><span><FileText size={18} />{d.name}</span></label>)}</div>
    <button className="primary-button" disabled={busy || ids.length < 2} onClick={compare}>{busy ? 'Comparing…' : 'Compare selected'} <Columns3 size={17} /></button>
    {docs.length < 2 && <p className="gentle-note">Upload another version or agreement to compare its clauses.</p>}
    {error && <p className="error-text" role="alert">{error}</p>}
    {result && <div className="comparison-results"><div className="result-head"><h3>Differences from {result.base}</h3><div className="export-actions"><CopyButton text={comparisonMarkdown(result)} /><button className="outline-button" onClick={() => exportComparison(result)}><Download size={15} /> Export</button><button className="icon-button" title="Print or save as PDF" aria-label="Print or save as PDF" onClick={() => window.print()}><Printer size={16} /></button></div></div>
      {result.comparisons.map(c => <section key={c.name}><h4>Compared with {c.name}</h4>{c.rows.length ? c.rows.map((row, i) => <article className="diff-row" key={`${row.heading}-${i}`}><div className="diff-title"><strong>{row.heading}</strong><span className={`status-tag ${row.status}`}>{row.status}</span></div>{row.changed_terms.length > 0 && <div className="term-changes" aria-label="Changed amounts and periods">{row.changed_terms.map(term => <p key={term.label}><strong>{term.label}:</strong> {term.before} → {term.after}</p>)}</div>}<div className="diff-columns"><div><small>{result.base}</small><p>{row.before || 'Not present'}</p></div><div><small>{c.name}</small><p>{row.after || 'Not present'}</p></div></div></article>) : <p>No text differences detected in matched sections.</p>}</section>)}
      <p className="disclaimer-line">{result.disclaimer}</p></div>}
  </div>
}
