import { NextResponse } from 'next/server'
import { getIdentityToken } from '@/lib/gcp-auth'

const AGENT_URL = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8000'
const UUID_RE = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i

const VALID_DECISIONS = ['approved', 'rejected', 'partial_settlement'] as const
type Decision = (typeof VALID_DECISIONS)[number]

function isValidDecision(value: unknown): value is Decision {
  return typeof value === 'string' && (VALID_DECISIONS as readonly string[]).includes(value)
}

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params

  if (!UUID_RE.test(id)) {
    return NextResponse.json(
      { error: { code: 'INVALID_ID', message: 'Invalid claim ID' } },
      { status: 400 },
    )
  }

  try {
    const body: unknown = await request.json()

    if (
      typeof body !== 'object' ||
      body === null ||
      !isValidDecision((body as Record<string, unknown>).decision)
    ) {
      return NextResponse.json(
        {
          error: {
            code: 'INVALID_DECISION',
            message: 'decision must be one of: approved, rejected, partial_settlement',
          },
        },
        { status: 400 },
      )
    }

    const token = await getIdentityToken(AGENT_URL)
    const resumeHeaders: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) resumeHeaders['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${AGENT_URL}/claims/${id}/resume`, {
      method: 'POST',
      headers: resumeHeaders,
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      return NextResponse.json(
        { error: { code: 'UPSTREAM_ERROR', message: 'Failed to process decision' } },
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
