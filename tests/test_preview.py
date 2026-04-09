"""Tests for the preview server — exercise the Verovio render payload."""

from __future__ import annotations

from pathlib import Path

import base64

from debussy import preview


class TestRenderPayload:
    def test_twinkle_payload_has_pages_and_midi(self, twinkle: str) -> None:
        payload = preview._render_payload(Path(twinkle))
        assert "pages" in payload
        assert "midi" in payload
        assert len(payload["pages"]) >= 1
        assert payload["pages"][0].lstrip().startswith("<svg") or "<svg " in payload["pages"][0][:500]
        # MIDI should decode cleanly and start with MThd
        decoded = base64.b64decode(payload["midi"])
        assert decoded.startswith(b"MThd")

    def test_autumn_leaves_multi_instrument_svg(self, autumn: str) -> None:
        payload = preview._render_payload(Path(autumn))
        svg = payload["pages"][0]
        # Three parts → Verovio should draw at least 3 staves
        # Verovio labels <g class="staff" ...> for each staff line
        assert svg.count("class=\"staff\"") >= 3

    def test_barbershop_four_part_svg(self, barbershop: str) -> None:
        payload = preview._render_payload(Path(barbershop))
        svg = payload["pages"][0]
        assert svg.count("class=\"staff\"") >= 4
