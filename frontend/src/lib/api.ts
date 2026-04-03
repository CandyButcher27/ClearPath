import type { CompleteEvent } from '../types/api'

const BASE = '/api'

/**
 * Upload 3 PDF files to the verification API.
 * Returns the job_id to poll for status.
 */
export async function submitDocuments(
  bol: File,
  invoice: File,
  packingList: File,
): Promise<{ job_id: string }> {
  const form = new FormData()
  form.append('bill_of_lading', bol)
  form.append('invoice', invoice)
  form.append('packing_list', packingList)

  const res = await fetch(`${BASE}/verify`, { method: 'POST', body: form })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Upload failed (${res.status}): ${text}`)
  }
  return res.json()
}

/**
 * Create an EventSource connected to the job status SSE stream.
 * The caller is responsible for closing it.
 */
export function createStatusStream(jobId: string): EventSource {
  return new EventSource(`${BASE}/verify/${jobId}/status`)
}

/**
 * Parse the 'complete' event payload from the SSE stream.
 */
export function parseCompleteEvent(raw: string): CompleteEvent {
  try {
    return JSON.parse(raw) as CompleteEvent
  } catch {
    return { results: null, error: 'Failed to parse results', status: 'error' }
  }
}

/**
 * Return the URL for downloading the PDF report for a given job.
 */
export function getReportUrl(jobId: string): string {
  return `${BASE}/verify/${jobId}/report`
}
