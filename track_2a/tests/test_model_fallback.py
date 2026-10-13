"""Model fallback: an endpoint that does not serve the configured model gets the best Apertus v1.5 model it lists."""

import unittest
from types import SimpleNamespace

from src import apertus_client as ac
from src.http_chat import APIError


def response(text='{"label": 0}'):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason="stop")],
                           usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3))


class FakeHTTP:
    def __init__(self, served, listed):
        self.served, self.listed, self.models_used, self.gets = served, listed, [], 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, timeout=60.0, **body):
        self.models_used.append(body["model"])
        if body["model"] not in self.served:
            raise APIError("The model `x` does not exist.", status_code=404)
        return response()

    def get(self, path, timeout=20.0):
        self.gets += 1
        return {"data": [{"id": i} for i in self.listed]}


def client(fake, model="swiss-ai/Apertus-v1.5-70B-thinking"):
    c = ac.ApertusClient(base_url="http://proxy/v1", api_key="k", model_name=model, mock=False)
    c.client = fake
    return c


class TestModelFallback(unittest.TestCase):
    def setUp(self):
        ac._MODEL_SWITCH.update(tried=False, model=None)

    tearDown = setUp

    def test_pick_model_preference(self):
        ids = ["swiss-ai/Apertus-v1.5-8B", "swiss-ai/Apertus-v1.5-70B", "google/gemma"]
        self.assertEqual(ac.pick_model(ids, "swiss-ai/Apertus-v1.5-70B-thinking"), "swiss-ai/Apertus-v1.5-70B")
        self.assertEqual(ac.pick_model(["swiss-ai/apertus-v1.5-70b-thinking"], "swiss-ai/Apertus-v1.5-70B-thinking"),
                         "swiss-ai/apertus-v1.5-70b-thinking")
        self.assertIsNone(ac.pick_model(["google/gemma"], "swiss-ai/Apertus-v1.5-70B-thinking"))

    def test_served_model_is_used_unchanged(self):
        fake = FakeHTTP(served={"swiss-ai/Apertus-v1.5-70B-thinking"}, listed=[])
        resp, err = client(fake)._create_with_retry(model="swiss-ai/Apertus-v1.5-70B-thinking", messages=[])
        self.assertIsNone(err)
        self.assertEqual(fake.models_used, ["swiss-ai/Apertus-v1.5-70B-thinking"])
        self.assertEqual(fake.gets, 0)

    def test_unknown_model_switches_once_for_all_later_requests(self):
        fake = FakeHTTP(served={"swiss-ai/Apertus-v1.5-70B"},
                        listed=["swiss-ai/Apertus-v1.5-8B", "swiss-ai/Apertus-v1.5-70B"])
        c = client(fake)
        resp, err = c._create_with_retry(model="swiss-ai/Apertus-v1.5-70B-thinking", messages=[])
        self.assertIsNone(err)
        resp, err = c._create_with_retry(model="swiss-ai/Apertus-v1.5-70B-thinking", messages=[])
        self.assertIsNone(err)
        self.assertEqual(fake.models_used, ["swiss-ai/Apertus-v1.5-70B-thinking", "swiss-ai/Apertus-v1.5-70B",
                                            "swiss-ai/Apertus-v1.5-70B"])
        self.assertEqual(fake.gets, 1)

    def test_empty_403_for_an_unknown_model_switches_after_the_quick_retries(self):
        fake = FakeHTTP(served={"swiss-ai/Apertus-v1.5-70B"}, listed=["swiss-ai/Apertus-v1.5-70B"])
        fake.create_orig = fake.create

        def create(timeout=60.0, **body):
            if body["model"] not in fake.served:
                fake.models_used.append(body["model"])
                raise APIError("HTTP 403", status_code=403)
            return fake.create_orig(timeout=timeout, **body)
        fake.chat.completions.create = create
        ac.time.sleep, sleep = (lambda s: None), ac.time.sleep
        try:
            resp, err = client(fake)._create_with_retry(model="swiss-ai/Apertus-v1.5-70B-thinking", messages=[])
        finally:
            ac.time.sleep = sleep
        self.assertIsNone(err)
        self.assertEqual(fake.models_used[-1], "swiss-ai/Apertus-v1.5-70B")
        self.assertEqual(fake.gets, 1)

    def test_403_with_the_model_listed_stays_an_error(self):
        fake = FakeHTTP(served=set(), listed=["swiss-ai/Apertus-v1.5-70B-thinking"])
        fake.chat.completions.create = lambda timeout=60.0, **body: (_ for _ in ()).throw(APIError("HTTP 403", status_code=403))
        ac.time.sleep, sleep = (lambda s: None), ac.time.sleep
        try:
            resp, err = client(fake)._create_with_retry(model="swiss-ai/Apertus-v1.5-70B-thinking", messages=[])
        finally:
            ac.time.sleep = sleep
        self.assertIsNone(resp)
        self.assertEqual(err.status_code, 403)

    def test_no_apertus_model_listed_fails_as_before(self):
        fake = FakeHTTP(served=set(), listed=["google/gemma"])
        resp, err = client(fake)._create_with_retry(model="swiss-ai/Apertus-v1.5-70B-thinking", messages=[])
        self.assertIsNone(resp)
        self.assertEqual(getattr(err, "status_code", None), 404)
        self.assertEqual(fake.gets, 1)


if __name__ == "__main__":
    unittest.main()
