// Ad-hoc Supabase query runner for debugging.
//
// Usage:
//   node scripts/query.mjs              # uses anon key (what the frontend uses)
//   node scripts/query.mjs --service    # uses service key (bypasses RLS)
//
// Edit the query at the bottom and re-run. Reads credentials from frontend/.env.
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { createClient } from '@supabase/supabase-js'

const __dirname = dirname(fileURLToPath(import.meta.url))

function loadEnv() {
  const raw = readFileSync(join(__dirname, '..', '.env'), 'utf8')
  const env = {}
  for (const line of raw.split('\n')) {
    const m = line.match(/^\s*([\w.-]+)\s*=\s*(.*)\s*$/)
    if (m && !line.trim().startsWith('#')) env[m[1]] = m[2]
  }
  return env
}

const env = loadEnv()
const useService = process.argv.includes('--service')
const url = env.SUPABASE_URL
const key = useService ? env.SUPABASE_SERVICE_KEY_DEBUG : env.SUPABASE_KEY

if (!url || !key) {
  console.error(`Missing ${useService ? 'SUPABASE_SERVICE_KEY_DEBUG' : 'SUPABASE_KEY'} or SUPABASE_URL in .env`)
  process.exit(1)
}

const sb = createClient(url, key)
console.log(`→ ${url}  (${useService ? 'service_role' : 'anon'})\n`)

// ─── edit your query here ─────────────────────────────────────────────
// Example: the exact join the /prices page runs for one product.
const { data, error } = await sb
  .from('canonical_products')
  .select('id, name, short_name')
  .ilike('name', '%milk%')
  .limit(10)
// ──────────────────────────────────────────────────────────────────────

console.log(JSON.stringify({ count: data?.length, data, error }, null, 2))
