/**
 * Comic Styles — frontend wire to the backend canonical catalog
 * ===============================================================
 *
 * P0 2026-05-18 — single source of truth.
 *
 * The backend `SAFE_STYLES` dict in `routes/photo_to_comic.py` is now
 * THE authoritative catalog. This module:
 *
 *   • Fetches the catalog from `GET /api/photo-to-comic/styles-catalog`
 *     filtered by mode (avatar / strip).
 *   • Caches in memory per mount.
 *   • Falls back to a HARDCODED MIRROR of the catalog if the network is
 *     down — this is intentionally a SUBSET of SAFE_STYLES (only the
 *     entries with `enabled: True`). Any drift between this mirror and
 *     the backend is caught by the regression tests.
 *
 * The exported `normalizeComicStyle()` keeps its old contract: pass a
 * raw user/UI value, get back the canonical key (or null if invalid).
 */
import api from '../utils/api';

// ────────────────────────────────────────────────────────────────────────
// Hardcoded mirror — used ONLY when the backend catalog fetch fails.
// MUST stay in lockstep with the `enabled: True` entries of
// `routes/photo_to_comic.py :: SAFE_STYLES`. Tests enforce this.
// ────────────────────────────────────────────────────────────────────────
export const COMIC_STYLES = Object.freeze([
  { key: 'bold_superhero', label: 'Bold Hero',     description: 'Action & courage',        preview_color: 'from-red-600 to-orange-500',     modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'cartoon_fun',    label: 'Cartoon',       description: 'Bright & playful',        preview_color: 'from-yellow-500 to-amber-400',   modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'retro_action',   label: 'Retro Pop',     description: 'Vibrant & dynamic',       preview_color: 'from-pink-500 to-rose-400',      modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'soft_manga',     label: 'Manga',         description: 'Gentle & expressive',     preview_color: 'from-indigo-500 to-violet-400',  modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'cute_chibi',     label: 'Chibi',         description: 'Adorable & mini',         preview_color: 'from-emerald-500 to-teal-400',   modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'kids_storybook', label: 'Storybook',     description: 'Friendly & wholesome',    preview_color: 'from-sky-500 to-cyan-400',       modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'noir_comic',     label: 'Noir',          description: 'Dramatic & shadowed',     preview_color: 'from-slate-600 to-zinc-500',     modes: ['avatar', 'strip'], tier: 'free' },
  { key: 'scifi_neon',     label: 'Sci-Fi Neon',   description: 'Futuristic & vibrant',    preview_color: 'from-fuchsia-600 to-purple-500', modes: ['avatar', 'strip'], tier: 'paid' },
  { key: 'cyberpunk_comic',label: 'Cyberpunk',     description: 'High-tech dystopia',      preview_color: 'from-cyan-500 to-blue-600',      modes: ['avatar', 'strip'], tier: 'paid' },
  { key: 'magical_fantasy',label: 'Fantasy',       description: 'Enchanted & mystical',    preview_color: 'from-violet-600 to-indigo-500',  modes: ['avatar', 'strip'], tier: 'paid' },
  { key: 'dreamy_pastel',  label: 'Pastel',        description: 'Soft & dreamy',           preview_color: 'from-rose-400 to-pink-300',      modes: ['avatar', 'strip'], tier: 'paid' },
  { key: 'black_white_ink',label: 'Ink Art',       description: 'Bold & contrasted',       preview_color: 'from-gray-700 to-gray-500',      modes: ['avatar', 'strip'], tier: 'paid' },
]);

// Map of canonical keys → label, used by normalizeComicStyle below.
const STYLE_KEYS = new Set(COMIC_STYLES.map(s => s.key));
const STYLE_KEY_BY_LABEL = new Map(
  COMIC_STYLES.map(s => [s.label.toLowerCase(), s.key])
);

/**
 * Normalize any user/UI input to a canonical style key.
 *
 * Accepts:
 *   • exact canonical key  ('cartoon_fun')
 *   • case-insensitive label ('Cartoon', 'CARTOON')
 *   • already-normalized object { key } from older code paths
 *
 * Returns the canonical string key, or `null` if it cannot be normalized.
 * `null` MUST be treated as a UI bug — the grid should never let the user
 * pick something that doesn't normalize.
 */
