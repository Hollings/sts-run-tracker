using System.Collections.Generic;
using System.Threading.Tasks;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Cards;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Enchantments;
using StS2Sim.SilentTests;

namespace StS2Sim.CharTests;

/// <summary>
/// Card enchantments (Instinct, Sharp, Nimble, ...) ride on individual deck
/// cards in the save file; the deck loader must reattach them or it sims a
/// materially weaker deck (Instinct alone doubles an attack). These tests
/// guard the DeckEntry → ReplaceDeck → EnchantInternal pipeline with the
/// game's own numbers. Enchantment ids resolve from ModelDb at runtime — no
/// guessed id strings.
/// </summary>
internal static class EnchantmentTests
{
    public static async Task<IReadOnlyList<TestHelpers.TestResult>> RunAll()
    {
        var instinctId = ModelDb.Enchantment<Instinct>().Id.ToString();
        var sharpId = ModelDb.Enchantment<Sharp>().Id.ToString();
        var nimbleId = ModelDb.Enchantment<Nimble>().Id.ToString();
        var glamId = ModelDb.Enchantment<Glam>().Id.ToString();

        var results = new List<TestHelpers.TestResult>
        {
            // Instinct: powered attacks deal double damage. 6 → 12.
            await CharTestHelpers.Test<Ironclad>(
                "Instinct Strike deals 12 (doubled)",
                new List<Harness.DeckEntry> { new(typeof(StrikeIronclad), 0, instinctId) },
                async h =>
                {
                    Reflect.SetEnergy(h.Player.PlayerCombatState!, 9);
                    var card = CharTestHelpers.MoveToHand(h, typeof(StrikeIronclad))!;
                    if (card.Enchantment == null) return "enchantment did not attach to the card";
                    var before = h.Dummy.CurrentHp;
                    await CharTestHelpers.PlayCard(h, card);
                    return TestHelpers.Expect(before - h.Dummy.CurrentHp, 12, "damage");
                }),

            // Sharp N: +N damage. Strike with Sharp 4 → 10.
            await CharTestHelpers.Test<Ironclad>(
                "Sharp 4 Strike deals 10",
                new List<Harness.DeckEntry> { new(typeof(StrikeIronclad), 0, sharpId, 4) },
                async h =>
                {
                    Reflect.SetEnergy(h.Player.PlayerCombatState!, 9);
                    var card = CharTestHelpers.MoveToHand(h, typeof(StrikeIronclad))!;
                    var before = h.Dummy.CurrentHp;
                    await CharTestHelpers.PlayCard(h, card);
                    return TestHelpers.Expect(before - h.Dummy.CurrentHp, 10, "damage");
                }),

            // Nimble N: +N block. Defend with Nimble 3 → 8.
            await CharTestHelpers.Test<Ironclad>(
                "Nimble 3 Defend gives 8 block",
                new List<Harness.DeckEntry> { new(typeof(DefendIronclad), 0, nimbleId, 3) },
                async h =>
                {
                    Reflect.SetEnergy(h.Player.PlayerCombatState!, 9);
                    var card = CharTestHelpers.MoveToHand(h, typeof(DefendIronclad))!;
                    await CharTestHelpers.PlayCard(h, card);
                    return TestHelpers.Expect(h.Player.Creature.Block, 8, "block");
                }),

            // Upgrade + enchantment stack: Strike+ (9) with Instinct → 18.
            await CharTestHelpers.Test<Ironclad>(
                "Instinct Strike+ deals 18",
                new List<Harness.DeckEntry> { new(typeof(StrikeIronclad), 1, instinctId) },
                async h =>
                {
                    Reflect.SetEnergy(h.Player.PlayerCombatState!, 9);
                    var card = CharTestHelpers.MoveToHand(h, typeof(StrikeIronclad))!;
                    var before = h.Dummy.CurrentHp;
                    await CharTestHelpers.PlayCard(h, card);
                    return TestHelpers.Expect(before - h.Dummy.CurrentHp, 18, "damage");
                }),

            // ── Replay × X-cost ───────────────────────────────────────────
            // Control: Skewer is X-cost, 8 damage per hit, hits = X. At 3
            // energy → 3 hits → 24. SpendResources captures X=3.
            await CharTestHelpers.Test<Ironclad>(
                "Skewer X=3 deals 24 (no replay)",
                new List<Harness.DeckEntry> { new(typeof(Skewer)) },
                async h =>
                {
                    Reflect.SetEnergy(h.Player.PlayerCombatState!, 3);
                    var card = CharTestHelpers.MoveToHand(h, typeof(Skewer))!;
                    var before = h.Dummy.CurrentHp;
                    await CharTestHelpers.PlayCard(h, card);
                    return TestHelpers.Expect(before - h.Dummy.CurrentHp, 24, "damage");
                }),

            // The question: does Replay work with an X-cost card? Glam adds
            // +1 play (playCount=2). The X value is captured ONCE before the
            // OnPlayWrapper replay loop and must persist across iterations —
            // if the second play re-captured X it would see 0 energy → 0
            // hits → 24. Correct game behavior: both plays use X=3 → 48.
            await CharTestHelpers.Test<Ironclad>(
                "Skewer X=3 + Glam replays at the captured X (48, not 24)",
                new List<Harness.DeckEntry> { new(typeof(Skewer), 0, glamId) },
                async h =>
                {
                    Reflect.SetEnergy(h.Player.PlayerCombatState!, 3);
                    var card = CharTestHelpers.MoveToHand(h, typeof(Skewer))!;
                    if (card.GetEnchantedReplayCount() != 1)
                        return $"Glam did not grant a replay (GetEnchantedReplayCount={card.GetEnchantedReplayCount()})";
                    var before = h.Dummy.CurrentHp;
                    await CharTestHelpers.PlayCard(h, card);
                    return TestHelpers.Expect(before - h.Dummy.CurrentHp, 48, "damage");
                }),
        };

        return results;
    }
}
