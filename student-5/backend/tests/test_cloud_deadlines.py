import pytest

from app import create_app


@pytest.mark.parametrize("slow,model,rag", [("false", 120, 30), ("true", 180, 200)])
def test_cloud_deadlines_are_opt_in_and_do_not_enable_features(monkeypatch, slow, model, rag):
    monkeypatch.setenv("CLOUD_AI_SLOW_MODE", slow)
    app = create_app({"AI_ENABLED": False, "RAG_ENABLED": False})
    assert app.config["OLLAMA_CLIENT"].timeout == model
    assert app.config["RAG_CLIENT"].timeout == rag
    assert app.config["AI_ENABLED"] is False and app.config["RAG_ENABLED"] is False
