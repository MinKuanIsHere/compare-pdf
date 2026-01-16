import { DragEvent, useEffect, useMemo, useRef, useState } from 'react'
import { getResult, getStatus, startCompare } from './api'
import { ResultResponse, StatusResponse } from './types'

type ChangeItem = { id: string; label: string; page?: number; bbox?: number[]; type: 'added' | 'deleted' | 'modified' }

function humanSize(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${(bytes / 1024 ** i).toFixed(1)} ${units[i]}`
}

export default function App() {
  const [fileA, setFileA] = useState<File | null>(null)
  const [fileB, setFileB] = useState<File | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [status, setStatus] = useState<StatusResponse | null>(null)
  const [result, setResult] = useState<ResultResponse | null>(null)
  const [diffList, setDiffList] = useState<ChangeItem[]>([])
  const [textThreshold, setTextThreshold] = useState(0.8)
  const [imageThreshold, setImageThreshold] = useState(5)
  const pollRef = useRef<number | null>(null)
  const [dragging, setDragging] = useState<{ a: boolean; b: boolean }>({ a: false, b: false })

  const canRun = useMemo(() => !!fileA && !!fileB, [fileA, fileB])

  useEffect(() => {
    if (!jobId) return
    let cancelled = false

    const poll = async () => {
      try {
        const s = await getStatus(jobId)
        if (cancelled) return
        setStatus(s)
        if (s.state === 'done') {
          const r = await getResult(jobId)
          if (!cancelled) setResult(r)
          if (pollRef.current) window.clearInterval(pollRef.current)
        } else if (s.state === 'error') {
          if (pollRef.current) window.clearInterval(pollRef.current)
        }
      } catch (err) {
        console.error(err)
      }
    }

    const timer = window.setInterval(poll, 1500)
    pollRef.current = timer
    poll()
    return () => {
      cancelled = true
      window.clearInterval(timer)
      pollRef.current = null
    }
  }, [jobId])

  const submit = async () => {
    if (!fileA || !fileB) return
    const form = new FormData()
    form.append('file_a', fileA)
    form.append('file_b', fileB)
    form.append('text_threshold', String(textThreshold))
    form.append('image_threshold', String(imageThreshold))
    const res = await startCompare(form)
    setJobId(res.job_id)
    setStatus({ job_id: res.job_id, state: 'queued', progress: [] })
    setResult(null)
    setDiffList([])
  }

  const handleDrop = (e: DragEvent<HTMLLabelElement>, which: 'a' | 'b') => {
    e.preventDefault()
    setDragging(prev => ({ ...prev, [which]: false }))
    const file = e.dataTransfer.files?.[0]
    if (file && file.type === 'application/pdf') {
      which === 'a' ? setFileA(file) : setFileB(file)
    }
  }

  const handleDragOver = (e: DragEvent<HTMLLabelElement>, which: 'a' | 'b') => {
    e.preventDefault()
    setDragging(prev => ({ ...prev, [which]: true }))
  }

  const handleDragLeave = (_e: DragEvent<HTMLLabelElement>, which: 'a' | 'b') => {
    setDragging(prev => ({ ...prev, [which]: false }))
  }

  // load diff list once result is available
  useEffect(() => {
    const loadDiff = async () => {
      if (!result?.outputs?.diff_json) return
      try {
        const [diffRes, matchRes] = await Promise.all([
          fetch(result.outputs.diff_json),
          fetch(result.outputs.matched_json),
        ])
        const data = await diffRes.json()
        const matched = await matchRes.json()
        const items: ChangeItem[] = []
        ;(matched.paragraphs?.[1] || []).forEach((p: any, idx: number) =>
          items.push({ id: `pa-new-${idx}`, label: p.text?.slice(0, 60) || 'New paragraph', page: p.page, bbox: p.bbox, type: 'added' })
        )
        ;(matched.paragraphs?.[2] || []).forEach((p: any, idx: number) =>
          items.push({ id: `pa-del-${idx}`, label: p.text?.slice(0, 60) || 'Deleted paragraph', page: p.page, bbox: p.bbox, type: 'deleted' })
        )
        ;(matched.images?.[1] || []).forEach((i: any, idx: number) =>
          items.push({ id: `im-new-${idx}`, label: `New image ${i.uid ?? ''}`, page: i.page, bbox: i.bbox, type: 'added' })
        )
        ;(matched.images?.[2] || []).forEach((i: any, idx: number) =>
          items.push({ id: `im-del-${idx}`, label: `Deleted image ${i.uid ?? ''}`, page: i.page, bbox: i.bbox, type: 'deleted' })
        )
        ;(matched.tables?.[1] || []).forEach((t: any, idx: number) =>
          items.push({ id: `tb-new-${idx}`, label: `New table ${t.uid ?? ''}`, page: t.page, bbox: t.bbox, type: 'added' })
        )
        ;(matched.tables?.[2] || []).forEach((t: any, idx: number) =>
          items.push({ id: `tb-del-${idx}`, label: `Deleted table ${t.uid ?? ''}`, page: t.page, bbox: t.bbox, type: 'deleted' })
        )

        ;(data.paragraphs || []).forEach((p: any, idx: number) =>
          items.push({
            id: `p-${idx}`,
            label: `${p.text_a ? p.text_a.slice(0, 60) : ''} -> ${p.text_b ? p.text_b.slice(0, 60) : ''}`,
            page: p.page,
            bbox: p.bbox,
            type: 'modified',
          })
        )
        ;(data.images || []).forEach((i: any, idx: number) =>
          items.push({ id: `i-${idx}`, label: `Image change ${i.uid_b ?? ''}`, page: i.page, bbox: i.bbox, type: 'modified' })
        )
        ;(data.tables || []).forEach((t: any, idx: number) =>
          items.push({ id: `t-${idx}`, label: `Table change ${t.uid_b ?? ''}`, page: t.page, bbox: t.bbox, type: 'modified' })
        )
        setDiffList(items)
      } catch (err) {
        console.error('load diff failed', err)
      }
    }
    loadDiff()
  }, [result])

  const onSelectChange = (item: ChangeItem) => {
    // hook for future bbox scroll; currently just logs
    console.log('jump to', item.page, item.bbox)
  }

  return (
    <div className="app-shell">
      <h1>PDF Compare</h1>

      <div className="panel">
        <h3 style={{ marginTop: 0, marginBottom: 12 }}>Upload</h3>
        <div className="flex" style={{ alignItems: 'center' }}>
          <div className="column">
            <div className="upload-title">File A (Original)</div>
            <div className="upload-sub">Upload the original PDF</div>
            <label
              className="upload-box"
              onDragOver={e => handleDragOver(e, 'a')}
              onDragLeave={e => handleDragLeave(e, 'a')}
              onDrop={e => handleDrop(e, 'a')}
              style={{ borderColor: dragging.a ? '#7c6bff' : undefined }}
            >
              <input type="file" accept="application/pdf" style={{ display: 'none' }} onChange={e => setFileA(e.target.files?.[0] ?? null)} />
              <div style={{ fontSize: 32 }}>📄</div>
              <div>{fileA ? fileA.name : 'Drop or click to upload'}</div>
              <div className="status">PDF only</div>
            </label>
          </div>
          <div className="swap">⇆</div>
          <div className="column">
            <div className="upload-title">File B (Modified)</div>
            <div className="upload-sub">Upload the modified PDF</div>
            <label
              className="upload-box"
              onDragOver={e => handleDragOver(e, 'b')}
              onDragLeave={e => handleDragLeave(e, 'b')}
              onDrop={e => handleDrop(e, 'b')}
              style={{ borderColor: dragging.b ? '#7c6bff' : undefined }}
            >
              <input type="file" accept="application/pdf" style={{ display: 'none' }} onChange={e => setFileB(e.target.files?.[0] ?? null)} />
              <div style={{ fontSize: 32 }}>📄</div>
              <div>{fileB ? fileB.name : 'Drop or click to upload'}</div>
              <div className="status">PDF only</div>
            </label>
          </div>
        </div>
        <div className="flex" style={{ marginTop: 14 }}>
          <div className="column">
            <label>Text similarity threshold (0-1, difflib ratio)</label>
            <input type="number" min="0" max="1" step="0.05" value={textThreshold} onChange={e => setTextThreshold(parseFloat(e.target.value))} />
          </div>
          <div className="column">
            <label>Image pHash distance threshold (smaller = more similar)</label>
            <input type="number" min="0" max="64" step="1" value={imageThreshold} onChange={e => setImageThreshold(parseInt(e.target.value))} />
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <button disabled={!canRun} onClick={submit}>Run Comparison</button>
          {status && <span style={{ marginLeft: 10 }} className="status">Status: {status.state}</span>}
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Progress</h3>
        {(status?.progress ?? []).map((p, idx) => (
          <div key={idx} className="status">[{p.ts}] {p.step} - {p.status} {p.message}</div>
        ))}
        {!status && <div className="status">Not started</div>}
      </div>

      {result && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Preview (Annotated PDFs)</h3>
          <div className="viewer-grid">
            <div>
              <div className="pill">A-view annotations</div>
              <div className="pdf-frame">
                <object data={result.outputs.annotated_a_pdf} type="application/pdf" width="100%" height="100%">
                  <iframe title="annotated-a" src={result.outputs.annotated_a_pdf} style={{ width: '100%', height: '100%', border: 'none' }} />
                </object>
              </div>
            </div>
            <div>
              <div className="pill">B-view annotations</div>
              <div className="pdf-frame">
                <object data={result.outputs.annotated_b_pdf} type="application/pdf" width="100%" height="100%">
                  <iframe title="annotated-b" src={result.outputs.annotated_b_pdf} style={{ width: '100%', height: '100%', border: 'none' }} />
                </object>
              </div>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Results & Downloads</h3>
          <div className="flex">
            <div className="column">
              <div className="pill">Originals</div>
              <div className="status"><a href={result.files.file_a.download_url} download>File A</a> ({humanSize(result.files.file_a.size_bytes)})</div>
              <div className="status"><a href={result.files.file_b.download_url} download>File B</a> ({humanSize(result.files.file_b.size_bytes)})</div>
            </div>
            <div className="column">
              <div className="pill">Annotations</div>
              <div className="status"><a href={result.outputs.annotated_a_pdf} download>A-view annotated</a></div>
              <div className="status"><a href={result.outputs.annotated_b_pdf} download>B-view annotated</a></div>
            </div>
            <div className="column">
              <div className="pill">Reports</div>
              <div className="status"><a href={result.outputs.diff_json} download>Diff JSON</a></div>
              <div className="status"><a href={result.outputs.summary_md} download>Summary MD</a></div>
              <div className="status"><a href={result.outputs.detailed_json} download>Detailed JSON</a></div>
            </div>
          </div>
        </div>
      )}

      <div className="panel" style={{ marginTop: 12 }}>
        <h3 style={{ marginTop: 0 }}>Annotation palette</h3>
        <div className="flex">
          <div className="pill" style={{ background: 'rgba(51, 204, 102, 0.2)', color: '#32d082' }}>Added (B-view) 0.2, 0.8, 0.4</div>
          <div className="pill" style={{ background: 'rgba(243, 85, 85, 0.2)', color: '#f87171' }}>Deleted (A-view) 0.95, 0.3, 0.3</div>
          <div className="pill" style={{ background: 'rgba(64, 122, 214, 0.2)', color: '#7eb3ff' }}>Modified (A/B) 0.25, 0.55, 0.9</div>
        </div>
      </div>

      <div className="panel">
        <h3 style={{ marginTop: 0 }}>Changes (click to jump)</h3>
        <div className="changes">
          {diffList.length === 0 && <div className="status">No changes yet (parsed after completion)</div>}
          {diffList.map(item => (
            <div key={item.id} className="change-item" onClick={() => onSelectChange(item)}>
              <span className={`tag ${item.type}`}>{item.type === 'added' ? 'Added' : item.type === 'deleted' ? 'Deleted' : 'Modified'}</span>
              <span>{item.label}</span>
              {item.page !== undefined && <span className="status"> p.{item.page + 1}</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
