// Extração pelo navegador interno do app Claude, para quando api.hotscool.com estiver bloqueada no ambiente em nuvem.
// 1) Abrir https://api.hotscool.com/v1/api-docs/ no navegador interno (mesma origem; o fetch passa).
// 2) Trocar CHAVE_API pela chave de chave_api_es.txt e ROSTER pela lista de e-mails do config.json (campo roster).
// 3) Rodar este código pela ferramenta de JavaScript da página. O resultado (JSON) é o dump: gravar em history/dump_es_AAAA-MM-DD.json.
// Mesmo critério de coorte e mesmos campos do extract.py. Nunca gravar a chave no dump nem no HTML.
const KEY = 'CHAVE_API';
const ROSTER = new Set(['e-mail-1@dealer.com', 'e-mail-2@dealer.com']);
const TRILHAS = new Set([1298, 622]);
const CARGOS = new Set(['especialistas lean', 'lidenrança lean', 'liderança lean']);

const H = {'x-access-token': KEY}, B = 'https://api.hotscool.com/v1/';
const g = async u => { const r = await fetch(B + u, {headers: H}); if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); };
const all = async pfx => { let out = [], p = 0; for (;;) { const d = await g(pfx + p); if (!Array.isArray(d) || !d.length) break; out = out.concat(d); if (d.length < 25) break; p++; } return out; };
const arr = x => Array.isArray(x) ? x : (x && typeof x === 'object' ? Object.values(x) : []);

const [courses, students] = await Promise.all([all('courses/all/'), all('students/3/all/')]);
const courseIds = courses.map(c => c.id);
const cohort = students.filter(s => ROSTER.has((s.email || '').toLowerCase())
  || arr(s.trilhas).some(t => TRILHAS.has(t.id_trilha))
  || CARGOS.has(((s.categorizacao || {}).nome_cargo || '').trim().toLowerCase()));

const rows = [];
for (let i = 0; i < cohort.length; i += 6) {
  await Promise.all(cohort.slice(i, i + 6).map(async s => {
    const cat = s.categorizacao || {}; const c = {}, cert = {};
    await Promise.all(courseIds.map(async cid => {
      try {
        const rc = ((await g(`students/${s.id}/report/course/${cid}`)) || {}).relatorio_curso || {};
        const pv = parseInt(rc.percentual_visto) || 0, done = !!rc.curso_concluido;
        if (pv || done) { c[cid] = done ? 100 : pv; if (done && rc.certificado && rc.certificado[0]) cert[cid] = (rc.certificado[0].data || '').slice(0, 10); }
      } catch (e) {}
    }));
    rows.push({id: s.id, code: s.codigo_externo || '', n: (s.nome || '').trim(), em: (s.email || '').toLowerCase(),
      cad: (s.data_cadastro || '').slice(0, 10), l: (s.ultimo_login || '').slice(0, 10),
      u: (cat.nome_unidade || '').trim(), r: (cat.nome_cargo || '').trim(),
      t: arr(s.trilhas).map(t => t.id_trilha), enr: arr(s.cursos_matriculados).map(x => x.id_curso), c, cert});
  }));
}
const dump = {ts: new Date().toISOString().slice(0, 19) + 'Z', escola: 'Lean Dealers Academy - Espanhol', idioma: 'es',
  courses: courses.map(c => [c.id, c.nome.trim(), (c.categoria || '').trim()]), rows};
window.__dump = dump;
// soma de controle para conferir a transferência: linhas, soma dos percentuais, nº de certificados
({rows: rows.length, sumPct: rows.reduce((a, r) => a + Object.values(r.c).reduce((x, y) => x + y, 0), 0), nCert: rows.reduce((a, r) => a + Object.keys(r.cert).length, 0)});
// depois: JSON.stringify(window.__dump)
