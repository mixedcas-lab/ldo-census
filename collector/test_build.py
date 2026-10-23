"""Offline tests: python3 -m unittest discover -s collector -v"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build  # noqa: E402
import classify as C  # noqa: E402


class TestRelevance(unittest.TestCase):
    def test_core(self):
        for t in ("A 54-nA Quiescent Current Capless LDO With −39-dB PSRR at 1 MHz",
                  "A Feedforward Controlled Digital Low-Dropout Regulator With Weight Redistribution Algorithm",
                  "Area-efficient linear regulator with ultra-fast load regulation",
                  "An External Capacitorless Low-Dropout Regulator With High PSR at All Frequencies"):
            self.assertEqual(C.relevance(t, ""), "core", t)

    def test_switched_regulators_are_not_ldos(self):
        for t in ("A Monolithic Resonant Switched-Capacitor Voltage Regulator With Dual-Phase Merged-LC Resonator",
                  "A Switched-Inductor Integrated Voltage Regulator With Nonlinear Feedback and Network-on-Chip Load in 45 nm SOI"):
            self.assertIsNone(C.relevance(t, ""), t)

    def test_ldo_as_a_block_is_related(self):
        t = "A Subthreshold ARM Cortex-M0+ Subsystem in 65 nm CMOS with Integrated LDO"
        self.assertEqual(C.relevance(t, ""), "related")


class TestSpecs(unittest.TestCase):
    def test_title(self):
        s = C.parse_specs("A 54-nA Quiescent Current Capless LDO With −39-dB PSRR at 1 MHz", "")
        self.assertEqual((s["iq"], s["psrr"], s["psrr_f"], s["capless"]), (54e-9, -39.0, 1e6, 1))
        self.assertAlmostEqual(C.parse_specs("A 0.087 fs FOM Analog-assisted Digital LDO", "")["fom"], 0.087e-15)
        self.assertEqual(C.parse_specs("14.6 A 10A Computational Digital LDO Achieving 263A/mm2 Current Density", "")["il"], 10.0)

    def test_abstract(self):
        a = ("The LDO delivers a maximum load current of 100 mA with a quiescent current of 14 µA. The undershoot is 120 mV "
             "with a 100-pF on-chip capacitor and the settling time is 0.5 µs. Dropout voltage of 150 mV, input voltage 1.2 V, "
             "output voltage 1 V. PSRR of -60 dB at 10 kHz. Fabricated in 65-nm CMOS, active area 0.012 mm2.")
        s = C.parse_specs("A Fast Transient LDO", a)
        self.assertEqual((s["il"], s["iq"], s["vdo"], s["vin"], s["vout"]), (0.1, 14e-6, 0.15, 1.2, 1.0))
        self.assertEqual((s["psrr"], s["psrr_f"], s["dv"], s["cout"], s["node"], s["area"]), (-60.0, 1e4, 0.12, 1e-10, 65, 0.012))
        self.assertAlmostEqual(s["ts"], 0.5e-6)
        self.assertAlmostEqual(C.derived(s)["fom_calc"], 1.68e-14)

    def test_more_spellings(self):
        self.assertAlmostEqual(C.parse_specs("X", "The ROR consumes only 130~boldsymbol µA of quiescent current")["iq"], 130e-6)
        self.assertAlmostEqual(C.parse_specs("X", "One of the NLDOs consumes 14 μA of the quiescent current")["iq"], 14e-6)
        self.assertEqual(C.parse_specs("X", "It can deliver 5 A maximum current from 3 to 5 V input")["il"], 5.0)
        self.assertEqual(C.parse_specs("X", "a 53-mV voltage droop and a 132-ns settling time for a 199-mA load step")["il"], 0.199)
        s = C.parse_specs("X", "The power-supply rejection ratio at 1 MHz is -30 dB.")
        self.assertEqual((s["psrr"], s["psrr_f"]), (-30.0, 1e6))
        self.assertEqual(C.parse_specs("X", "the DLB LDO demonstrates a worst case PSR of –28 dB")["psrr"], -28.0)
        self.assertEqual(C.parse_specs("X", "the measured undershoot and overshoot at the output are 75 and 77 mV")["dv"], 0.075)
        self.assertEqual(C.parse_specs("X", "achieves a 53-mV voltage droop")["dv"], 0.053)

    def test_type(self):
        self.assertEqual(C.ldo_type("A Feedforward Controlled Digital Low-Dropout Regulator", ""), "Digital")
        self.assertEqual(C.ldo_type("A Current-mirror-based Analog-assisted Digital LDO", ""), "Hybrid")
        self.assertEqual(C.ldo_type("A Capless LDO With Adaptive Biasing", ""), "Analog")


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = {k: getattr(build, k) for k in ("DATA", "PAPERS", "META")}
        build.DATA = os.path.join(self.tmp, "data")
        build.PAPERS = os.path.join(build.DATA, "papers.json")
        build.META = os.path.join(build.DATA, "meta.json")
        os.makedirs(build.DATA)
        self.cache = os.path.join(self.tmp, "cache")
        os.makedirs(self.cache)

    def tearDown(self):
        for k, v in self.saved.items():
            setattr(build, k, v)
        shutil.rmtree(self.tmp)

    def put(self, n, title, pub, abstract="", year=2025):
        with open(os.path.join(self.cache, "%d.json" % n), "w", encoding="utf-8") as f:
            json.dump({"article_number": n, "title": title, "publication_title": pub, "abstract": abstract,
                       "publication_year": year, "publication_date": "Feb. %d" % year, "doi": "10.1109/x.%d" % n,
                       "authors": {"authors": [{"full_name": "A. Kim", "author_order": 1,
                                                "affiliation": "KAIST, Daejeon, South Korea"}]}}, f)

    def test_rebuild(self):
        config = build.load_json(build.CONFIG, None)
        self.put(1, "A 100-mA Capacitor-Less LDO", "IEEE Journal of Solid-State Circuits", "The quiescent current is 10 µA.")
        self.put(2, "A 12-b SAR ADC", "IEEE Journal of Solid-State Circuits")
        self.put(3, "A Digital LDO With Event-Driven Control", "2025 IEEE Custom Integrated Circuits Conference (CICC)")
        self.put(4, "A 1-A LDO", "Some Other Conference")
        self.put(5, "An RISC-V Processor With Integrated LDO", "IEEE Journal of Solid-State Circuits", "It draws 50 mA.")
        meta = build.rebuild(config, self.cache, "2026-10-23")
        papers = {p["id"]: p for p in build.load_json(build.PAPERS, [])}
        self.assertEqual(set(papers), {"1", "3", "5"})
        self.assertEqual((papers["1"]["ty"], papers["1"]["s"]["il"], papers["1"]["s"]["iq"]), ("Analog", 0.1, 1e-5))
        self.assertEqual(papers["3"]["ty"], "Digital")
        self.assertEqual((papers["5"]["lv"], papers["5"]["s"], papers["5"]["sys"]), ("related", {}, True))
        self.assertNotIn("abstract", json.dumps(list(papers.values())))
        self.assertEqual((meta["core"], meta["last_run_new"]), (2, 0))


if __name__ == "__main__":
    unittest.main()
