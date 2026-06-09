import pytest
from uuid import uuid4
from app.core.eval_engine.models import EvaluationContext, TestCase
from app.core.kernel.models import RuntimeState, RuntimeEvent, FileProcessedPayload
from app.core.eval_engine.extractors.runtime_state_extractor import RuntimeStateExtractorService

def test_extract_input_artifacts_ocr_from_events():
    # Setup test data with file processed OCR events
    event1 = RuntimeEvent(
        runtime_id=uuid4(),
        payload=FileProcessedPayload(
            file_name="doc1.pdf",
            processor="ocr",
            content="Extracted OCR Text Page 1",
            latency_ms=100
        )
    )
    event2 = RuntimeEvent(
        runtime_id=uuid4(),
        payload=FileProcessedPayload(
            file_name="doc2.pdf",
            processor="ocr",
            content="Extracted OCR Text Page 2",
            latency_ms=200
        )
    )
    
    state = RuntimeState(events=[event1, event2])
    context = EvaluationContext(
        test_case=TestCase(id=None, inputs={}, expected_outputs={}, metadata={}),
        runtime_states=[state]
    )
    
    extracted = RuntimeStateExtractorService.extract_variable("input_artifacts_ocr", context)
    assert extracted == "Extracted OCR Text Page 1\nExtracted OCR Text Page 2"

def test_extract_input_artifacts_ocr_fallback_metadata():
    # Setup test data with metadata fallback
    state = RuntimeState(
        events=[],
        metadata={"input_artifacts_ocr": "Metadata Fallback OCR Text"}
    )
    context = EvaluationContext(
        test_case=TestCase(id=None, inputs={}, expected_outputs={}, metadata={}),
        runtime_states=[state]
    )
    
    extracted = RuntimeStateExtractorService.extract_variable("input_artifacts_ocr", context)
    assert extracted == "Metadata Fallback OCR Text"
