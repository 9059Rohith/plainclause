import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowRight, BookOpen, ChevronDown, ClipboardList, Download, FileText, HelpCircle, LockKeyhole, MessageCircle, Plus, Printer, Search, ShieldCheck, Trash2, UploadCloud, X } from 'lucide-react'
import { api, askStream, upload } from './api'
import { exportAnswer, exportOverview } from './export'
import type { Answer, Chunk, DocSummary, Document, HistoryItem, IndexProgress, SummaryAnswer } from './types'
import CopyButton from './CopyButton'

type Tab = 'overview' | 'ask' | 'compare' | 'prepare'
const DISCLAIMER = 'Legal information, not legal advice.'
const Compare = lazy(() => import('./Compare'))
const Prepare = lazy(() => import('./Prepare'))

function EmptyWorkspace({ onBrowse, hosted }: { onBrowse: () => void; hosted: boolean }) {
  return <div className="empty-workspace">
    <div className="empty-icon"><FileText size={38} strokeWidth={1.5} /></div>
    <h1>Understand the fine print.</h1>
    <p>Upload an agreement, lease, policy, or other legal document. Plainclause helps you find the terms that matter and trace every answer back to the original.</p>
    <button className="primary-button" onClick={onBrowse}><Plus size={18} /> Add your first document</button>
    <div className="empty-points"><span><ShieldCheck size={17} /> {hosted ? 'Stored on this service' : 'Stored in your local workspace'}</span><span><BookOpen size={17} /> Sources stay visible</span></div>
  </div>
}

function SourceList({ answer }: { answer: Answer }) {
  return <div className="source-list" aria-label="Source passages">
    {answer.citations.map(c => <blockquote key={c.id} id={`source-${c.id}`}>
      <div className="source-head"><span>{c.heading}</span><small>Page {c.page}</small></div>
      <p>{c.quote}</p>
    </blockquote>)}
  </div>
}

function AnswerView({ answer, title, onExport }: { answer: Answer; title?: string; onExport?: () => void }) {
  return <div className={`answer-box ${answer.status}`} aria-live="polite">
    <div className="answer-top"><strong>{title || (answer.status === 'source_only' ? 'Source found' : answer.status === 'not_found' ? 'Not found in this document' : 'Plainclause interpretation')}</strong><div className="answer-actions"><CopyButton text={`${answer.answer}\n\n${answer.citations.map(c => `${c.heading} (page ${c.page}): ${c.quote}`).join('\n')}\n\n${answer.disclaimer}`} />{onExport && <button className="icon-button" title="Export as Markdown" aria-label="Export as Markdown" onClick={onExport}><Download size={17} /></button>}<button className="icon-button" title="Print or save as PDF" aria-label="Print or save as PDF" onClick={() => window.print()}><Printer size={16} /></button></div></div>
    <p>{answer.answer}</p>
    {answer.professional_note && <p className="professional-note">{answer.professional_note}</p>}
    {answer.jurisdiction_note && <small>{answer.jurisdiction_note}</small>}
    <SourceList answer={answer} />
    <div className="answer-disclaimer">{answer.disclaimer}</div>
  </div>
}