export function normalizeComicStyle(input) {
  if (input == null) return null;
  if (typeof input === 'string') {
    const t = input.trim();
    if (!t) return null;
    if (STYLE_KEYS.has(t)) return t;
    const byLabel = STYLE_KEY_BY_LABEL.get(t.toLowerCase());
    return byLabel || null;
  }
  // P0 2026-05-19 — CASE B production hotfix. The previous object branch
  // ONLY looked at `input.key`. Production was holding tile objects
  // shaped `{ id, name, color, tier }` (no `key` field), which silently
  // rejected and produced the toast "frontend rejected style=object".
  // We now extract from the canonical id field-name set (key / id /
  // value / slug / apiValue / style) AND retry the case-insensitive
  // label map against `name` / `label` so even legacy tile objects
  // coerce cleanly.
  if (typeof input === 'object') {
    const idCandidates = ['key', 'id', 'value', 'slug', 'apiValue', 'style'];
    for (const f of idCandidates) {
      const v = input[f];
      if (typeof v === 'string' && v.trim()) {
        const t = v.trim();
        if (STYLE_KEYS.has(t)) {
          // eslint-disable-next-line no-console
          console.info('[p2c/style-normalize] OBJECT_FALLBACK received=object', { extracted_from: f, key: t });
          return t;
        }
        // Try label coercion (catches `{id: 'Cartoon'}` shaped objects).
        const byLabel = STYLE_KEY_BY_LABEL.get(t.toLowerCase());
        if (byLabel) {
          // eslint-disable-next-line no-console
          console.info('[p2c/style-normalize] OBJECT_FALLBACK received=object', { extracted_from: f, label: t, key: byLabel });
          return byLabel;
        }
      }
    }
    // Last-ditch: try `name` / `label` against the label map.
    for (const f of ['name', 'label']) {
      const v = input[f];
      if (typeof v === 'string') {
        const byLabel = STYLE_KEY_BY_LABEL.get(v.trim().toLowerCase());
        if (byLabel) {
          // eslint-disable-next-line no-console
          console.info('[p2c/style-normalize] OBJECT_FALLBACK received=object', { extracted_from: f, label: v, key: byLabel });
          return byLabel;
        }
      }
    }
    // eslint-disable-next-line no-console
    console.warn('[p2c/style-normalize] OBJECT_REJECTED no id/label match', { keys: Object.keys(input).slice(0, 10) });
    return null;
  }
  return null;
}

export function isValidComicStyle(input) {
  return normalizeComicStyle(input) !== null;
}

// ────────────────────────────────────────────────────────────────────────
// Backend-backed catalog fetch (P0 2026-05-18)
// ────────────────────────────────────────────────────────────────────────

const _modeCache = new Map(); // mode → { ts, styles }
const CACHE_TTL_MS = 60_000;

/**
 * Fetch the canonical comic-style catalog from the backend filtered by
 * mode. Returns an Array of `{ key, label, name, modes, tier,
 * preview_color, provider_style }`. On network failure, returns the
 * hardcoded mirror filtered by mode.
 *
 * @param {('avatar'|'strip')} mode
 * @returns {Promise<Array>} catalog entries valid for `mode`
 */
export async function fetchComicStylesCatalog(mode) {
  if (mode !== 'avatar' && mode !== 'strip') {
    throw new Error(`fetchComicStylesCatalog: invalid mode '${mode}'`);
  }
  const cached = _modeCache.get(mode);
  if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
    return cached.styles;
  }
  try {
    const r = await api.get(
      `/api/photo-to-comic/styles-catalog?mode=${encodeURIComponent(mode)}`
    );
    const styles = Array.isArray(r?.data?.styles) ? r.data.styles : null;
    if (!styles || styles.length === 0) throw new Error('empty catalog');
    _modeCache.set(mode, { ts: Date.now(), styles });
    return styles;
  } catch (_) {
    // Fallback: filter the hardcoded mirror by mode. This guarantees the
    // grid always renders SOMETHING, and every entry is in the
    // hardcoded mirror — which the regression tests prove is a strict
    // subset of the backend's `enabled: True` entries.
    const fallback = COMIC_STYLES.filter(s => s.modes.includes(mode));
    return fallback.map(s => ({
      key: s.key,
      label: s.label,
      name: s.label,
      modes: s.modes,
      tier: s.tier,
      preview_color: s.preview_color,
      provider_style: s.key,
      enabled: true,
    }));
  }
}

/** Synchronous accessor for the hardcoded mirror filtered by mode. Used
 *  by tests and any UI that needs an instant render before the fetch
 *  completes. */
export function comicStylesMirrorForMode(mode) {
  return COMIC_STYLES.filter(s => s.modes.includes(mode));
}
