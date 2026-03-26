const AGENT_URL = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8000'

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params

  const agentRes = await fetch(`${AGENT_URL}/claims/${id}/run`, {
    method: 'POST',
    headers: { Accept: 'text/event-stream' },
  })

  if (!agentRes.ok || !agentRes.body) {
    return new Response(
      JSON.stringify({
        error: { code: 'UPSTREAM_ERROR', message: 'Failed to start pipeline' },
      }),
      {
        status: agentRes.status,
        headers: { 'Content-Type': 'application/json' },
      },
    )
  }

  // Proxy the SSE stream directly to the client
  return new Response(agentRes.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
