import requests
import json

url = "https://mediathekviewweb.de/api/query"
headers = {"Content-Type": "text/plain"}
data = {
    "queries": [
        {
            "fields": ["title", "topic"],
            "query": "Tatort"
        }
    ],
    "sortBy": "timestamp",
    "sortOrder": "desc",
    "future": False,
    "offset": 0,
    "size": 1
}

try:
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    print("Status Code:", response.status_code)
    print("Response JSON:", json.dumps(response.json(), indent=2))
except Exception as e:
    print("Error:", e)
