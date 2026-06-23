from unittest.mock import MagicMock, patch
import pytest
from google.genai import errors as genai_errors
from utils import is_retryable_exception, retry_api_call, with_retry

def test_is_retryable_exception():
    # 1. Standard Python Exceptions
    assert is_retryable_exception(ConnectionError("connection failed")) is True
    assert is_retryable_exception(TimeoutError("timeout failed")) is True
    assert is_retryable_exception(ValueError("value error")) is False

    # 2. ServerError (5xx)
    assert is_retryable_exception(genai_errors.ServerError(code=503, response_json={})) is True

    # 3. APIError specific status codes
    assert is_retryable_exception(genai_errors.APIError(code=429, response_json={})) is True
    assert is_retryable_exception(genai_errors.APIError(code=500, response_json={})) is True
    assert is_retryable_exception(genai_errors.APIError(code=502, response_json={})) is True
    assert is_retryable_exception(genai_errors.APIError(code=503, response_json={})) is True
    assert is_retryable_exception(genai_errors.APIError(code=504, response_json={})) is True

    # Non-retryable client errors
    assert is_retryable_exception(genai_errors.APIError(code=400, response_json={})) is False
    assert is_retryable_exception(genai_errors.APIError(code=404, response_json={})) is False

@patch("utils.time.sleep")
def test_retry_api_call_success(mock_sleep):
    mock_func = MagicMock()
    mock_func.side_effect = [
        genai_errors.APIError(code=429, response_json={}),
        genai_errors.ServerError(code=503, response_json={}),
        "success"
    ]
    res = retry_api_call(mock_func, max_retries=2, initial_delay=1.0, use_jitter=False)
    assert res == "success"
    assert mock_func.call_count == 3
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1.0)
    mock_sleep.assert_any_call(2.0)

@patch("utils.time.sleep")
def test_retry_api_call_non_retryable_raises(mock_sleep):
    mock_func = MagicMock()
    mock_func.side_effect = ValueError("permanent error")
    with pytest.raises(ValueError, match="permanent error"):
        retry_api_call(mock_func, max_retries=3)
    assert mock_func.call_count == 1
    assert mock_sleep.call_count == 0

@patch("utils.time.sleep")
def test_retry_api_call_exhausted(mock_sleep):
    mock_func = MagicMock()
    mock_func.side_effect = genai_errors.APIError(code=429, response_json={})
    with pytest.raises(genai_errors.APIError):
        retry_api_call(mock_func, max_retries=3, initial_delay=1.0, use_jitter=False)
    # 1 initial + 3 retries = 4 attempts total
    assert mock_func.call_count == 4
    assert mock_sleep.call_count == 3
    sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
    assert sleep_calls == [1.0, 2.0, 4.0]

@patch("utils.time.sleep")
def test_with_retry_decorator(mock_sleep):
    mock_func = MagicMock()
    mock_func.side_effect = [
        genai_errors.APIError(code=429, response_json={}),
        "decorator success"
    ]

    @with_retry(max_retries=2, initial_delay=1.0, use_jitter=False)
    def decorated_func(arg1, kwarg1=None):
        return mock_func(arg1, kwarg1=kwarg1)

    res = decorated_func("test", kwarg1="val")
    assert res == "decorator success"
    assert mock_func.call_count == 2
    mock_func.assert_called_with("test", kwarg1="val")
    assert mock_sleep.call_count == 1
    mock_sleep.assert_called_with(1.0)