function SectionRow({ chunk, doc, level }: { chunk: Chunk; doc: Document; level: 'simple' | 'detailed' }) {
  const [open, setOpen] = useState(false)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setAnswer(null) }, [level])
  async function simplify() {
    setWorking(true); setError('')
    try { setAnswer(await api.simplify(doc.id, chunk.id, level)) }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not simplify this section.') }
    finally { setWorking(false) }
  }
  return <article className="section-row" id={`section-${chunk.id}`}>
    <button className="section-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
      <span className="section-number">{String(chunk.ordinal + 1).padStart(2, '0')}</span>
      <span className="section-title">{chunk.heading}</span>
      <span className="section-meta">{chunk.categories.slice(0, 2).join(' · ') || 'Section'}</span>
      <ChevronDown className={open ? 'rotate' : ''} size={18} />
    </button>
    {open && <div className="section-detail">
      <div className="original-label">Original text · page {chunk.page}</div>
      <p className="original-text">{chunk.text}</p>
      {chunk.review_reasons.length > 0 && <div className="review-inline"><strong>Worth reviewing</strong>{chunk.review_reasons.map(reason => <p key={reason}>{reason}</p>)}</div>}
      {chunk.deadlines.length > 0 && <p className="deadline-inline"><strong>Dates & periods:</strong> {chunk.deadlines.join(', ')}</p>}
      <button className="outline-button" disabled={working} onClick={simplify}>{working ? 'Reading this section…' : answer ? 'Refresh explanation' : 'Explain this section'} <ArrowRight size={15} /></button>
      {error && <p className="error-text" role="alert">{error}</p>}
      {answer && <AnswerView answer={answer} title={`${level === 'simple' ? 'Simple' : 'Detailed'} explanation`} onExport={() => exportAnswer(doc, `Explain ${chunk.heading}`, answer)} />}
    </div>}
  </article>
}

function Overview({ doc, onAsk }: { doc: Document; onAsk: () => void }) {
  const [level, setLevel] = useState<'simple' | 'detailed'>(() => sessionStorage.getItem(`plainclause-level-${doc.id}`) === 'detailed' ? 'detailed' : 'simple')
  const [summaryParts, setSummaryParts] = useState<SummaryAnswer[]>([])
  const [summaryProgress, setSummaryProgress] = useState(0)
  const [summaryBusy, setSummaryBusy] = useState(false)
  const [stopPending, setStopPending] = useState(false)
  const [summaryError, setSummaryError] = useState('')
  const [summaryLoaded, setSummaryLoaded] = useState(false)
  const cancelSummary = useRef(false)
  useEffect(() => () => { cancelSummary.current = true }, [])
  useEffect(() => { let active = true; api.summaries(doc.id, level).then(parts => { if (active) { setSummaryParts(parts); setSummaryProgress(parts.reduce((total, part) => total + part.coverage_count, 0)); setSummaryLoaded(true) } }).catch(err => { if (active) { setSummaryError(err instanceof Error ? err.message : 'Could not load saved overview.'); setSummaryLoaded(true) } }); return () => { active = false } }, [doc.id, level])
  async function getSummary() {
    cancelSummary.current = false
    setStopPending(false)
    setSummaryBusy(true); setSummaryError('')
    try {
      const resume = summaryParts.length > 0 && summaryProgress < doc.chunks.length && summaryParts.every(part => part.status === 'answered')
      if (!resume) { await api.clearSummaries(doc.id); setSummaryParts([]); setSummaryProgress(0) }
      let offset = resume ? summaryProgress : 0
      while (offset < doc.chunks.length && !cancelSummary.current) {
        const part = await api.summary(doc.id, offset, level)
        setSummaryParts(current => [...current, part])
        offset += part.coverage_count
        setSummaryProgress(offset)
        if (part.status !== 'answered' || part.coverage_count === 0) break
      }
    }
    catch (err) { setSummaryError(err instanceof Error ? err.message : 'Could not summarize this document.') }
    finally { setSummaryBusy(false) }
  }
  return <>
    <div className="intro-line"><div><h2>Read with clarity.</h2><p>Explore every section in its original wording, then ask for a plain-language explanation when you need one.</p></div><label className="level-picker">Reading level<select value={level} disabled={summaryBusy} onChange={e => { const next = e.target.value as 'simple' | 'detailed'; sessionStorage.setItem(`plainclause-level-${doc.id}`, next); setSummaryParts([]); setSummaryProgress(0); setSummaryLoaded(false); setSummaryError(''); setLevel(next) }}><option value="simple">Simple</option><option value="detailed">Detailed</option></select></label></div>
    <div className="info-strip"><BookOpen size={18} /><span>Explanations are generated one section at a time so nothing is silently skipped. Review the original text before relying on a summary.</span></div>
    <div className="summary-request"><div><strong>Document overview</strong><p>Generate a source-linked overview in small batches. Saved batches remain available after a refresh.</p></div><div className="summary-controls"><button className="outline-button" disabled={summaryBusy || !summaryLoaded} onClick={getSummary}>{summaryBusy ? 'Summarizing…' : summaryParts.length && summaryProgress < doc.chunks.length && summaryParts.every(part => part.status === 'answered') ? 'Continue overview' : summaryParts.length ? 'Refresh overview' : 'Generate overview'} <ArrowRight size={15} /></button>{summaryBusy && <button className="text-button" onClick={() => { cancelSummary.current = true; setStopPending(true) }}>{stopPending ? 'Stopping…' : 'Stop after this batch'}</button>}</div></div>
    {summaryError && <p className="error-text" role="alert">{summaryError}</p>}
    {(summaryBusy || summaryParts.length > 0) && <div className="summary-result"><div className="summary-progress" role="status"><span>{summaryProgress} of {doc.chunks.length} sections processed{summaryBusy ? '…' : '.'}</span>{summaryParts.length > 1 && <button className="outline-button" onClick={() => exportOverview(doc, summaryParts)}><Download size={15} /> Export overview</button>}</div>{!summaryBusy && summaryProgress < doc.chunks.length && <p className="coverage-note">This overview is incomplete. Review the remaining sections below; they may change the overall picture.</p>}{summaryParts.some(part => part.status !== 'answered') && <p className="coverage-note">The local model could not produce a verifiable summary for a batch. Its source text is shown instead.</p>}{summaryParts.map(part => <div key={part.start_offset}><AnswerView answer={part} title={`Sections ${part.start_offset + 1}–${part.start_offset + part.coverage_count}`} onExport={() => exportAnswer(doc, `Overview, sections ${part.start_offset + 1}–${part.start_offset + part.coverage_count}`, part)} />{part.status === 'answered' && part.uncited_headings.length > 0 && <p className="coverage-note">No source was cited for {part.uncited_headings.join(', ')}. Review {part.uncited_headings.length === 1 ? 'this section' : 'these sections'} below.</p>}</div>)}</div>}
    <div className="section-heading"><h3>Sections</h3><span>{doc.chunks.length} found</span></div>
    <div className="sections">{doc.chunks.map(chunk => <SectionRow key={chunk.id} chunk={chunk} doc={doc} level={level} />)}</div>
    <div className="closing-cta"><p>Something unclear in the wording?</p><button className="text-button" onClick={onAsk}>Ask about this document <ArrowRight size={16} /></button></div>
  </>
}

