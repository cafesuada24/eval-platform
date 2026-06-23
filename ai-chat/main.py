"""Streamlit frontend and pipeline demo for Multi-Modal RAG."""

import contextlib
import os
import tempfile
from collections import Counter
from typing import Any, Literal

import streamlit as st
from dotenv import load_dotenv
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.helpers import trace
from parser import ingest_file
from rag_engine import generate_answer
from vector_store import collection, delete_file, get_indexed_files

load_dotenv()


def _render_overview_tab(_filename: str, chunks: list[dict[str, Any]], ext: str) -> None:
    """Renders the Overview tab of the file detail panel."""
    pages = sorted({c['metadata'].get('page_number', 1) for c in chunks})
    content_types = Counter(c['metadata'].get('content_type', 'text') for c in chunks)

    st.markdown(f'**File type:** `{ext}`')
    st.markdown(f'**Total chunks:** `{len(chunks)}`')
    st.markdown(f'**Total characters:** `{sum(len(c["document"]) for c in chunks):,}`')
    st.markdown(f'**Pages spanned:** `{len(pages)}` (pages {pages[0]}–{pages[-1]})' if len(pages) > 1 else f'**Page:** `{pages[0]}`')
    st.markdown('**Content types:**')
    for ctype, count in content_types.most_common():
        st.markdown(f'- `{ctype}` × {count}')
    st.markdown('**Chunk size:** `1000` chars')
    st.markdown('**Chunk overlap:** `100` chars')


def _render_chunks_tab(chunks: list[dict[str, Any]]) -> None:
    """Renders the Chunks tab of the file detail panel, capped at first 50 chunks for performance."""
    sorted_chunks = sorted(
        chunks,
        key=lambda c: (c['metadata'].get('page_number', 0),),
    )

    max_chunks = 50
    display_chunks = sorted_chunks[:max_chunks]
    if len(sorted_chunks) > max_chunks:
        st.info(f'Showing first {max_chunks} of {len(sorted_chunks)} chunks for performance.')

    for i, chunk in enumerate(display_chunks, start=1):
        meta = chunk['metadata']
        page = meta.get('page_number', '?')
        ctype = meta.get('content_type', 'text')
        char_count = len(chunk['document'])
        preview = chunk['document'][:200]
        full = chunk['document']

        with st.expander(
            f'Chunk {i} · `{ctype}` · Page {page} · {char_count:,} chars — {preview[:60]}…',
        ):
            st.code(full, language='markdown')


def _render_raw_tab(chunks: list[dict[str, Any]]) -> None:
    """Renders the Raw Content tab of the file detail panel."""
    sorted_chunks = sorted(
        chunks,
        key=lambda c: (c['metadata'].get('page_number', 0),),
    )
    raw = '\n\n---\n\n'.join(c['document'] for c in sorted_chunks)
    st.code(raw, language='markdown')


# Initialize Telemetry
@st.cache_resource
def init_telemetry() -> EvalClient:
    """Initializes and returns the evaluation platform client."""
    return EvalClient(
        api_key=os.environ.get('EVAL_API_KEY', 'dummy_key'),
        base_url=os.environ.get('EVAL_BASE_URL', 'http://localhost:8000'),
    )


eval_client = init_telemetry()

if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None

if 'pending_delete' not in st.session_state:
    st.session_state.pending_delete = None

st.set_page_config(page_title='AI Chat with RAG', page_icon='🤖')

st.title('🤖 AI Chat with Documents')
st.write('Upload text, images, or PDFs and ask questions about them!')

