"""Provider-neutral LLM adapters.

Implement one OpenAI-compatible client for OpenRouter and Ollama base URLs. Bedrock, if
selected, belongs behind the same application-facing protocol. Capture model, latency,
token use, estimated cost, prompt version, schema failures, and fallback events.
"""
