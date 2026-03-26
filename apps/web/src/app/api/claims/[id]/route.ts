import { NextResponse } from 'next/server'

const AGENT_URL = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8000'

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params
  try {
    const res = await fetch(`${AGENT_URL}/claims/${id}`, { cache: 'no-store' })
    if (!res.ok) {
      return NextResponse.json(
        { error: { code: 'NOT_FOUND', message: 'Claim not found' } },
        { status: 404 },
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
