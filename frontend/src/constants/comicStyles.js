/**
 * Canonical Photo-to-Comic style registry — 2026-05-16 P0
 *
 * Single source of truth for comic styles. The page imports `COMIC_STYLES`
 * for the grid rendering AND `normalizeComicStyle()` to defensively coerce
 * any value (string | object | nullish) into the canonical API string the
 * backend expects.
 *
 * The previous bug: an upstream caller occasionally passed a raw style
 * OBJECT into `formData.append('style', s)`, which serialized to the
 * literal string "[object Object]" — the backend then rejected it with
 * "Invalid style '[object Object]'".
 */

export const COMIC_STYLES = [
  { id: 'bold_superhero',  apiValue: 'bold_superhero',  label: 'Bold Hero',   color: 'from-red-600 to-orange-500',     tier: 'free' },
  { id: 'cartoon_fun',     apiValue: 'cartoon_fun',     label: 'Cartoon',     color: 'from-yellow-500 to-amber-400',   tier: 'free' },
  { id: 'retro_action',    apiValue: 'retro_action',    label: 'Retro Pop',   color: 'from-pink-500 to-rose-400',      tier: 'free' },
  { id: 'soft_manga',      apiValue: 'soft_manga',      label: 'Manga',       color: 'from-indigo-500 to-violet-400',  tier: 'free' },
  { id: 'cute_chibi',      apiValue: 'cute_chibi',      label: 'Chibi',       color: 'from-emerald-500 to-teal-400',   tier: 'free' },
  { id: 'kids_storybook',  apiValue: 'kids_storybook',  label: 'Storybook',   color: 'from-sky-500 to-cyan-400',       tier: 'free' },
  { id: 'noir_comic',      apiValue: 'noir_comic',      label: 'Noir',        color: 'from-slate-600 to-zinc-500',     tier: 'free' },
  { id: 'scifi_neon',      apiValue: 'scifi_neon',      label: 'Sci-Fi Neon', color: 'from-fuchsia-600 to-purple-500', tier: 'paid' },
  { id: 'cyberpunk_comic', apiValue: 'cyberpunk_comic', label: 'Cyberpunk',   color: 'from-cyan-500 to-blue-600',      tier: 'paid' },
  { id: 'magical_fantasy', apiValue: 'magical_fantasy', label: 'Fantasy',     color: 'from-violet-600 to-indigo-500',  tier: 'paid' },
  { id: 'dreamy_pastel',   apiValue: 'dreamy_pastel',   label: 'Pastel',      color: 'from-rose-400 to-pink-300',      tier: 'paid' },
  { id: 'black_white_ink', apiValue: 'black_white_ink', label: 'Ink Art',     color: 'from-gray-700 to-gray-500',      tier: 'paid' },
];

const VALID_KEYS = new Set(COMIC_STYLES.map((s) => s.apiValue));

/**
 * Coerce any input to the canonical API string the backend expects.
 * Accepts:
 *   - string: "soft_manga"           → "soft_manga"
 *   - object: { id: "soft_manga" }   → "soft_manga"
 *   - object: { apiValue: "soft_manga" } → "soft_manga"
 *   - object: { key: "soft_manga" }  → "soft_manga"
 *   - object: { value: "soft_manga" }→ "soft_manga"
 *   - anything else                  → null (caller must surface an error)
 *
 * Returns null on any unsupported / unknown value so the caller can show
 * the structured "Selected comic style is not supported." toast and refuse
 * to send the request.
 */
export function normalizeComicStyle(input) {
  if (input == null) return null;
  let candidate = null;
  if (typeof input === 'string') {
    candidate = input.trim();
  } else if (typeof input === 'object') {
    candidate = input.apiValue || input.id || input.key || input.value || input.style || null;
    if (typeof candidate === 'string') candidate = candidate.trim();
  }
  if (!candidate || typeof candidate !== 'string') return null;
  return VALID_KEYS.has(candidate) ? candidate : null;
}

export function isValidComicStyle(input) {
  return normalizeComicStyle(input) !== null;
}
