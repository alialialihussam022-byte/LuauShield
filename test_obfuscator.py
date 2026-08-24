import unittest
from luau_obfuscator import ObfuscationError, obfuscate


class CorrectnessTests(unittest.TestCase):
    def test_print(self):
        result = obfuscate('print("hi")', seed=1)
        self.assertIn('print(', result.code)
        self.assertIn('bit32.bxor', result.code)

    def test_structure_is_preserved(self):
        source = '''local total = 0
for i = 1, 3 do
  total += i
end
print(total)
game:GetService("Players").PlayerAdded:Connect(function(player)
  print(player.Name)
end)'''
        result = obfuscate(source, seed=7)
        for line in ("for i = 1, 3 do", "total += i", "game:GetService(", "PlayerAdded:Connect"):
            self.assertIn(line, result.code)

    def test_invalid_source_is_rejected(self):
        with self.assertRaises(ObfuscationError):
            obfuscate('print("never closed)')

    def test_safe_mode_is_exact(self):
        source = 'local x = { [1] = "ok" }'
        self.assertEqual(obfuscate(source, mode="safe").code, source)


if __name__ == "__main__":
    unittest.main()