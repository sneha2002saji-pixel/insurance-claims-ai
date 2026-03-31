import { NextResponse } from 'next/server'
import { getIdentityToken } from '@/lib/gcp-auth'

const AGENT_URL = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8000'

async function agentHeaders(extra?: Record<string, string>): Promise<Record<string, string>> {
  const token = await getIdentityToken(AGENT_URL)
  const headers: Record<string, string> = { ...extra }
  if (token) headers['Authorization'] = `Bearer ${token}`
  return headers
}

export async function GET(): Promise<NextResponse> {
  try {
    const res = await fetch(`${AGENT_URL}/claims`, {
      cache: 'no-store',
      headers: await agentHeaders(),
    })
    if (!res.ok) {
      return NextResponse.json(
        { error: { code: 'UPSTREAM_ERROR', message: 'Failed to fetch claims' } },
        { status: res.status },
      )
    }
    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'Internal server error' } },
      { status: 500 },
    )
  }
}

export async function POST(request: Request): Promise<NextResponse> {
  try {
    const body: unknown = await request.json()
    const res = await fetch(`${AGENT_URL}/claims`, {
      method: 'POST',
      headers: await agentHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err: unknown = await res.json()
      return NextResponse.json(err, { status: res.status })
    }
    const data: unknown = await res.json()
    return NextResponse.json(data, { status: 201 })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'Internal server error' } },
      { status: 500 },
    )
  }
}
