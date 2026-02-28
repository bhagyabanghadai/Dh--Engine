from __future__ import annotations

from dhi.interceptor.extractor import extract_candidate, validate_python_code


def test_validate_python_code_valid() -> None:
    code = "def foo():\n    return 42"
    assert validate_python_code(code) is None


def test_validate_python_code_invalid() -> None:
    code = "def foo(:\n    return 42"
    error = validate_python_code(code)
    assert error is not None
    assert "SyntaxError" in error


def test_validate_python_code_empty() -> None:
    assert validate_python_code("") is not None
    assert validate_python_code("   \n") is not None


def test_extract_candidate_valid_json() -> None:
    response = """
    {
        "language": "python",
        "code": "print('hello')",
        "notes": "Simple print"
    }
    """
    result = extract_candidate(response)
    assert result.success is True
    assert result.code == "print('hello')"
    assert result.language == "python"
    assert result.notes == "Simple print"
    assert result.fallback_used is False


def test_extract_candidate_json_wrapped_in_markdown() -> None:
    response = """```json
    {
        "language": "python",
        "code": "print('hello')",
        "notes": "Simple print"
    }
    ```"""
    result = extract_candidate(response)
    assert result.success is True
    assert result.code == "print('hello')"
    assert result.fallback_used is False


def test_extract_candidate_fallback_markdown() -> None:
    response = """
    Sure, here is the code:
    ```python
    print('hello world')
    ```
    This should work.
    """
    result = extract_candidate(response)
    assert result.success is True
    assert result.code == "print('hello world')"
    assert result.fallback_used is True
    assert result.language == "python"


def test_extract_candidate_fallback_invalid_syntax() -> None:
    response = """
    Here you go:
    ```python
    def my_func(
    ```
    """
    result = extract_candidate(response)
    assert result.success is False
    assert result.fallback_used is True
    assert result.error is not None
    assert "SyntaxError" in result.error


def test_extract_candidate_total_failure() -> None:
    response = "I cannot write code right now, sorry."
    result = extract_candidate(response)
    assert result.success is False
    assert result.fallback_used is True
    assert result.error is not None
    assert "Could not extract" in result.error


def test_extract_candidate_structured_invalid_python_fails() -> None:
    response = """
    {
        "language": "python",
        "code": "def broken(:",
        "notes": "bad"
    }
    """
    result = extract_candidate(response)
    assert result.success is False
    assert result.fallback_used is False
    assert result.error is not None
    assert "SyntaxError" in result.error