def test_positive_review_gets_positive_sentiment(client, auth_headers, sample_property):
    response = client.post("/reviews", json={
        "property_id": sample_property["id"],
        "source": "google",
        "rating": 5,
        "text": "Absolutely wonderful place to live, staff is amazing and always helpful.",
    }, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["sentiment"] == "positive"


def test_negative_review_gets_negative_sentiment(client, auth_headers, sample_property):
    response = client.post("/reviews", json={
        "property_id": sample_property["id"],
        "source": "google",
        "rating": 1,
        "text": "Terrible experience, maintenance never responds and the building is falling apart.",
    }, headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["sentiment"] == "negative"