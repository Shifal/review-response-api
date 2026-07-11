def test_company_cannot_see_another_companys_properties(client):
    import uuid

    # Company A creates a property
    email_a = f"companya_{uuid.uuid4().hex[:8]}@example.com"
    signup_a = client.post("/auth/signup", json={
        "company_name": "Company A",
        "email": email_a,
        "password": "PassA123",
    })
    token_a = signup_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    client.post("/properties", json={"name": "Company A Property", "city": "CityA"}, headers=headers_a)

    # Company B signs up separately
    email_b = f"companyb_{uuid.uuid4().hex[:8]}@example.com"
    signup_b = client.post("/auth/signup", json={
        "company_name": "Company B",
        "email": email_b,
        "password": "PassB123",
    })
    token_b = signup_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Company B should see zero properties, not Company A's
    response_b = client.get("/properties", headers=headers_b)
    assert response_b.status_code == 200
    assert response_b.json() == []


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/properties")
    assert response.status_code == 401