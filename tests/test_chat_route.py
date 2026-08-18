def _create_tutor(client, admin_headers, **overrides):
    payload = {
        "title": "Tutor de História",
        "short_description": "Ajuda com história do Brasil",
        "system_instructions": "Seja didático.",
        "sources": [],
    }
    payload.update(overrides)
    response = client.post("/api/admin/tutors", json=payload, headers=admin_headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_routes_require_admin_key(client):
    response = client.get("/api/admin/tutors")
    assert response.status_code == 401


def test_create_tutor_and_chat_end_to_end(client, admin_headers):
    tutor = _create_tutor(client, admin_headers)

    chat_response = client.post(
        "/api/public/chat",
        json={
            "tutor_id": tutor["id"],
            "embed_token": tutor["embed_token"],
            "message": "Olá, tudo bem?",
        },
    )

    assert chat_response.status_code == 200, chat_response.text
    body = chat_response.json()
    assert body["reply"] == "Resposta de teste do tutor."
    assert body["session_id"]

    history = client.get(
        f"/api/public/chat/{body['session_id']}/history",
        params={"tutor_id": tutor["id"], "embed_token": tutor["embed_token"]},
    )
    assert history.status_code == 200
    roles = [m["role"] for m in history.json()["messages"]]
    assert roles == ["user", "assistant"]


def test_chat_rejects_invalid_embed_token(client, admin_headers):
    tutor = _create_tutor(client, admin_headers)

    response = client.post(
        "/api/public/chat",
        json={"tutor_id": tutor["id"], "embed_token": "token-errado", "message": "oi"},
    )

    assert response.status_code == 403
    assert "stack" not in response.text.lower()


def test_chat_rejects_inactive_tutor(client, admin_headers):
    tutor = _create_tutor(client, admin_headers)
    client.post(f"/api/admin/tutors/{tutor['id']}/deactivate", headers=admin_headers)

    response = client.post(
        "/api/public/chat",
        json={"tutor_id": tutor["id"], "embed_token": tutor["embed_token"], "message": "oi"},
    )

    assert response.status_code == 409


def test_unhandled_error_does_not_leak_stack_trace(client, admin_headers):
    response = client.get("/api/admin/tutors/this-id-does-not-exist", headers=admin_headers)

    assert response.status_code == 404
    assert "Traceback" not in response.text


def test_chat_rate_limit_returns_well_formed_429(client, admin_headers):
    """Regressão: o handler de RateLimitExceeded copiava Content-Length do corpo
    original do slowapi para um corpo diferente (mensagem em PT), o que o
    TestClient não pega (não passa pelo parser HTTP real), mas quebrava a
    resposta de verdade em produção. Aqui validamos ao menos que o body/JSON
    do 429 é consistente e não deixa de ter `detail`.
    """
    tutor = _create_tutor(client, admin_headers)
    payload = {"tutor_id": tutor["id"], "embed_token": tutor["embed_token"], "message": "oi"}

    responses = [client.post("/api/public/chat", json=payload) for _ in range(21)]
    statuses = [r.status_code for r in responses]

    assert statuses.count(429) >= 1, statuses
    limited = next(r for r in responses if r.status_code == 429)
    assert limited.json()["detail"]
