def test_duplicate_source_review_id_does_not_create_new_row(client, auth_headers, sample_property):
    payload = {
        "property_id": sample_property["id"],
        "source": "google",
        "source_review_id": "test_dup_001",
        "rating": 4,
        "text": "Solid place, good management.",
    }

    first = client.post("/reviews", json=payload, headers=auth_headers)
    second = client.post("/reviews", json=payload, headers=auth_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_different_source_review_id_creates_new_row(client, auth_headers, sample_property):
    base_payload = {
        "property_id": sample_property["id"],
        "source": "google",
        "rating": 3,
        "text": "Decent experience overall.",
    }

    first = client.post("/reviews", json={**base_payload, "source_review_id": "test_a_001"}, headers=auth_headers)
    second = client.post("/reviews", json={**base_payload, "source_review_id": "test_a_002"}, headers=auth_headers)

    assert first.json()["id"] != second.json()["id"]