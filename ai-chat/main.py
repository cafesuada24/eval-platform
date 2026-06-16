"""Streamlit frontend and pipeline demo for Multi-Modal RAG."""

import contextlib
import os
import tempfile

import streamlit as st
from dotenv import load_dotenv
from evalplatform_sdk.client import EvalClient
from evalplatform_sdk.helpers import trace
from parser import ingest_file
from rag_engine import generate_answer
from vector_store import collection

load_dotenv()


# Initialize Telemetry
@st.cache_resource
def init_telemetry() -> EvalClient:
    """Initializes and returns the evaluation platform client."""
    return EvalClient(
        api_key=os.environ.get('EVAL_API_KEY', 'dummy_key'),
        base_url=os.environ.get('EVAL_BASE_URL', 'http://localhost:8000'),
    )


eval_client = init_telemetry()

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
            file_tracker.file_info(
                file_name=uploaded_file.name,
                processor='file_reader',
            )
            # Save uploaded file to a temporary location
            ext = '.' + uploaded_file.name.split('.')[-1]
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=ext,
            ) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            try:
                # Ingest and embed
                chunks_count = ingest_file(tmp_path)
                st.success(
                    f'Successfully ingested {chunks_count} chunks from {uploaded_file.name}',
                )
            except Exception as e:
                st.error(f'Error processing file: {e}')
            finally:
                os.unlink(tmp_path)

# Create Tabs for Chat and Evaluation
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
                                file_tracker.file_info(
                                    file_name=filename, processor='file_reader',
                                )
                                chunks_count = ingest_file(tmp_path)
                                file_tracker.content(f"Ingested {chunks_count} chunks.")

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
