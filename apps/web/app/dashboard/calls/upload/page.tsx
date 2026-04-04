'use client'

import { useState, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { Upload, Mic, Phone, User, FileAudio, CheckCircle2 } from 'lucide-react'

const API = 'http://localhost:8000'

export default function UploadCallPage() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragging, setDragging] = useState(false)
  const [phoneNumber, setPhoneNumber] = useState('')
  const [repName, setRepName] = useState('')
  const [notes, setNotes] = useState('')
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) setFile(dropped)
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError('')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('phone_number', phoneNumber)
    formData.append('rep_name', repName)
    formData.append('call_type', 'inbound')
    formData.append('notes', notes)

    try {
      const res = await fetch(`${API}/api/v1/calls/upload`, { method: 'POST', body: formData })
      if (res.ok) {
        setSuccess(true)
        setTimeout(() => router.push('/dashboard/calls'), 2000)
      } else {
        const d = await res.json()
        setError(d.detail || 'Upload failed')
      }
    } catch {
      setError('Cannot reach API — is the backend running?')
    } finally {
      setUploading(false)
    }
  }

  const fmtSize = (b: number) => b < 1024 * 1024 ? `${(b / 1024).toFixed(0)} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`

  return (
    <div className="max-w-xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Log Inbound Call</h1>
        <p className="text-sm text-gray-500 mt-1">Upload a GSM call recording for local AI transcription and sales analysis</p>
      </div>

      <div className="bg-white rounded-xl border p-6 space-y-5">
        {/* Drop zone */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Call Recording <span className="text-red-400">*</span>
          </label>
          <div
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${
              dragging ? 'border-blue-400 bg-blue-50' : file ? 'border-green-300 bg-green-50' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".mp3,.wav,.m4a,.ogg,.aac,.mp4,.webm"
              className="hidden"
              onChange={e => setFile(e.target.files?.[0] || null)}
            />
            {file ? (
              <div className="space-y-1">
                <FileAudio size={28} className="text-green-500 mx-auto" />
                <p className="text-sm font-medium text-green-700">{file.name}</p>
                <p className="text-xs text-green-500">{fmtSize(file.size)}</p>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload size={28} className="text-gray-300 mx-auto" />
                <p className="text-sm text-gray-500">Drag & drop or click to select</p>
                <p className="text-xs text-gray-400">MP3, WAV, M4A, OGG, AAC, MP4</p>
              </div>
            )}
          </div>
        </div>

        {/* Phone number */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            <span className="flex items-center gap-1.5"><Phone size={13} className="text-gray-400" /> Customer Phone Number</span>
          </label>
          <input
            value={phoneNumber}
            onChange={e => setPhoneNumber(e.target.value)}
            placeholder="+90 5xx xxx xx xx"
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Rep name */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            <span className="flex items-center gap-1.5"><User size={13} className="text-gray-400" /> Sales Rep Name</span>
          </label>
          <input
            value={repName}
            onChange={e => setRepName(e.target.value)}
            placeholder="Rep name"
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            <span className="flex items-center gap-1.5"><Mic size={13} className="text-gray-400" /> Notes (optional)</span>
          </label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="Any context about this call…"
            rows={3}
            className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{error}</div>
        )}

        {success ? (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
            <CheckCircle2 size={16} />
            Call uploaded! AI analysis started. Redirecting…
          </div>
        ) : (
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Uploading & processing…' : 'Upload & Analyze'}
          </button>
        )}

        <p className="text-xs text-gray-400 text-center">
          Transcribed locally with Whisper · Analyzed with Ollama qwen3:8b · No data leaves your machine
        </p>
      </div>
    </div>
  )
}
