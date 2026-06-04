const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { messages, message, data, metric_id: providedMetricId, metric_name: providedMetricName } = body;
    
    let metric_id = providedMetricId;
    let metric_name = providedMetricName;
    let yamlConfigStr = undefined;

    if (data && data.current_yaml_config) {
      yamlConfigStr = data.current_yaml_config;
    } else if (messages && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.data && lastMessage.data.current_yaml_config) {
        yamlConfigStr = lastMessage.data.current_yaml_config;
      }
    }

    if (!metric_name && yamlConfigStr) {
       try {
         const yamlConfig = JSON.parse(yamlConfigStr);
         metric_name = yamlConfig.name;
       } catch(e) {}
    }
    
    // Sanitize messages for backend: keep only 'role' and 'content'
    const sanitizedMessages = (messages || []).map((msg: any) => ({
      role: msg.role,
      content: msg.content
    }));

    const response = await fetch(`${API_BASE_URL}/v1/agent/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages: sanitizedMessages, metric_id }),
    });

    if (!response.ok) {
      return new Response(await response.text(), {
        status: response.status,
      });
    }

    const result = await response.json();
    return Response.json(result);
  } catch (error) {
    console.error('Agent chat proxy error:', error);
    return new Response('Internal Server Error', { status: 500 });
  }
}
