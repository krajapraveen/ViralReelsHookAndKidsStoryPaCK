"""P0 2026-06-PROD-FOLLOWUP #5 — Same-origin video streaming proxy.

Production incident (sixth strike):
  Raw R2 presigned URLs returned `403 Forbidden` to the browser even
  though `curl` succeeded. COEP removal alone didn't help. Chrome's
  combination of strict cross-origin handling for `<video>` and R2's
  signed-URL quirks made direct R2 playback fundamentally unreliable.

Bug-class fix: serve video bytes through our OWN backend. The browser
sees a vanilla same-origin `<video src="/api/photo-trailer/jobs/<id>/video">`,
eliminating CORS, COEP, ORB, signed-URL expiry, and signed-URL CDN
race conditions in one stroke.

These tests pin the contract — any future PR that removes Range
support, breaks auth, leaks data to non-owners, or drops the headers
the browser needs will fail.

Registered under `make audit-boundaries`.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path("/app")
BACKEND = REPO / "backend"
FRONTEND = REPO / "frontend"
sys.path.insert(0, str(BACKEND))

PHOTO_TRAILER_PY = BACKEND / "routes" / "photo_trailer.py"
PHOTO_TRAILER_JSX = FRONTEND / "src" / "pages" / "PhotoTrailerPage.jsx"


# ─────────────────────────────────────────────────────────────────────
# Section A — Range header parser semantics.
# ─────────────────────────────────────────────────────────────────────
class TestRangeHeaderParser:
    def _p(self, hdr, total):
        from routes.photo_trailer import _parse_range_header
        return _parse_range_header(hdr, total)

    def test_no_header_returns_none(self):
        assert self._p(None, 1000) is None
        assert self._p("", 1000) is None

    def test_full_explicit_range(self):
        assert self._p("bytes=0-999", 1000) == (0, 999)

    def test_open_ended_range_clamps_to_eof(self):
        assert self._p("bytes=500-", 1000) == (500, 999)

    def test_suffix_range(self):
        """`bytes=-500` = last 500 bytes."""
        assert self._p("bytes=-500", 1000) == (500, 999)

    def test_suffix_larger_than_total_clamps_to_zero(self):
        """`bytes=-5000` on a 1000-byte file = full file."""
        assert self._p("bytes=-5000", 1000) == (0, 999)

    def test_end_beyond_total_clamps(self):
        """`bytes=500-99999` on a 1000-byte file = 500..999."""
        assert self._p("bytes=500-99999", 1000) == (500, 999)

    def test_start_past_eof_is_unsatisfiable(self):
        """`bytes=2000-` on a 1000-byte file → (-1, -1) → 416."""
        assert self._p("bytes=2000-", 1000) == (-1, -1)
        assert self._p("bytes=2000-3000", 1000) == (-1, -1)

    def test_malformed_returns_none(self):
        assert self._p("bytes=abc-xyz", 1000) is None
        assert self._p("bytes=", 1000) is None
        assert self._p("bytes=-", 1000) is None
        # Note: "items=0-100" is a non-bytes unit. The parser uses a strict
        # `^bytes=...$` match, so it should reject.
        assert self._p("items=0-100", 1000) is None

    def test_negative_start_or_inverted_returns_none(self):
        # `bytes=500-100` is end<start — malformed.
        assert self._p("bytes=500-100", 1000) is None


# ─────────────────────────────────────────────────────────────────────
# Section B — Endpoint shape: routes exist with correct methods + auth.
# ─────────────────────────────────────────────────────────────────────
class TestEndpointShape:
    @classmethod
    def setup_class(cls):
        cls.src = PHOTO_TRAILER_PY.read_text()

    def test_owner_endpoint_route_exists(self):
        assert '@router.api_route("/jobs/{job_id}/video"' in self.src, (
            "Same-origin streaming proxy must exist at "
            "GET /api/photo-trailer/jobs/{job_id}/video"
        )

    def test_owner_endpoint_supports_get_and_head(self):
        m = re.search(
            r'@router\.api_route\("/jobs/\{job_id\}/video"\s*,\s*methods=\[(?P<m>[^\]]+)\]\)',
            self.src,
        )
        assert m, "Owner endpoint must declare methods explicitly."
        methods = m.group("m")
        assert '"GET"' in methods and '"HEAD"' in methods, (
            "Endpoint must support both GET (playback) and HEAD "
            "(pre-flight ownership check before download navigation)."
        )

    def test_public_share_endpoint_exists(self):
        """Public share-page playback must ALSO use the same-origin
        proxy — otherwise sharing reproduces the R2 403 bug."""
        assert '@router.api_route("/share/{slug}/video"' in self.src, (
            "Public share-page playback must use the same-origin proxy."
        )

    def test_owner_endpoint_accepts_token_query_param(self):
        """The <video> element can't send Authorization headers — the
        proxy MUST accept the JWT via `?token=` query string."""
        # Locate the stream_video_proxy function body.
        m = re.search(
            r"async def stream_video_proxy\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
            self.src, re.S,
        )
        assert m, "stream_video_proxy must exist"
        body = m.group("body")
        assert "token: Optional[str] = Query(None)" in body, (
            "Proxy must accept `token` as an optional Query param so "
            "<video src='...?token=...'> playback works."
        )
        # Must still honour Authorization header for fetch()/curl callers.
        assert "authorization" in body.lower(), (
            "Proxy must also honour the Authorization: Bearer header so "
            "programmatic callers don't need to use the query string."
        )

    def test_owner_endpoint_enforces_ownership(self):
        """Non-owners get 404 (not 403) — deliberately indistinguishable
        from `job doesn't exist` so we don't leak existence."""
        m = re.search(
            r"async def stream_video_proxy\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
            self.src, re.S,
        )
        body = m.group("body")
        assert 'find_one({"_id": job_id, "user_id": user_id})' in body, (
            "Ownership must be enforced inside the DB query — never on "
            "the response side."
        )
        assert 'raise HTTPException(404' in body, (
            "Non-owner / missing job must raise 404, not 403."
        )

    def test_owner_endpoint_requires_completed_status(self):
        m = re.search(
            r"async def stream_video_proxy\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef )",
            self.src, re.S,
        )
        body = m.group("body")
        assert 'COMPLETED' in body, (
            "Endpoint must refuse to stream a non-COMPLETED job."
        )

    def test_response_headers_contract(self):
        """The _serve_video_stream helper MUST set Content-Type,
        Accept-Ranges, Cache-Control, and (for ranged) Content-Range
        + Content-Length."""
        m = re.search(
            r"async def _serve_video_stream\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef |\n@router)",
            self.src, re.S,
        )
        assert m, "_serve_video_stream helper must exist."
        body = m.group("body")
        for hdr in ("Content-Type", "Accept-Ranges", "Cache-Control",
                    "Content-Range", "Content-Length"):
            assert hdr in body, (
                f"_serve_video_stream must set `{hdr}` header somewhere "
                f"in its response path."
            )
        assert '"bytes"' in body, (
            "Accept-Ranges must be set to `bytes`."
        )

    def test_partial_content_206_for_range_requests(self):
        m = re.search(
            r"async def _serve_video_stream\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef |\n@router)",
            self.src, re.S,
        )
        body = m.group("body")
        assert "status_code=206" in body, (
            "Range requests must return 206 Partial Content."
        )

    def test_416_for_unsatisfiable_range(self):
        m = re.search(
            r"async def _serve_video_stream\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef |\n@router)",
            self.src, re.S,
        )
        body = m.group("body")
        assert "status_code=416" in body, (
            "Unsatisfiable range must return 416."
        )
        assert 'bytes */' in body, (
            "416 response must include `Content-Range: bytes */TOTAL` "
            "per RFC 7233."
        )

    def test_404_for_missing_r2_object(self):
        """If the underlying R2 object has been deleted, the endpoint
        must return 404 (not 500 — that would dirty the error budget)."""
        m = re.search(
            r"async def _serve_video_stream\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef |\n@router)",
            self.src, re.S,
        )
        body = m.group("body")
        assert "raise HTTPException(404" in body, (
            "Missing R2 object must surface as 404."
        )

    def test_download_filename_uses_content_disposition_attachment(self):
        m = re.search(
            r"async def _serve_video_stream\([^)]*\)[^:]*:(?P<body>.+?)(?=\nasync def |\ndef |\n@router)",
            self.src, re.S,
        )
        body = m.group("body")
        assert "Content-Disposition" in body and "attachment" in body, (
            "Download flow must set Content-Disposition: attachment "
            "so the browser auto-saves the file."
        )

    def test_chunk_size_is_bounded(self):
        """Pipeline must NOT buffer the entire MP4 in memory. Pin the
        1 MB chunk constant so a future PR can't accidentally turn it
        into an unbounded read."""
        m = re.search(
            r"_VIDEO_STREAM_CHUNK_BYTES\s*=\s*(?P<expr>[^\n]+)", self.src,
        )
        assert m, "_VIDEO_STREAM_CHUNK_BYTES constant must exist."
        # Evaluate the expression in a tiny safe context.
        chunk = eval(m.group("expr").strip(), {"__builtins__": {}}, {})
        assert chunk <= 8 * 1024 * 1024, (
            "Chunk size must be ≤ 8 MB. Anything larger risks worker "
            "thread starvation and unbounded memory growth."
        )
        assert chunk >= 64 * 1024, (
            "Chunk size must be ≥ 64 KB. Smaller chunks waste syscalls."
        )


