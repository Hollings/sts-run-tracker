using System;
using System.Threading.Tasks;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Hooks;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.ValueProps;

namespace StS2Tracker;

/// <summary>
/// Harmony patches for the static Hook methods in MegaCrit.Sts2.Core.Hooks.Hook.
/// We use Postfix patches so the game's own logic runs first, then we record the data.
/// </summary>
[HarmonyPatch(typeof(Hook))]
public static class HarmonyPatches
{
    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.BeforeCombatStart))]
    public static void BeforeCombatStart_Postfix(IRunState runState, CombatState? combatState)
    {
        try
        {
            CombatTracker.OnCombatStart(runState, combatState);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in BeforeCombatStart patch: " + ex);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.AfterCombatEnd))]
    public static void AfterCombatEnd_Postfix(IRunState runState, CombatState? combatState, CombatRoom room)
    {
        try
        {
            CombatTracker.OnCombatEnd(runState, combatState, room);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in AfterCombatEnd patch: " + ex);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.AfterDamageGiven))]
    public static void AfterDamageGiven_Postfix(
        CombatState combatState,
        Creature? dealer,
        DamageResult results,
        ValueProp props,
        Creature target,
        CardModel? cardSource)
    {
        try
        {
            CombatTracker.OnDamageGiven(dealer, results, target, cardSource);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in AfterDamageGiven patch: " + ex);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.AfterBlockGained))]
    public static void AfterBlockGained_Postfix(
        CombatState combatState,
        Creature creature,
        decimal amount,
        ValueProp props,
        CardModel? cardSource)
    {
        try
        {
            CombatTracker.OnBlockGained(creature, amount);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in AfterBlockGained patch: " + ex);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.AfterCardPlayed))]
    public static void AfterCardPlayed_Postfix(
        CombatState combatState,
        CardPlay cardPlay)
    {
        try
        {
            CombatTracker.OnCardPlayed(cardPlay);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in AfterCardPlayed patch: " + ex);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.AfterPlayerTurnStart))]
    public static void AfterPlayerTurnStart_Postfix(
        CombatState combatState,
        Player player)
    {
        try
        {
            CombatTracker.OnTurnStart(player);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in AfterPlayerTurnStart patch: " + ex);
        }
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Hook.AfterPowerAmountChanged))]
    public static void AfterPowerAmountChanged_Postfix(
        CombatState combatState,
        PowerModel power,
        decimal amount,
        Creature? applier,
        CardModel? cardSource)
    {
        try
        {
            CombatTracker.OnPowerChanged(power, (int)amount, applier);
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR in AfterPowerAmountChanged patch: " + ex);
        }
    }
}
