async function run() {
  const payload = {
    name: "BadReqTest",
    metrics: [
      {
        metric_id: "3b170ecc-6436-4da2-86e3-1f0af42c7fce",
        threshold: { fail_over: 0 }
      }
    ]
  };
  const res = await fetch("http://localhost:8000/v1/configs/pipelines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  console.log(res.status);
  const data = await res.json().catch(() => null);
  console.log(data);
}
run();
