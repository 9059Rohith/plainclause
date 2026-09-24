import type { Answer, Comparison, Document, Prep, SummaryAnswer } from './types'

function save(name: string, content: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/markdown;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = name.replace(/[^a-z0-9._-]/gi, '_') + '.md'
  link.click()
  URL.revokeObjectURL(url)
}

export function answerMarkdown(doc: Document, question: string, answer: Answer) {
  return `# ${doc.name}\n\n**Question:** ${question}\n\n${answer.answer}\n\n## Sources\n${answer.citations.map(c => `- ${c.heading} (page ${c.page}): “${c.quote}”`).join('\n')}\n\n${answer.disclaimer}\n`
}

export function exportAnswer(doc: Document, question: string, answer: Answer) {
  save('plainclause-answer', answerMarkdown(doc, question, answer))
}

export function exportOverview(doc: Document, parts: SummaryAnswer[]) {
  save('plainclause-overview', `# Document overview · ${doc.name}\n\n${parts.map(part => `## Sections ${part.start_offset + 1}–${part.start_offset + part.coverage_count}\n\n${part.answer}\n\nSources:\n${part.citations.map(c => `- ${c.heading} (page ${c.page}): “${c.quote}”`).join('\n')}\n\nUncited sections to review: ${part.uncited_headings.join(', ') || 'none'}`).join('\n\n')}\n\n${parts.reduce((n, part) => n + part.coverage_count, 0)} of ${doc.chunks.length} sections processed.\n\n${parts[0]?.disclaimer || ''}\n`)
}

export function prepMarkdown(prep: Prep) {
  return `# Lawyer consultation prep · ${prep.document}\n\n${prep.disclaimer}\n\n## My goals and context\n${prep.user_goals?.trim() || 'Not entered.'}\n\n## Key passages from the document\n${prep.facts.map(x => `- ${x.source} (page ${x.page}): ${x.excerpt}`).join('\n') || '- No common clause category was detected; inspect the full document.'}\n\n## Checklist\n${prep.checklist.map(x => `- [ ] ${x}`).join('\n')}\n\n## Questions to discuss\n${prep.questions.map(x => `- ${x.question} (${x.source})`).join('\n') || '- No review signals were detected. Bring any concerns you have.'}\n\n## Dates and periods to verify\n${prep.deadlines.map(x => `- ${x.text} (${x.source})`).join('\n') || '- None detected automatically.'}\n\n## Types of help to consider\n${prep.resources.map(x => `- ${x}`).join('\n')}\n`
}

export function exportPrep(prep: Prep) {
  save('plainclause-lawyer-prep', prepMarkdown(prep))
}

export function comparisonMarkdown(result: Comparison) {
  return `# Comparison · ${result.base}\n\n${result.disclaimer}\n\n${result.comparisons.map(c => `## Compared with ${c.name}\n${c.rows.map(r => `### ${r.heading} · ${r.status}\n${r.changed_terms.map(term => `${term.label}: ${term.before} → ${term.after}`).join('\n')}\nBefore: ${r.before || '—'}\n\nAfter: ${r.after || '—'}`).join('\n\n') || 'No text differences detected.'}`).join('\n\n')}`
}

export function exportComparison(result: Comparison) {
  save('plainclause-comparison', comparisonMarkdown(result))
}