# Sidebar for file upload
with st.sidebar:
    st.header('Upload Document')
    uploaded_file = st.file_uploader(
        'Choose a file',
        type=['txt', 'png', 'jpg', 'jpeg', 'webp', 'pdf'],
    )

    if uploaded_file is not None and st.button('Process & Ingest'):
        with (
            st.spinner('Processing file...'),
            trace() as state,
            state.track_file_processed() as file_tracker,
        ):
            ext = '.' + uploaded_file.name.split('.')[-1].lower()
            processor: Literal['ocr', 'file_reader'] = 'ocr' if ext in ['.png', '.jpg', '.jpeg', '.webp'] else 'file_reader'
            file_tracker.file_info(
                file_name=uploaded_file.name,
                processor=processor,
            )
            # Save uploaded file to a temporary location
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=ext,
            ) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            try:
                # Ingest and embed
                chunks_count, content = ingest_file(tmp_path)
                file_tracker.content(content)
                st.success(
                    f'Successfully ingested {chunks_count} chunks from {uploaded_file.name}',
                )
            except Exception as e:
                st.error(f'Error processing file: {e}')
            finally:
                os.unlink(tmp_path)

    # ── File Manager ──────────────────────────────────────────────
    st.divider()

    try:
        file_index = get_indexed_files()
    except Exception as e:
        st.warning(f'Could not load file index: {e}')
        file_index = {}

    file_names = sorted(file_index.keys())
    st.subheader(f'📋 Uploaded Files ({len(file_names)})')

    if not file_names:
        st.caption('No files ingested yet. Upload a document above.')
    else:
        for fname in file_names:
            chunks = file_index[fname]
            icon = '🖼' if fname.lower().split('.')[-1] in ('png', 'jpg', 'jpeg', 'webp') else '📄'

            col_name, col_view, col_del = st.columns([5, 1, 1])
            with col_name:
                st.caption(f'{icon} {fname}  ·  {len(chunks)} chunks')
            with col_view:
                if st.button('👁', key=f'view_{fname}', help='View details'):
                    st.session_state.selected_file = fname
                    st.session_state.pending_delete = None
                    st.rerun()
            with col_del:
                if st.button('🗑', key=f'del_{fname}', help='Delete file'):
                    st.session_state.pending_delete = fname
                    st.rerun()

            # Inline delete confirmation
            if st.session_state.pending_delete == fname:
                st.warning(
                    f'⚠ Delete **{fname}** and all {len(chunks)} chunks from the index?',
                )
                confirm_col, cancel_col = st.columns(2)
                with confirm_col:
                    if st.button('Confirm Delete', key=f'confirm_{fname}', type='primary'):
                        try:
                            delete_file(fname)
                            if st.session_state.selected_file == fname:
                                st.session_state.selected_file = None
                            st.session_state.pending_delete = None
                            st.rerun()
                        except Exception as e:
                            st.error(f'Delete failed: {e}')
                with cancel_col:
                    if st.button('Cancel', key=f'cancel_{fname}'):
                        st.session_state.pending_delete = None
                        st.rerun()

# Create Tabs for Chat and Evaluation
main_col: Any
detail_col: Any
if st.session_state.selected_file and st.session_state.selected_file in file_index:
    main_col, detail_col = st.columns([2, 1])
else:
    main_col = st.container()
    detail_col = None

with main_col:
    tab1, tab2 = st.tabs(['💬 Chat', '🧪 Evaluation'])

with tab1:
    # Chat Interface
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    # Accept user input
    if prompt := st.chat_input('Ask a question about your documents...'):
        # Add user message to chat history
        st.session_state.messages.append({'role': 'user', 'content': prompt})
        with st.chat_message('user'):
            st.markdown(prompt)

        # Generate response
        with st.chat_message('assistant'), st.spinner('Thinking...'):
            try:
                with trace() as state:
                    answer = generate_answer(state, prompt)
                st.markdown(answer)
                st.session_state.messages.append(
                    {'role': 'assistant', 'content': answer},
                )
            except Exception as e:
                st.error(f'Error generating answer: {e}')

