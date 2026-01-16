import axios from 'axios'
import { ResultResponse, StatusResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

const withBase = (path: string) => (path.startsWith('http') ? path : `${API_BASE}${path}`)

export async function startCompare(form: FormData) {
  const res = await axios.post(`${API_BASE}/compare`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data as { job_id: string; state: string }
}

export async function getStatus(jobId: string) {
  const res = await axios.get(`${API_BASE}/status/${jobId}`)
  return res.data as StatusResponse
}

export async function getResult(jobId: string) {
  const res = await axios.get(`${API_BASE}/result/${jobId}`)
  const data = res.data as ResultResponse
  // inject absolute URLs
  data.files.file_a.download_url = withBase(data.files.file_a.download_url)
  data.files.file_b.download_url = withBase(data.files.file_b.download_url)
  Object.entries(data.outputs).forEach(([k, v]) => {
    // @ts-expect-error dynamic assign
    data.outputs[k] = withBase(v as string)
  })
  return data
}
