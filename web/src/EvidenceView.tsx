interface EvidenceItem {
  number: string
  title: string
  url: string
  summary: string
}

function parseEvidence(raw: string): EvidenceItem[] {
  return raw.split(/\n\s*\n/).flatMap((block) => {
    const match = block.match(/^\[(\d+)\] 标题：([^\n]+)\nURL：([^\n]+)\n文本：([\s\S]+)$/)
    if (!match) return []
    const [, number, title, url, summary] = match
    try {
      const parsedUrl = new URL(url.trim())
      if (!['http:', 'https:'].includes(parsedUrl.protocol)) return []
      return [{ number, title: title.trim(), url: parsedUrl.href, summary: summary.trim() }]
    } catch {
      return []
    }
  })
}

export default function EvidenceView({ evidence }: { evidence: string }) {
  const items = parseEvidence(evidence)

  return (
    <details className="evidence-card">
      <summary>参考资料 · {items.length}</summary>
      <p className="muted">
        以下是搜索时取得的网页摘要，仅供追溯参考；不代表每项活动均由来源直接支持，
        也不能证明当前票价、开放时间或交通安排。请以来源网页和官方信息为准。
      </p>
      {items.length ? (
        <ol className="evidence-list">
          {items.map((item) => (
            <li key={`${item.number}-${item.url}`}>
              <a href={item.url} target="_blank" rel="noopener noreferrer">
                {item.title}
              </a>
              <p className="muted">搜索摘要：{item.summary}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p className="muted">这份行程未保存可展示的网页来源。</p>
      )}
    </details>
  )
}
