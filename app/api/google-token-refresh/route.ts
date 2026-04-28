import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const { refresh_token } = await req.json()

  if (!refresh_token) {
    return NextResponse.json({ error: 'Missing refresh_token' }, { status: 400 })
  }

  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: process.env.GOOGLE_CLIENT_ID ?? '',
      client_secret: process.env.GOOGLE_CLIENT_SECRET ?? '',
      refresh_token,
      grant_type: 'refresh_token'
    })
  })

  const data = await response.json()

  if (!response.ok) {
    return NextResponse.json({ error: data }, { status: response.status })
  }

  return NextResponse.json({ access_token: data.access_token, expires_in: data.expires_in })
}
