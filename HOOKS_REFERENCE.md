# StS2 Decompiled API Reference

Quick reference for the game internals we need. All types decompiled from
`data_sts2_windows_x86_64/sts2.dll` (v0.99.1, .NET 9.0, Godot 4.5.1).

Full decompilation at: `decompiled/full/` (ILSpy project output)
Individual types at: `decompiled/*.cs`

---

## Mod System

### Loading
- Mods live in `<game_dir>/mods/` or Steam Workshop
- Each mod is a directory containing a JSON manifest + optional DLL + optional PCK
- The DLL must be named `<manifest.id>.dll`

### Manifest (`StS2Tracker.json`)
```json
{
  "id": "StS2Tracker",         // required, also the DLL filename
  "name": "StS2 Run Tracker",
  "author": "jhol",
  "description": "...",
  "version": "0.1.0",
  "has_dll": true,              // load <id>.dll
  "has_pck": false,             // load <id>.pck (Godot resource pack)
  "affects_gameplay": false,    // false = not flagged as gameplay-modifying
  "dependencies": []            // optional, list of other mod IDs
}
```

### Entry Point
Two options (checked in order):
1. **`[ModInitializer("MethodName")]`** attribute on a class - calls the named static method
2. **Auto `Harmony.PatchAll(assembly)`** - if no ModInitializer attribute found

Source: `ModManager.TryLoadMod()` in `decompiled/ModManager.cs:404-476`

### Assembly Resolution
The game auto-resolves `sts2` and `0Harmony` assembly references, so mods
don't need to bundle these. Source: `ModManager.HandleAssemblyResolveFailure()`

---

## Hook System (`MegaCrit.Sts2.Core.Hooks.Hook`)

All hooks are static async methods. They iterate `combatState.IterateHookListeners()`
which yields all AbstractModel instances (relics, powers, cards, monsters).

**We Harmony-patch these static methods directly** rather than implementing AbstractModel.

### Damage Hooks

```csharp
// Fired when a creature deals damage to a target
static async Task AfterDamageGiven(
    PlayerChoiceContext choiceContext,
    CombatState combatState,
    Creature? dealer,           // who dealt the damage (null for environmental)
    DamageResult results,       // blocked, unblocked, overkill, was_killed
    ValueProp props,            // damage properties (card, unblockable, etc.)
    Creature target,            // who received the damage
    CardModel? cardSource       // the card that caused it (null for non-card damage)
)

// Fired when a creature receives damage
static async Task AfterDamageReceived(
    PlayerChoiceContext choiceContext,
    IRunState runState,
    CombatState? combatState,
    Creature target,            // who received damage
    DamageResult result,
    ValueProp props,
    Creature? dealer,           // who dealt it
    CardModel? cardSource
)
```

### Block Hook
```csharp
static async Task AfterBlockGained(
    CombatState combatState,
    Creature creature,          // who gained block
    decimal amount,             // how much
    ValueProp props,
    CardModel? cardSource
)
```

### Card Play Hook
```csharp
static async Task AfterCardPlayed(
    CombatState combatState,
    PlayerChoiceContext choiceContext,
    CardPlay cardPlay           // .Card (CardModel), .Target (Creature?), .PlayIndex, .PlayCount
)
```

### Combat Lifecycle
```csharp
static async Task BeforeCombatStart(IRunState runState, CombatState? combatState)
static async Task AfterCombatEnd(IRunState runState, CombatState? combatState, CombatRoom room)
static async Task AfterCombatVictory(IRunState runState, CombatState? combatState, CombatRoom room)
```

### Turn Hooks
```csharp
static async Task AfterPlayerTurnStart(
    CombatState combatState,
    PlayerChoiceContext choiceContext,
    Player player               // which player's turn
)

static async Task AfterTurnEnd(CombatState combatState, CombatSide side)
```

### Power Hooks
```csharp
static async Task AfterPowerApplied(
    PlayerChoiceContext choiceContext,
    CombatState combatState,
    PowerModel power,
    Creature target,
    int amount,
    Creature? source
)

static async Task AfterPowerRemoved(CombatState combatState, PowerModel power, Creature creature)
```

