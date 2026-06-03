/**
 * test_endpoints.js  —  Test the new O*NET/SOC endpoints
 *
 * Run with:
 *   node test_endpoints.js
 * or change BASE_URL to point to a different host/port.
 *
 * Requires Node.js 18+ (native fetch) or install the `node-fetch` polyfill.
 */

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

async function request(method, path, body) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${BASE_URL}${path}`, opts);
  const data = await res.json();
  return { status: res.status, data };
}

function heading(n, title) {
  const bar = '='.repeat(46);
  console.log(`\n${bar}`);
  console.log(` ${n}. ${title}`);
  console.log(bar);
}

async function main() {
  // --- 1. Predict SOC (basic) ---
  heading(1, 'POST /predict-soc  — basic prediction');
  const r1 = await request('POST', '/predict-soc', {
    skills: ['Python', 'SQL', 'Machine Learning', 'Project Management'],
    top_n: 3,
  });
  console.log(JSON.stringify(r1.data, null, 2));

  // --- 2. Predict SOC (custom alpha, include all) ---
  heading(2, 'POST /predict-soc  — custom alpha + include_all');
  const r2 = await request('POST', '/predict-soc', {
    skills: ['Python', 'Java', 'C++'],
    top_n: 5,
    alpha: 0.8,
    include_all: true,
  });
  console.log(JSON.stringify(r2.data, null, 2));

  // --- 3. Predict SOC (unknown skills) ---
  heading(3, 'POST /predict-soc  — unknown skills only');
  const r3 = await request('POST', '/predict-soc', {
    skills: ['Frobnication', 'Widget Smithing'],
    top_n: 3,
  });
  console.log(JSON.stringify(r3.data, null, 2));

  // --- 4. Adjacent SOCs (same category only) ---
  heading(4, 'POST /adjacent-socs  — find adjacent SOCs');
  const r4 = await request('POST', '/adjacent-socs', {
    soc: '15-1132.00',
    top_n: 5,
  });
  console.log(JSON.stringify(r4.data, null, 2));

  // --- 5. Adjacent SOCs (with user skills) ---
  heading(5, 'POST /adjacent-socs  — with user skills');
  const r5 = await request('POST', '/adjacent-socs', {
    soc: '15-1132.00',
    top_n: 3,
    skills: ['Python', 'Kubernetes', 'AWS'],
  });
  console.log(JSON.stringify(r5.data, null, 2));

  // --- 6. SOC details ---
  heading(6, 'GET /soc/{code}  — SOC details');
  const r6 = await request('GET', '/soc/15-1132.00');
  console.log(JSON.stringify(r6.data, null, 2));

  // --- 7. SOC details (another SOC) ---
  heading(7, 'GET /soc/{code}  — another SOC');
  const r7 = await request('GET', '/soc/11-1011.00');
  console.log(JSON.stringify(r7.data, null, 2));

  console.log('\n' + '='.repeat(46));
  console.log(' Done.');
  console.log('='.repeat(46) + '\n');
}

main().catch((err) => {
  console.error('Test failed:', err);
  process.exit(1);
});