function Ask({ doc }: { doc: Document }) {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState('')
  const [error, setError] = useState('')
  useEffect(() => { let active = true; api.history(doc.id).then(items => { if (active) setHistory(items) }).catch(err => { if (active) setError(err instanceof Error ? err.message : 'Could not load conversation history.') }); return () => { active = false } }, [doc.id])
  async function ask(event: React.FormEvent) {
    event.preventDefault()
    const text = question.trim()
    if (text.length < 4) return
    setBusy(true); setError(''); setProgress('Starting document search')
    try { const result = await askStream(doc.id, text, setProgress); setHistory(current => [...current, { id: crypto.randomUUID(), question: text, answer: result, created_at: new Date().toISOString() }]); setQuestion('') }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not answer this question.') }
    finally { setBusy(false); setProgress('') }
  }
  return <div className="feature-page">
    <h2>Ask the document.</h2><p className="feature-subtitle">Questions are answered from retrieved passages in <strong>{doc.name}</strong>. If the text does not say, Plainclause will say so.</p>
    <form className="ask-form" onSubmit={ask}><label htmlFor="question">What would you like to understand?</label><div><input id="question" value={question} onChange={e => setQuestion(e.target.value)} maxLength={1000} placeholder="For example, how much notice is required to end this agreement?" /><button className="primary-button" disabled={busy || question.trim().length < 4}>{busy ? 'Reading…' : 'Ask'} <ArrowRight size={17} /></button></div></form>
    <div className="suggestions"><span>Try asking</span>{['What payments are required?', 'How can this agreement end?', 'What deadlines are mentioned?'].map(prompt => <button key={prompt} onClick={() => setQuestion(prompt)}>{prompt}</button>)}</div>
    {error && <p className="error-text" role="alert">{error}</p>}
    {busy && <p className="gentle-note" role="status">{progress}</p>}
    {history.length > 0 && <div className="conversation-history" aria-label="Conversation history">{history.map(item => <div className="ask-result" key={item.id}><div className="question-line"><HelpCircle size={17} /><strong>{item.question}</strong></div><AnswerView answer={item.answer} onExport={() => exportAnswer(doc, item.question, item.answer)} /></div>)}</div>}
  </div>
}

