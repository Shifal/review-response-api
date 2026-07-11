def _create_review(client, auth_headers, property_id):
    response = client.post("/reviews", json={
        "property_id": property_id,
        "source": "manual",
        "rating": 2,
        "text": "The elevator has been broken for two weeks and no one has fixed it.",
    }, headers=auth_headers)
    return response.json()


def test_draft_then_confirm_flow(client, auth_headers, sample_property):
    review = _create_review(client, auth_headers, sample_property["id"])

    draft_res = client.post(f"/reviews/{review['id']}/draft-response", headers=auth_headers)
    assert draft_res.status_code == 200
    assert draft_res.json()["status"] == "draft"
    assert draft_res.json()["final_text"] is None

    confirm_res = client.post(f"/reviews/{review['id']}/confirm-response", json={}, headers=auth_headers)
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "confirmed"
    assert confirm_res.json()["final_text"] is not None


def test_cannot_draft_twice_for_same_review(client, auth_headers, sample_property):
    review = _create_review(client, auth_headers, sample_property["id"])

    client.post(f"/reviews/{review['id']}/draft-response", headers=auth_headers)
    second_attempt = client.post(f"/reviews/{review['id']}/draft-response", headers=auth_headers)

    assert second_attempt.status_code == 400


def test_cannot_edit_after_confirming(client, auth_headers, sample_property):
    review = _create_review(client, auth_headers, sample_property["id"])
    client.post(f"/reviews/{review['id']}/draft-response", headers=auth_headers)
    client.post(f"/reviews/{review['id']}/confirm-response", json={}, headers=auth_headers)

    edit_attempt = client.patch(f"/reviews/{review['id']}/response", json={
        "final_text": "trying to change this"
    }, headers=auth_headers)

    assert edit_attempt.status_code == 400