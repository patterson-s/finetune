"""serve — export + expose the finetuned model via a local OpenAI-compatible endpoint.

Backends (providers.yaml): llama.cpp (port 8080) and Ollama (port 11434), both
serving an OpenAI-compatible /v1 API. The client here talks to that endpoint so
downstream tooling (Hermes, Claude Code) can consume the model with the standard
chat-completions contract.
"""