function ReviewRail({ doc, onAsk, onSection }: { doc: Document; onAsk: () => void; onSection: (id: string) => void }) {
  const review = useMemo(() => doc.chunks.flatMap(c => c.review_reasons.map(reason => ({ chunk: c, reason }))), [doc])
  const deadlines = useMemo(() => doc.chunks.flatMap(c => c.deadlines.map(date => ({ chunk: c, date }))), [doc])
  return <aside className="review-rail" aria-label="Review signals"><div className="rail-group"><div className="rail-title"><span className="rail-symbol amber">!</span><h3>Worth reviewing</h3><span className="rail-count">{review.length}</span></div><p className="rail-subtitle">Signals from the document text, not legal conclusions.</p>
    {review.length ? review.slice(0, 12).map(({ chunk, reason }, i) => <button onClick={() => onSection(chunk.id)} className="rail-item" key={`${chunk.id}-${i}`}><span className="rail-dot">!</span><span><strong>{chunk.heading}</strong><small>Page {chunk.page}</small><span>{reason}</span></span><ArrowRight size={15} /></button>) : <p className="rail-empty">No common review signals detected. That does not mean the document is risk-free.</p>}
    {review.length > 12 && <small>{review.length - 12} more signals appear in the sections.</small>}</div>
    <div className="rail-group"><div className="rail-title"><span className="rail-symbol teal">▢</span><h3>Dates & deadlines</h3><span className="rail-count">{deadlines.length}</span></div>{deadlines.length ? deadlines.slice(0, 10).map(({ chunk, date }, i) => <button onClick={() => onSection(chunk.id)} className="date-item" key={`${chunk.id}-${i}`}><strong>{date}</strong><small>{chunk.heading} · page {chunk.page}</small></button>) : <p className="rail-empty">No dates or notice periods detected. Check the original text.</p>}</div>
    <div className="rail-help"><MessageCircle size={19} /><strong>Need a closer look?</strong><p>Ask a question and inspect the cited passage.</p><button className="outline-button" onClick={onAsk}>Go to Ask <ArrowRight size={15} /></button></div>
  </aside>
}