with tab2:
    st.header('🧪 Pipeline Evaluation')
    st.write('Run evaluation batches against registered datasets and pipelines.')

    try:
        # Fetch configurations from platform SDK
        datasets = eval_client.datasets.list_datasets()
        pipelines = eval_client.pipelines.list_pipelines()
        metrics_list = eval_client.metrics.list_metrics()

        metric_names = {str(m['id']): m['name'] for m in metrics_list}
    except Exception as e:
        st.error(f'Error connecting to evaluation backend: {e}')
        datasets = []
        pipelines = []
        metric_names = {}

    dataset_options = {d['name']: d['id'] for d in datasets}
    pipeline_options = {p['name']: p['id'] for p in pipelines}

    col1, col2 = st.columns(2)
    with col1:
        selected_dataset_name = st.selectbox(
            'Select Dataset',
            options=list(dataset_options.keys()),
            disabled=not dataset_options,
        )
    with col2:
        selected_pipeline_name = st.selectbox(
            'Select Pipeline',
            options=list(pipeline_options.keys()),
            disabled=not pipeline_options,
        )

    run_clicked = st.button(
        '▶️ Run Evaluation',
        disabled=not dataset_options or not pipeline_options,
    )

    if run_clicked:
        dataset_id = dataset_options[selected_dataset_name]
        pipeline_id = pipeline_options[selected_pipeline_name]

        with st.status('Running evaluation job...', expanded=True) as status_box:
            st.write('Fetching cases...')
            cases = eval_client.datasets.get_cases(dataset_id)
            st.write(f'Found {len(cases)} test cases.')

            st.write('Starting evaluation job on platform...')
            evaluation = eval_client.pipelines.start_evaluation(
                pipeline_id=pipeline_id,
                dataset_id=dataset_id,
            )

            progress_bar = st.progress(0.0)

            for idx, case in enumerate(cases):
                case_id = case['id']
                inputs = case.get('inputs', {})
                query = inputs.get('query', '')
                file_id = inputs.get('image_id')
                filename = file_id or 'text_only_query'

                st.write(f'**Case {idx + 1}/{len(cases)} (ID: `{case_id}`):** {query}')

                # Start tracking context for this specific testcase row
                with evaluation.track_case(case_id) as case_tracker, trace() as state:
                    # Check if this case includes an image file that needs OCR
                    if file_id:
                        st.write(
                            f'  └─ Downloading and processing file: `{file_id}`',
                        )
                        tmp_dir = tempfile.mkdtemp()
                        tmp_path = os.path.join(tmp_dir, filename)

                        try:
                            # Fetch the file from the platform
                            eval_client.datasets.download_file_to_disk(
                                dataset_id, file_id, tmp_path,
                            )

                            # Trace File processing
                            with state.track_file_processed() as file_tracker:
                                ext = '.' + filename.split('.')[-1].lower()
                                processor = 'ocr' if ext in ['.png', '.jpg', '.jpeg', '.webp'] else 'file_reader'
                                file_tracker.file_info(
                                    file_name=filename, processor=processor,
                                )
                                chunks_count, content = ingest_file(tmp_path)
                                file_tracker.content(content)

                            st.write(
                                f'  └─ Indexed {chunks_count} chunks into vector DB.',
                            )

                        except Exception as e:
                            st.error(f'  └─ [ERROR] File process failed: {e}')
                        finally:
                            if os.path.exists(tmp_path):
                                os.unlink(tmp_path)
                            with contextlib.suppress(Exception):
                                os.rmdir(tmp_dir)

                    # Generate Response — forced retrieval ensures eval traces match historical behaviour
                    answer = generate_answer(state, query, force_retrieve=True)
                    st.write(f'  └─ Q: {query}')
                    st.write(f'  └─ A: {answer.strip()}')

                    # Cleanup Case-specific vector data to prevent bleeding context
                    if file_id:
                        collection.delete(where={'source_file': filename})
                        st.write(
                            '  └─ Cleaned up case vector context from ChromaDB.',
                        )

                progress_bar.progress((idx + 1) / len(cases))

            st.write('Finalizing evaluation job...')
            evaluation.complete(block=True)
            status_box.update(
                label='Evaluation completed successfully!', state='complete',
            )

            # Fetch summary
            st.subheader('📊 Evaluation Summary')
            try:
                summary = evaluation.get_summary()
                if 'metrics' in summary and summary['metrics']:
                    for metric in summary['metrics']:
                        metric_id_str = str(metric.get('metric_id', ''))
                        m_name = metric_names.get(metric_id_str, metric_id_str)
                        avg_score = metric.get('average_score', 0.0)
                        pass_count = metric.get('pass_count', 0)
                        fail_count = metric.get('fail_count', 0)
                        warning_count = metric.get('warning_count', 0)
                        total_runs = metric.get('total_runs', 0)
                        pass_rate = metric.get('pass_rate', 0.0)

                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            st.metric(
                                label=f'Metric: {m_name}', value=f'{avg_score:.2f}',
                            )
                        with col_m2:
                            st.metric(label='Pass Rate', value=f'{pass_rate:.1f}%')
                        with col_m3:
                            st.markdown(
                                f'**Passed:** `{pass_count}` | **Warning:** `{warning_count}` | **Failed:** `{fail_count}` (Total: `{total_runs}`)',
                            )
                else:
                    st.info('No metrics summary returned from evaluation job.')
            except Exception as ex:
                st.error(f'Failed to load evaluation summary: {ex}')


if detail_col is not None:
    selected = st.session_state.selected_file
    chunks = file_index.get(selected, [])

    with detail_col:
        # Close button at the very top for high accessibility/responsiveness
        close_col, _ = st.columns([1, 4])
        with close_col:
            if st.button('✕ Close', key='detail_close'):
                st.session_state.selected_file = None
                st.rerun()

        # Header
        ext = selected.rsplit('.', 1)[-1].upper() if '.' in selected else 'FILE'
        icon = '🖼' if ext.lower() in ('png', 'jpg', 'jpeg', 'webp') else '📄'
        total_chars = sum(len(c['document']) for c in chunks)

        st.markdown(f'### {icon} {selected}')
        st.caption(f'{ext} · {len(chunks)} chunks · {total_chars:,} chars')

        # Tabs
        ov_tab, ch_tab, raw_tab = st.tabs([
            'Overview',
            f'Chunks ({min(len(chunks), 50)})',
            'Raw Content',
        ])

        with ov_tab:
            _render_overview_tab(selected, chunks, ext)

        with ch_tab:
            _render_chunks_tab(chunks)

        with raw_tab:
            _render_raw_tab(chunks)

