import json, os, shutil, tempfile, time, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from serve import usage_log

SVC = SimpleNamespace(instance_id="inst-abc", model="qwen3.8-flash-next-iq3_s")
LAST = {"reused": 7, "prompt_ms": 12.5, "decode_ms": 100.0, "drafts_offered": 4, "drafts_accepted": 3}


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def ym():
    return time.strftime("%Y%m", time.gmtime())


class UsageLog(unittest.TestCase):
    @staticmethod
    def _reset():
        usage_log._state.update(path=None, fh=None, month=None, fails=0, disabled=False, written=0)

    def setUp(self):
        self._reset()

    def tearDown(self):
        usage_log.close()                     # Windows will not delete a temp dir an append handle is still in

    def tempdir(self):
        d = tempfile.mkdtemp()
        self.addCleanup(lambda: (usage_log.close(), shutil.rmtree(d, ignore_errors=True)))
        return d

    def write(self, spec, **kw):
        args = dict(request_id="req-1", started=1_700_000_000.5, finish="stop",
                    prompt_read=11, prompt_total=20, engine_last=LAST, output_tokens=5)
        args.update(kw)
        with mock.patch.dict(os.environ, {"STRATA_USAGE_LOG": spec}):
            return usage_log.generation(SVC, **args)   # type: ignore[arg-type]

    def test_off_by_default(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(usage_log.generation(SVC, request_id="r", started=1.0, finish="stop",
                                                 prompt_read=1, prompt_total=1, engine_last={}, output_tokens=1))
            self.assertEqual(os.listdir(d), [])

    def test_one_row_per_generation_with_the_servers_own_numbers(self):
        d = self.tempdir()
        self.assertTrue(self.write(d))
        usage_log.close()
        files = os.listdir(d)
        self.assertEqual(files, [f"usage-{ym()}.jsonl"])
        r = rows(Path(d, files[0]))[0]
        self.assertEqual((r["id"], r["instance_id"], r["pid"], r["model"]),
                         ("req-1", "inst-abc", os.getpid(), "qwen3.8-flash-next-iq3_s"))
        # the categories the cost model needs, exactly as the engine reported them
        self.assertEqual((r["prompt_read"], r["prompt_total"], r["reused"], r["output"]), (11, 20, 7, 5))
        self.assertEqual((r["prompt_ms"], r["decode_ms"]), (12.5, 100.0))
        self.assertEqual((r["drafts_offered"], r["drafts_accepted"]), (4, 3))
        self.assertLess(r["t_start"], r["t"])
        self.assertEqual(r["v"], usage_log.SCHEMA_VERSION)

    def test_explicit_file_is_honoured(self):
        d = self.tempdir()
        p = os.path.join(d, "usage.jsonl")
        self.assertTrue(self.write(p))
        usage_log.close()
        self.assertEqual(len(rows(p)), 1)
        self.assertEqual([f for f in os.listdir(d) if f.startswith("usage-")], [])

    def test_a_broken_target_never_reaches_the_request(self):
        d = self.tempdir()
        blocker = os.path.join(d, "blocker")
        Path(blocker).write_text("not a directory")
        for _ in range(usage_log.MAX_FAILURES + 2):
            self.assertFalse(self.write(os.path.join(blocker, "sub")))   # "no exception" is the assertion
        st = usage_log.status()
        self.assertGreaterEqual(st["failures"], usage_log.MAX_FAILURES)
        self.assertFalse(st["enabled"])
        self.assertEqual(st["written"], 0)

    def test_missing_arguments_do_not_raise(self):
        d = self.tempdir()
        self.assertTrue(self.write(d, engine_last=None, prompt_total=None, output_tokens=None))
        usage_log.close()
        r = rows(Path(d, f"usage-{ym()}.jsonl"))[0]
        self.assertEqual((r["reused"], r["prompt_total"], r["output"]), (0, 0, 0))

    def test_month_boundary_opens_a_new_file(self):
        d = self.tempdir()
        with mock.patch.object(usage_log, "_month", lambda _now: "202610"):
            self.assertTrue(self.write(d))
        with mock.patch.object(usage_log, "_month", lambda _now: "202611"):
            self.assertTrue(self.write(d))
        usage_log.close()
        self.assertEqual(sorted(os.listdir(d)), ["usage-202610.jsonl", "usage-202611.jsonl"])


if __name__ == "__main__":
    unittest.main()