---

## Key Data Types

### `DamageResult` (`MegaCrit.Sts2.Core.Entities.Creatures`)
```csharp
public class DamageResult {
    Creature Receiver;
    ValueProp Props;
    int BlockedDamage;          // damage absorbed by block
    int UnblockedDamage;        // damage that went through to HP
    int OverkillDamage;         // damage beyond 0 HP
    int TotalDamage => BlockedDamage + UnblockedDamage;
    bool WasBlockBroken;
    bool WasFullyBlocked;
    bool WasTargetKilled;
}
```

### `CardPlay` (`MegaCrit.Sts2.Core.Entities.Cards`)
```csharp
public class CardPlay {
    CardModel Card;             // the card being played
    Creature? Target;           // target creature (null for untargeted)
    PileType ResultPile;        // where the card goes after play
    bool IsAutoPlay;
    int PlayIndex;              // index in multi-play series
    int PlayCount;              // total plays in series
}
```

### `Creature` (`MegaCrit.Sts2.Core.Entities.Creatures`)
```csharp
public class Creature {
    Player? Player;             // non-null if this creature IS a player
    bool IsPlayer;
    bool IsEnemy;
    CombatSide Side;
    ModelId ModelId;            // e.g. CHARACTER.DEFECT or MONSTER.TOADPOLE
    string DisplayName;
    int CurrentHp;
    int MaxHp;
    int Block;
    Player? PetOwner;           // if this creature is a pet/minion
    bool IsPet;
    IReadOnlyList<PowerModel> Powers;
}
```

### `Player` (`MegaCrit.Sts2.Core.Entities.Players`)
```csharp
public class Player {
    ulong NetId;                // Steam ID (e.g. 76561198036923077)
    CharacterModel Character;   // .Id = CHARACTER.DEFECT, .Title = display name
    int CurrentHp;
    int MaxHp;
    int Gold;
    IReadOnlyList<CardModel> Deck;
    IReadOnlyList<RelicModel> Relics;
}
```

### `CardModel` (`MegaCrit.Sts2.Core.Models`)
```csharp
public abstract class CardModel : AbstractModel {
    ModelId Id;                 // e.g. CARD.STRIKE_DEFECT
    Player Owner;               // the player who owns this card
    // ... damage values, block values, cost, etc.
}
```

### `CombatState` (`MegaCrit.Sts2.Core.Combat`)
```csharp
public class CombatState {
    EncounterModel Encounter;   // .Id = ENCOUNTER.TOADPOLES_WEAK
    IRunState RunState;
    IEnumerable<Creature> Allies;   // player creatures
    IEnumerable<Creature> Enemies;  // monster creatures
    IReadOnlyList<Player> Players;
    int TurnNumber;
}
```

### `CombatRoom` (`MegaCrit.Sts2.Core.Rooms`)
```csharp
public class CombatRoom : AbstractRoom {
    CombatState CombatState;
    EncounterModel Encounter;
    ModelId ModelId;            // encounter ID
}
```

---

## Networking (Multiplayer)

- P2P via Steam (`SteamClientConnectionInitializer`)
- Host-authoritative: combat logic runs on host
- Full combat state synced to all clients via `CombatStateSynchronizer`
- Even clients see all players' card plays, damage events, etc. in hooks
- Player IDs = `Player.NetId` = Steam ID throughout

## File Paths

| What | Where |
|------|-------|
| Game install | `C:\Program Files (x86)\Steam\steamapps\common\Slay the Spire 2\` |
| Game DLLs | `...\data_sts2_windows_x86_64\` |
| Mods folder | `...\mods\` (create if not exists) |
| Save data | `Steam\userdata\<uid>\2868840\remote\` |
| Run history | `.../profile1/saves/history/*.run` (JSON) |
| Current run | `.../profile1/saves/current_run.save` (JSON) |
| Progress | `.../profile1/saves/progress.save` (JSON) |
| Game logs | `%APPDATA%\SlayTheSpire2\logs\godot*.log` |