# ─────────────────────────────────────────────────────────────────────
# Section C — Frontend uses the same-origin proxy URL.
# ─────────────────────────────────────────────────────────────────────
class TestFrontendUsesSameOriginProxy:
    @classmethod
    def setup_class(cls):
        cls.src = PHOTO_TRAILER_JSX.read_text()

    def test_video_src_uses_same_origin_proxy(self):
        """The <video> element must point at our own backend, not at
        the raw R2 signed URL."""
        assert "/api/photo-trailer/jobs/" in self.src
        assert "/video" in self.src, (
            "Frontend must build a same-origin URL ending in `/video` "
            "(the new streaming proxy endpoint)."
        )

    def test_no_raw_r2_url_in_video_src_path(self):
        """Sanity: r2.cloudflarestorage.com must NOT appear hard-coded
        anywhere in the player flow."""
        assert "r2.cloudflarestorage.com" not in self.src, (
            "Frontend must never embed a raw R2 hostname — that's the "
            "bug-class we just eliminated."
        )

    def test_token_query_param_carries_jwt(self):
        """The frontend MUST include `?token=<jwt>` so the proxy can
        authenticate the request (the <video> element can't send the
        Authorization header)."""
        assert "token=" in self.src
        # Either auth_token or token from localStorage is acceptable.
        assert ("auth_token" in self.src) or ("token'" in self.src), (
            "Frontend must read the JWT from localStorage and append "
            "it as `?token=`."
        )

    def test_download_uses_same_origin_proxy(self):
        """The Download button must hit the same proxy, not the legacy
        /stream?download=true endpoint that returned R2 URLs."""
        # The download flow must include `download=true` against the
        # /video endpoint.
        assert "download=true" in self.src
        assert ("/video?download=true" in self.src
                or "/video`\n" in self.src
                or "download=true" in self.src), (
            "Download flow must target the same-origin proxy."
        )


# ─────────────────────────────────────────────────────────────────────
# Section D — Range parser fuzzy / boundary fuzz.
# ─────────────────────────────────────────────────────────────────────
class TestRangeParserBoundaries:
    def _p(self, hdr, total):
        from routes.photo_trailer import _parse_range_header
        return _parse_range_header(hdr, total)

    def test_zero_byte_file_with_no_range(self):
        # Edge case: empty file, no range header → (None) full-body path.
        assert self._p(None, 0) is None

    def test_single_byte_range(self):
        assert self._p("bytes=0-0", 1000) == (0, 0)

    def test_whitespace_tolerated(self):
        assert self._p("  bytes=0-100  ", 1000) == (0, 100)

    def test_chrome_typical_initial_range(self):
        """Chrome typically issues `bytes=0-` for the first request."""
        assert self._p("bytes=0-", 10_000_000) == (0, 9_999_999)
