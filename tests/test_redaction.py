from patchwitness.redaction import excerpt, redact


def test_redacts_common_secret_shapes() -> None:
    text = "api_key=super-secret-value token: abcdefghijklmnop ghp_abcdefghijklmnopqrstuvwxyz"
    result = redact(text)
    assert "super-secret-value" not in result
    assert "abcdefghijklmnop" not in result
    assert "ghp_" not in result


def test_excerpt_keeps_head_and_tail() -> None:
    result = excerpt("a" * 100 + "tail", limit=20)
    assert "truncated" in result
    assert result.endswith("tail")
