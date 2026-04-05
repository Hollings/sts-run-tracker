using System;
using System.Threading.Tasks;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.Hooks;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.PauseMenu;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.ValueProps;
using MegaCrit.Sts2.addons.mega_text;

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

/// <summary>
/// Adds a "Dashboard" button to the pause menu that opens the web tracker in the browser.
/// </summary>
[HarmonyPatch(typeof(NPauseMenu), nameof(NPauseMenu._Ready))]
public static class PauseMenuPatch
{
    public static void Postfix(NPauseMenu __instance)
    {
        try
        {
            var container = __instance.GetNode<Control>("%ButtonContainer");
            // Duplicate the Settings button (it's always visible and has the right scene structure)
            var settingsBtn = container.GetNode<NPauseMenuButton>("Settings");
            var dashboardBtn = (NPauseMenuButton)settingsBtn.Duplicate();
            dashboardBtn.Name = "Dashboard";

            // Update the label text
            var label = dashboardBtn.GetNode<MegaLabel>("Label");
            label.SetTextAutoSize("STS Tracker");

            // Wire up click to open browser
            dashboardBtn.Connect(
                NClickableControl.SignalName.Released,
                Callable.From<NButton>(_ =>
                {
                    var url = $"http://localhost:{ModEntry.DashboardPort}";
                    OS.ShellOpen(url);
                    ModEntry.Log("Opened dashboard: " + url);
                }));

            // Insert after Settings (index 1), before Compendium
            container.AddChild(dashboardBtn);
            container.MoveChild(dashboardBtn, settingsBtn.GetIndex() + 1);

            ModEntry.Log("Dashboard button added to pause menu");
        }
        catch (Exception ex)
        {
            ModEntry.Log("ERROR adding dashboard button to pause menu: " + ex);
        }
    }
}