export default function App() {
  const [docs, setDocs] = useState<DocSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(sessionStorage.getItem('plainclause-selected'))
  const [doc, setDoc] = useState<Document | null>(null)
  const [tab, setTab] = useState<Tab>('overview')
  const [status, setStatus] = useState<{ model_available: boolean; disclaimer: string; hosted_preview: boolean; hosted_service: boolean } | null>(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [indexProgress, setIndexProgress] = useState<IndexProgress | null>(null)
  const [indexError, setIndexError] = useState('')
  const [indexAttempt, setIndexAttempt] = useState(0)
  const fileInput = useRef<HTMLInputElement>(null)
  useEffect(() => { api.list().then(setDocs).catch(() => setError('The document service is unavailable. Please refresh and try again.')); api.status().then(setStatus).catch(() => undefined) }, [])
  useEffect(() => { const timer = window.setTimeout(() => setSearch(searchInput), 180); return () => window.clearTimeout(timer) }, [searchInput])
  useEffect(() => { if (!selectedId) { setDoc(null); return } sessionStorage.setItem('plainclause-selected', selectedId); api.document(selectedId).then(setDoc).catch(() => { setDoc(null); setSelectedId(null) }) }, [selectedId])
  useEffect(() => {
    if (!doc) { setIndexProgress(null); return }
    let active = true
    const id = doc.id
    setIndexError('')
    async function run() {
      try {
        const status = await api.indexStatus(id)
        if (!active) return
        setIndexProgress(status); setIndexError('')
        if (status.indexed >= status.total) return
        for (let offset = 0; offset < status.total && active; offset += 16) {
          const next = await api.indexBatch(id, offset)
          if (active) setIndexProgress(next)
        }
      } catch (err) { if (active) setIndexError(err instanceof Error ? err.message : 'Semantic indexing is unavailable.') }
    }
    void run()
    return () => { active = false }
  }, [doc?.id, indexAttempt])
  useEffect(() => { const handler = (event: BeforeUnloadEvent) => { if (busy) event.preventDefault() }; window.addEventListener('beforeunload', handler); return () => window.removeEventListener('beforeunload', handler) }, [busy])
  const filteredDocs = docs.filter(d => d.name.toLowerCase().includes(search.toLowerCase()))
  const isHosted = !!(status?.hosted_preview || status?.hosted_service)
  async function handleFile(file?: File) {
    if (!file) return
    setError('')
    if (file.size > 10 * 1024 * 1024) { setError('File exceeds the 10 MB limit.'); return }
    if (!/\.(pdf|docx|txt)$/i.test(file.name)) { setError('Choose a PDF, DOCX, or TXT file.'); return }
    setBusy('Starting upload…')
    try { const result = await upload(file, setBusy); setDocs(await api.list()); setSelectedId(result.id); setTab('overview') }
    catch (err) { setError(err instanceof Error ? err.message : 'Upload failed.') }
    finally { setBusy(''); if (fileInput.current) fileInput.current.value = '' }
  }
  async function removeDoc() {
    if (!doc || !window.confirm(`Permanently delete ${doc.name} from this workspace?`)) return
    try { await api.deleteDocument(doc.id); sessionStorage.removeItem(`plainclause-goals-${doc.id}`); sessionStorage.removeItem(`plainclause-level-${doc.id}`); setDocs(await api.list()); setDoc(null); setSelectedId(null); sessionStorage.removeItem('plainclause-selected') }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not delete this document.') }
  }
  async function removeAll() {
    if (!window.confirm('Permanently delete all documents and extracted text in this workspace?')) return
    try { await api.deleteAll(); docs.forEach(item => { sessionStorage.removeItem(`plainclause-goals-${item.id}`); sessionStorage.removeItem(`plainclause-level-${item.id}`) }); setDocs([]); setDoc(null); setSelectedId(null); sessionStorage.removeItem('plainclause-selected'); setError('') }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not delete workspace data.') }
  }
  return <div className="app-shell">
    <header className="topbar"><div className="brand"><span className="brand-name">Plainclause</span><span className="brand-line">Your documents. Your understanding.</span></div><div className="top-actions"><span className="local-status"><LockKeyhole size={17} /><span>{status?.hosted_service ? 'Hosted service' : status?.hosted_preview ? 'Hosted preview' : 'Local workspace'}<small>{status?.model_available ? 'AI ready' : 'AI model unavailable · sources still work'}</small></span></span><button className="top-delete" onClick={removeAll}><Trash2 size={18} /> Delete my data</button></div></header>
    <aside className="sidebar"><div className="upload-area" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); void handleFile(e.dataTransfer.files[0]) }}><input ref={fileInput} type="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" onChange={e => void handleFile(e.target.files?.[0])} aria-label="Upload a PDF, DOCX, or TXT document" /><button className="upload-button" disabled={!!busy} onClick={() => fileInput.current?.click()}><span className="upload-icon"><UploadCloud size={23} /></span><strong>{busy || 'Upload a document'}</strong><span>{busy ? 'Please keep this page open' : 'Drop a file here or click to browse'}</span></button><small>PDF, DOCX, TXT · 10 MB max · 200 PDF pages</small></div>
      {status?.hosted_preview && <p className="hosted-notice" role="note">Temporary online preview: uploads pass through a secure tunnel provider to this computer. Delete your data when done. The link works only while this computer and tunnel are running.</p>}
      {status?.hosted_service && <p className="hosted-notice" role="note">Hosted evaluation service: documents and AI processing stay on the service provider's infrastructure. Delete your data when done. Do not upload confidential documents.</p>}
      <div className="sidebar-heading"><h2>Documents</h2><Search size={18} /></div>{docs.length > 4 && <input className="doc-search" value={searchInput} onChange={e => setSearchInput(e.target.value)} placeholder="Find a document" aria-label="Find a document" />}
      <nav className="doc-list" aria-label="Documents">{filteredDocs.map(d => <button key={d.id} className={selectedId === d.id ? 'selected' : ''} onClick={() => { setSelectedId(d.id); setTab('overview') }}><FileText size={20} /><span><strong>{d.name}</strong><small>{d.section_count} sections · {d.file_type.toUpperCase()}</small></span></button>)}{!docs.length && <p className="sidebar-empty">Your documents will appear here.</p>}</nav>
      <div className="privacy-note"><LockKeyhole size={17} /><div><strong>{status?.hosted_service ? "Hosted workspace" : status?.hosted_preview ? "Temporary preview" : "Private by design"}</strong><p>{status?.hosted_service ? "Extracted text and local AI processing remain on the hosted service and its attached storage. Delete your data when done." : status?.hosted_preview ? "Uploads pass through a secure tunnel provider to this computer, where documents and AI processing remain. Delete your data when done; this preview link and host are temporary." : "Extracted text stays in this local service. No paid cloud account is needed."}</p></div></div>
    </aside>
    <main className="main-panel">{error && <div className="global-error" role="alert">{error}<button aria-label="Dismiss error" onClick={() => setError('')}><X size={16} /></button></div>}
      {!doc ? <EmptyWorkspace onBrowse={() => fileInput.current?.click()} hosted={isHosted} /> : <><div className="document-head"><div className="document-icon"><FileText size={27} /></div><div><h1>{doc.name}</h1><p>{doc.chunks.length} sections · {doc.file_type.toUpperCase()} · Added {new Date(doc.created_at + 'Z').toLocaleDateString()}</p></div><button className="icon-button remove-document" title="Delete this document" aria-label="Delete this document" onClick={removeDoc}><Trash2 size={18} /></button></div>
        {indexProgress && indexProgress.indexed < indexProgress.total && <p className="info-strip" role="status">Building local semantic index: {indexProgress.indexed} of {indexProgress.total} sections. Document reading and lexical search are available.</p>}
        {indexError && <p className="coverage-note" role="status">{indexError} Precise-word search remains available. <button className="text-button" onClick={() => setIndexAttempt(value => value + 1)}>Retry indexing</button></p>}
        <nav className="tabs" aria-label="Document tools">{([['overview', 'Overview'], ['ask', 'Ask'], ['compare', 'Compare'], ['prepare', 'Prepare']] as const).map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} aria-current={tab === key ? 'page' : undefined} onClick={() => setTab(key)}>{label}</button>)}</nav>
        <div className="tab-content">{tab === 'overview' && <Overview key={doc.id} doc={doc} onAsk={() => setTab('ask')} />}{tab === 'ask' && <Ask key={doc.id} doc={doc} />}{tab === 'compare' && <Suspense fallback={<p role="status">Opening comparison?</p>}><Compare docs={docs} selectedId={doc.id} /></Suspense>}{tab === 'prepare' && <Suspense fallback={<p role="status">Opening preparation sheet?</p>}><Prepare key={doc.id} doc={doc} /></Suspense>}</div></>}
    </main>
    {doc && <ReviewRail doc={doc} onAsk={() => setTab('ask')} onSection={id => { setTab('overview'); window.setTimeout(() => document.getElementById(`section-${id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 0) }} />}
    <footer className="global-disclaimer"><ClipboardList size={15} />{DISCLAIMER} Check the original document and local law; consult a licensed professional for advice.</footer>
  </div>
}
