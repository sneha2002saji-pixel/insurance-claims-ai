import { NextResponse } from 'next/server'

const AGENT_URL = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8000'
const UUID_RE = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i

function validateId(id: string): NextResponse | null {
  if (!UUID_RE.test(id)) {
    return NextResponse.json(
      { error: { code: 'INVALID_ID', message: 'Invalid claim ID' } },
      { status: 400 },
    )
  }
  return null
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params
  const idError = validateId(id)
  if (idError) return idError
  try {
    const res = await fetch(`${AGENT_URL}/claims/${id}`, { cache: 'no-store' })
    if (!res.ok) {
      if (res.status === 404) {
        return NextResponse.json(
          { error: { code: 'NOT_FOUND', message: 'Claim not found' } },
          { status: 404 },
        )
      }
      return NextResponse.json(
        { error: { code: 'UPSTREAM_ERROR', message: 'Failed to fetch claim' } },
        { status: 502 },
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

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await params
  const idError = validateId(id)
  if (idError) return idError
  try {
    const res = await fetch(`${AGENT_URL}/claims/${id}`, {
      method: 'DELETE',
      cache: 'no-store',
    })
    if (!res.ok) {
      const data: unknown = res.status === 404
        ? { error: { code: 'NOT_FOUND', message: 'Claim not found' } }
        : { error: { code: 'UPSTREAM_ERROR', message: 'Failed to delete claim' } }
      return NextResponse.json(data, { status: res.status })
    }
    return new NextResponse(null, { status: 204 })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'Internal server error' } },
      { status: 500 },
    )
  }
}
