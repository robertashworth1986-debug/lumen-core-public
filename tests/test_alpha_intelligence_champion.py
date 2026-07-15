import math
import unittest

from code.alpha_intelligence_champion import (
    bio_digital_echo,
    harmonic_coherence,
    quantum_alpha_lock,
    select_champion,
)


class AlphaIntelligenceChampionTests(unittest.TestCase):
    def test_harmonic_signal_has_bounded_coherence(self):
        signal = [math.sin(2.0 * math.pi * i / 16.0) for i in range(64)]
        score = harmonic_coherence(signal)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        self.assertGreater(score, 0.70)

    def test_echo_field_is_bounded_and_same_length(self):
        field = bio_digital_echo([0, 1, 0, 1, 0, 1])
        self.assertEqual(len(field), 6)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in field))

    def test_lock_is_deterministic(self):
        payload = {"alpha": 1, "omega": [2, 3]}
        self.assertEqual(quantum_alpha_lock(payload), quantum_alpha_lock(payload))

    def test_champion_selection_is_deterministic(self):
        candidates = {
            "steady": [0.5] * 64,
            "harmonic": [math.sin(2.0 * math.pi * i / 16.0) for i in range(64)],
            "noisy": [((i * 37) % 101) / 100.0 for i in range(64)],
        }
        first = select_champion(candidates)
        second = select_champion(candidates)
        self.assertEqual(first.champion_id, second.champion_id)
        self.assertEqual(first.quantum_alpha_lock, second.quantum_alpha_lock)
        self.assertEqual(len(first.quantum_alpha_lock), 64)

    def test_empty_candidates_rejected(self):
        with self.assertRaises(ValueError):
            select_champion({})


if __name__ == "__main__":
    unittest.main()
