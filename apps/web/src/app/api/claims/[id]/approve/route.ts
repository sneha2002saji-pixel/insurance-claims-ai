import { NextResponse } from 'next/server'

const AGENT_URL = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8000'

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params
  try {
    const body: unknown = await request.json()
    const res = await fetch(`${AGENT_URL}/claims/${id}/resume`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err: unknown = await res.json()
      return NextResponse.json(err, { status: res.status })
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
