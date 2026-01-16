export type ProgressEvent = {
  step: string
  status: 'pending' | 'running' | 'done' | 'error'
  message: string
  ts: string
}

export type FileMeta = {
  name: string
  size_bytes: number
  pages: number | null
  download_url: string
}

export type Outputs = {
  annotated_a_pdf: string
  annotated_b_pdf: string
  extracted_a_json: string
  extracted_b_json: string
  matched_json: string
  diff_json: string
  summary_md: string
  detailed_json: string
}

export type StatusResponse = {
  job_id: string
  state: 'queued' | 'running' | 'done' | 'error'
  progress: ProgressEvent[]
  error?: string
}

export type ResultResponse = {
  job_id: string
  state: 'done'
  files: { file_a: FileMeta; file_b: FileMeta }
  outputs: Outputs
  diff_counts?: any
}
