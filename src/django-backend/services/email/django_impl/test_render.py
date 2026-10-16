from . import render_email


class TestRenderEmail:
    def test_renders_html_with_branding_colors(self):
        html, _ = render_email(
            "verification_code",
            {
                "code": "123456",
                "expiry_minutes": 15,
                "user_name": "Test",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "#ffffff" in html  # white background
        assert "Naglasúpan" in html  # brand name

    def test_renders_html_with_verification_code(self):
        html, _ = render_email(
            "verification_code",
            {
                "code": "987654",
                "expiry_minutes": 15,
                "user_name": "Test",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "987654" in html

    def test_renders_plain_text_fallback(self):
        _, text = render_email(
            "verification_code",
            {
                "code": "112233",
                "expiry_minutes": 15,
                "user_name": "Alice",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "112233" in text
        assert "Hi Alice" in text
        assert "15 minutes" in text

    def test_plain_text_is_not_html_escaped(self):
        html, text = render_email(
            "verification_code",
            {
                "code": "445566",
                "expiry_minutes": 15,
                "user_name": "O'Brien <&>",
                "logo_url": "https://example.com/logo.png",
                "current_year": 2025,
            },
        )

        assert "Hi O'Brien <&>" in text
        assert "O'Brien <&>" not in html
