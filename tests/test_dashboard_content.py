"""Checks that dashboard roadmap and playground values come from project code."""

import unittest

from src.dashboard_data import build_dashboard_payload


class DashboardContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = build_dashboard_payload(benchmark_trials=1)

    def test_dashboard_covers_all_36_sessions_and_phase_states(self) -> None:
        roadmap = self.payload["roadmap"]
        self.assertEqual(sum(len(phase["sessions"]) for phase in roadmap), 36)
        self.assertEqual(roadmap[0]["status"], "completed")
        self.assertEqual(roadmap[1]["status"], "completed")
        self.assertTrue(all(phase["status"] == "upcoming" for phase in roadmap[2:]))
        self.assertEqual(self.payload["project"]["total_sessions"], 36)
        self.assertEqual(
            [session["title"] for session in roadmap[0]["sessions"]],
            [
                "Session 1: Computational models and project baseline",
                "Session 2: Hardware performance bottlenecks",
                "Session 3: Amortised analysis of growing event storage",
                "Session 4: Expected complexity and fingerprints",
                "Session 5: Profiling-driven optimisation",
                "Session 6: Choosing a computational model",
            ],
        )

    def test_sessions_7_through_12_have_live_acceptance_checks(self) -> None:
        session_7 = self.payload["roadmap"][1]["sessions"][0]
        self.assertEqual(session_7["title"], "Session 7: Range queries and lazy updates")
        self.assertEqual(session_7["status"], "completed")
        self.assertTrue(all(
            self.payload["phase2"][f"session{number}"]["acceptance_passed"]
            for number in range(7, 13)
        ))
        self.assertTrue(all(
            self.payload["roadmap"][1]["sessions"][number - 7]["status"] == "completed"
            for number in range(7, 13)
        ))

    def test_sessions_13_through_36_remain_upcoming(self) -> None:
        later = [session for phase in self.payload["roadmap"][2:] for session in phase["sessions"]]
        self.assertEqual(len(later), 24)
        self.assertTrue(all(session["status"] == "upcoming" for session in later))

    def test_live_session1_benchmarks_use_all_required_sizes(self) -> None:
        rows = self.payload["session1"]["benchmarks"]
        self.assertEqual([row["product_count"] for row in rows], [20, 100, 1000])
        self.assertTrue(all(row["oracle_passed"] for row in rows))

    def test_playground_outputs_come_from_existing_implementations(self) -> None:
        buffer = self.payload["playground"]["dynamic_buffer"]
        self.assertEqual(buffer["events_appended"], 16)
        self.assertEqual(buffer["cumulative_copies"], 15)
        self.assertEqual(buffer["total_actual_writes"], 31)
        collision = self.payload["playground"]["fingerprint_collision"]
        self.assertTrue(collision["collision_rejected_as_duplicate"])
        self.assertFalse(collision["is_duplicate"])


if __name__ == "__main__":
    unittest.main()
