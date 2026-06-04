/**
 * socApi.ts — Client for the O*NET/SOC prediction endpoints
 *
 * Endpoints (served by backend/main.py, same base URL as skillsApi):
 *   POST /predict-soc   — predict SOC codes from a list of skills
 *   POST /adjacent-socs — find SOC codes adjacent to a given SOC
 *   GET  /soc/{code}    — get details for a specific SOC code
 */
 
// ── Response types ──────────────────────────────────────────────────────────
 
export interface SocPrediction {
  soc: string
  title: string
  score: number
  hard_matches?: string[]
  soft_matches?: string[]
}
 
export interface PredictSocResponse {
  predictions: SocPrediction[]
  not_found: string[]
}
 
export interface AdjacentSocEntry {
  soc: string
  title: string
  score: number
}
 
export interface AdjacentSocsResponse {
  same_category: AdjacentSocEntry[]
  cross_category: AdjacentSocEntry[]
}
 
export interface SocDetails {
  soc: string
  title: string
  major_group: string
  hard_skills: string[]
  soft_skills: string[]
  total_skills: number
}
 
// ── Helpers ─────────────────────────────────────────────────────────────────
 
function getBaseUrl(): string {
  return (
    process.env.NEXT_PUBLIC_SKILLS_API_URL || 'http://localhost:8000'
  )
}
 
// ── Public API functions ────────────────────────────────────────────────────
 
/**
 * Predict the most likely SOC codes for a list of user skills.
 * Calls POST /predict-soc
 */
export async function predictSocApi(
  skills: string[],
  top_n: number = 5,
  alpha: number = 0.6,
  signal?: AbortSignal,
): Promise<PredictSocResponse> {
  if (!skills || skills.length === 0) {
    return { predictions: [], not_found: [] }
  }
 
  const res = await fetch(`${getBaseUrl()}/predict-soc`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ skills, top_n, alpha }),
    signal,
  })
 
  if (!res.ok) {
    console.warn('[socApi] predict-soc returned', res.status)
    return { predictions: [], not_found: [] }
  }
 
  return res.json()
}
 
/**
 * Find SOC codes adjacent to a given SOC for upskilling.
 * Optionally pass user skills to influence the ranking.
 * Calls POST /adjacent-socs
 */
export async function adjacentSocsApi(
  soc: string,
  top_n: number = 5,
  skills?: string[],
  signal?: AbortSignal,
): Promise<AdjacentSocsResponse> {
  if (!soc) {
    return { same_category: [], cross_category: [] }
  }
 
  const body: Record<string, unknown> = { soc, top_n }
  if (skills && skills.length > 0) {
    body.skills = skills
  }
 
  const res = await fetch(`${getBaseUrl()}/adjacent-socs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
 
  if (!res.ok) {
    console.warn('[socApi] adjacent-socs returned', res.status)
    return { same_category: [], cross_category: [] }
  }
 
  return res.json()
}
 
/**
 * Get detailed information about a specific SOC code.
 * Calls GET /soc/{code}
 */
export async function getSocDetailsApi(
  soc: string,
  signal?: AbortSignal,
): Promise<SocDetails | null> {
  if (!soc) return null
 
  const res = await fetch(`${getBaseUrl()}/soc/${encodeURIComponent(soc)}`, {
    signal,
  })
 
  if (!res.ok) {
    console.warn('[socApi] soc details returned', res.status)
    return null
  }
 
  return res.json()
}