/**
 * Fetches a GCP identity token from the metadata server (only works on Cloud Run / GCE).
 * Falls back gracefully in local dev (returns undefined).
 */
export async function getIdentityToken(audience: string): Promise<string | undefined> {
  try {
    const metadataUrl = `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(audience)}`
    const res = await fetch(metadataUrl, {
      headers: { 'Metadata-Flavor': 'Google' },
      // Short timeout so local dev doesn't hang
      signal: AbortSignal.timeout(1000),
    })
    if (!res.ok) return undefined
    return await res.text()
  } catch {
    return undefined
  }
}
