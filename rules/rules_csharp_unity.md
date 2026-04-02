# C# + Unity Coding Rules

> Framework-specific rules for Unity game development projects (2D/3D), targeting PC/Steam.

---

## 1. Project Structure

```
Assets/
├── _Project/                  # All project-specific assets (prefixed to stay at top)
│   ├── Art/
│   │   ├── Sprites/           # 2D sprites, sprite atlases
│   │   ├── UI/                # UI icons, backgrounds, frames
│   │   ├── Animations/        # Animation clips and controllers
│   │   ├── Materials/
│   │   ├── Shaders/
│   │   └── VFX/               # Particle systems, visual effects
│   ├── Audio/
│   │   ├── Music/
│   │   ├── SFX/
│   │   └── Mixers/            # AudioMixer assets
│   ├── Data/
│   │   ├── Cards/             # ScriptableObject card definitions
│   │   ├── Enemies/           # ScriptableObject enemy definitions
│   │   ├── Events/            # ScriptableObject random events
│   │   ├── Relics/            # ScriptableObject relic/artifact definitions
│   │   └── Maps/              # ScriptableObject map/floor configurations
│   ├── Prefabs/
│   │   ├── UI/
│   │   ├── Cards/
│   │   ├── Enemies/
│   │   ├── Effects/
│   │   └── Map/
│   ├── Scenes/
│   │   ├── Boot.unity         # Initialization scene
│   │   ├── MainMenu.unity
│   │   ├── Map.unity          # Map/node selection scene
│   │   ├── Combat.unity       # Battle scene
│   │   ├── Event.unity        # Random event scene
│   │   ├── Shop.unity
│   │   └── GameOver.unity
│   ├── Scripts/
│   │   ├── Core/              # Game manager, state machine, save/load
│   │   │   ├── GameManager.cs
│   │   │   ├── GameState.cs
│   │   │   ├── SaveSystem.cs
│   │   │   └── SceneLoader.cs
│   │   ├── Cards/             # Card logic, effects, deck management
│   │   │   ├── CardData.cs           # ScriptableObject definition
│   │   │   ├── CardInstance.cs       # Runtime card instance
│   │   │   ├── DeckManager.cs
│   │   │   ├── HandManager.cs
│   │   │   └── Effects/              # Individual card effect implementations
│   │   ├── Combat/            # Turn system, energy, targeting
│   │   │   ├── CombatManager.cs
│   │   │   ├── TurnSystem.cs
│   │   │   ├── EnergySystem.cs
│   │   │   └── TargetingSystem.cs
│   │   ├── Characters/        # Player, enemies, stats, buffs/debuffs
│   │   │   ├── Character.cs          # Base class
│   │   │   ├── Player.cs
│   │   │   ├── Enemy.cs
│   │   │   ├── EnemyAI.cs
│   │   │   ├── StatusEffect.cs
│   │   │   └── Stats.cs
│   │   ├── Map/               # Procedural map generation, node types
│   │   │   ├── MapGenerator.cs
│   │   │   ├── MapNode.cs
│   │   │   └── MapRenderer.cs
│   │   ├── UI/                # All UI controllers and views
│   │   │   ├── Screens/              # Full-screen UI (menus, game over)
│   │   │   ├── HUD/                  # In-game overlay elements
│   │   │   ├── Cards/                # Card visual representation
│   │   │   └── Common/              # Reusable UI components
│   │   ├── Events/            # Random event system
│   │   ├── Relics/            # Relic/artifact system
│   │   ├── Shop/              # Shop logic
│   │   ├── Audio/             # Audio manager, sound pooling
│   │   ├── Persistence/       # Save/load serialization
│   │   └── Utils/             # Extension methods, helpers
│   ├── Fonts/
│   ├── Settings/              # URP settings, quality settings
│   └── StreamingAssets/       # External data files if needed
├── Plugins/                   # Third-party native plugins
├── TextMesh Pro/              # TMP essentials
└── Resources/                 # Only for assets that MUST be loaded by name at runtime
                               # Keep this minimal — prefer Addressables or direct references
```

### File Naming Conventions
- **Scripts**: `PascalCase.cs` matching the primary class name — `DeckManager.cs`
- **Scenes**: `PascalCase.unity` — `MainMenu.unity`, `Combat.unity`
- **Prefabs**: `PascalCase.prefab` — `CardVisual.prefab`, `EnemySlime.prefab`
- **ScriptableObjects**: `PascalCase.asset` — `FireballCard.asset`, `SlimeEnemy.asset`
- **Sprites/Textures**: `snake_case.png` — `card_frame_common.png`, `icon_attack.png`
- **Audio**: `snake_case.wav/.ogg` — `sfx_card_play.wav`, `music_combat_01.ogg`
- **Animations**: `PascalCase.anim` — `EnemyIdle.anim`, `CardDraw.anim`
- **Materials**: `PascalCase.mat` — `CardGlow.mat`

### Assembly Definitions
Use Assembly Definition files (`.asmdef`) to organize code into modules:
```
Scripts/Core/       → Game.Core.asmdef
Scripts/Cards/      → Game.Cards.asmdef
Scripts/Combat/     → Game.Combat.asmdef
Scripts/Characters/ → Game.Characters.asmdef
Scripts/UI/         → Game.UI.asmdef
Scripts/Utils/      → Game.Utils.asmdef
Tests/EditMode/     → Game.Tests.EditMode.asmdef
Tests/PlayMode/     → Game.Tests.PlayMode.asmdef
```
This enforces dependency boundaries and speeds up compilation.

---

## 2. C# / Unity Naming Conventions

### General
- **Classes/Structs/Enums**: `PascalCase` — `DeckManager`, `CardRarity`, `CombatState`
- **Interfaces**: `IPascalCase` — `IDamageable`, `ITargetable`, `ISaveable`
- **Methods**: `PascalCase` — `DrawCards()`, `ApplyDamage()`, `CalculateBlock()`
- **Properties**: `PascalCase` — `CurrentHealth`, `MaxEnergy`, `IsAlive`
- **Public fields**: `camelCase` (only when required by Unity serialization)
- **Private fields**: `_camelCase` — `_currentHealth`, `_deckList`, `_turnCount`
- **Constants**: `PascalCase` (C# convention) — `MaxHandSize`, `DefaultEnergy`
- **Static readonly**: `PascalCase` — `EmptyDeck`, `DefaultStats`
- **Enums**: `PascalCase` for type and members — `CardType.Attack`, `Rarity.Rare`
- **Parameters**: `camelCase` — `int damageAmount`, `CardData cardData`
- **Local variables**: `camelCase` — `var remainingHealth`, `var drawnCards`
- **Events/Delegates**: `PascalCase` with `On` prefix — `OnCardPlayed`, `OnTurnEnded`
- **Namespaces**: `PascalCase`, matching folder structure — `Game.Cards`, `Game.Combat`

### Unity-Specific
- **MonoBehaviour classes**: Name matches file name exactly
- **SerializeField**: Use `[SerializeField]` with private fields, not public fields
- **Tooltip**: Add `[Tooltip("...")]` for inspector-editable fields used by designers
- **Header/Space**: Use `[Header("Section")]` and `[Space]` to organize inspector fields

```csharp
// Good
public class CombatManager : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private Transform _cardPlayArea;
    [SerializeField] private EnergyDisplay _energyDisplay;

    [Header("Settings")]
    [SerializeField, Tooltip("Cards drawn at start of turn")]
    private int _drawCount = 5;

    [SerializeField, Tooltip("Starting energy per turn")]
    private int _baseEnergy = 3;

    private TurnState _currentTurn;
    private readonly List<CardInstance> _hand = new();

    public int CurrentEnergy { get; private set; }
    public bool IsPlayerTurn => _currentTurn == TurnState.Player;

    public event Action<CardInstance> OnCardPlayed;
}
```

---

## 3. Unity-Specific Patterns

### ScriptableObject for Data
Use ScriptableObjects for all game data definitions. This is critical for a deck-builder:

```csharp
[CreateAssetMenu(fileName = "NewCard", menuName = "Game/Card Data")]
public class CardData : ScriptableObject
{
    [Header("Identity")]
    public string cardName;
    public string description;
    public Sprite artwork;
    public CardType cardType;
    public Rarity rarity;

    [Header("Cost")]
    public int energyCost;

    [Header("Effects")]
    public List<CardEffect> effects;

    [Header("Upgrades")]
    public bool isUpgradeable;
    public CardData upgradedVersion;
}
```

**Why ScriptableObjects:**
- Designer-friendly (editable in Inspector without code changes)
- Memory efficient (shared references, not duplicated data)
- Easy to create variants (duplicate asset, tweak values)
- Version-control friendly (YAML serialization)

### Singleton Pattern (GameManager only)
Use sparingly — only for true global managers:

```csharp
public class GameManager : MonoBehaviour
{
    public static GameManager Instance { get; private set; }

    private void Awake()
    {
        if (Instance != null && Instance != this)
        {
            Destroy(gameObject);
            return;
        }
        Instance = this;
        DontDestroyOnLoad(gameObject);
    }
}
```

**Limit singletons to:** GameManager, AudioManager, SaveSystem.
**Do NOT make singletons for:** CombatManager, DeckManager, MapGenerator, UI controllers.
Use dependency injection or scene references for everything else.

### State Machine Pattern
Use for game flow and combat states:

```csharp
public enum GamePhase
{
    MainMenu,
    MapNavigation,
    Combat,
    Event,
    Shop,
    Rest,
    Reward,
    GameOver
}

public enum CombatState
{
    Setup,
    PlayerTurnStart,
    PlayerAction,
    PlayerTurnEnd,
    EnemyTurn,
    Victory,
    Defeat
}
```

### Object Pooling
Pool frequently instantiated/destroyed objects (cards in hand, damage numbers, particles):

```csharp
// Use Unity's built-in ObjectPool<T> (Unity 2021+)
private ObjectPool<DamageNumber> _damagePool;

private void Awake()
{
    _damagePool = new ObjectPool<DamageNumber>(
        createFunc: () => Instantiate(_damageNumberPrefab),
        actionOnGet: obj => obj.gameObject.SetActive(true),
        actionOnRelease: obj => obj.gameObject.SetActive(false),
        actionOnDestroy: obj => Destroy(obj.gameObject),
        defaultCapacity: 20,
        maxSize: 50
    );
}
```

### Event System
Use C# events or a lightweight event bus for decoupling:

```csharp
// Event definitions
public static class GameEvents
{
    public static event Action<CardInstance, Character> OnCardPlayed;
    public static event Action<Character, int> OnDamageDealt;
    public static event Action<Character> OnEnemyDefeated;
    public static event Action<int> OnGoldChanged;
    public static event Action OnTurnEnded;

    public static void CardPlayed(CardInstance card, Character target)
        => OnCardPlayed?.Invoke(card, target);

    public static void DamageDealt(Character target, int amount)
        => OnDamageDealt?.Invoke(target, amount);

    // Always unsubscribe in OnDisable/OnDestroy to prevent memory leaks
}
```

---

## 4. Anti-Patterns to Avoid

### ❌ Using `Find()` at runtime
```csharp
// ❌ Never do this — slow, fragile, breaks on rename
var player = GameObject.Find("Player");
var manager = FindObjectOfType<CombatManager>();

// ✅ Use serialized references or dependency injection
[SerializeField] private Player _player;
[SerializeField] private CombatManager _combatManager;
```

### ❌ Using `Resources.Load()` everywhere
```csharp
// ❌ Loads everything in Resources/ into memory at startup
var sprite = Resources.Load<Sprite>("Cards/Fireball");

// ✅ Use direct references via ScriptableObjects or Addressables
[SerializeField] private Sprite _fireballSprite;
```

### ❌ Heavy logic in `Update()`
```csharp
// ❌ Runs every frame unnecessarily
void Update()
{
    healthBar.fillAmount = currentHealth / maxHealth;  // Only changes when hit
}

// ✅ Update only when value changes
public void TakeDamage(int amount)
{
    _currentHealth -= amount;
    _healthBar.fillAmount = (float)_currentHealth / _maxHealth;
}
```

### ❌ String-based comparisons
```csharp
// ❌ Fragile, no compile-time checking
if (collision.gameObject.tag == "Enemy") { }
if (animator.GetCurrentAnimatorStateInfo(0).IsName("Idle")) { }

// ✅ Use CompareTag (faster) or constants
if (collision.gameObject.CompareTag("Enemy")) { }

// ✅ Or better yet, use component checks
if (collision.gameObject.TryGetComponent<Enemy>(out var enemy)) { }
```

### ❌ Allocating in hot paths
```csharp
// ❌ Creates garbage every frame
void Update()
{
    var enemies = FindObjectsOfType<Enemy>();  // Allocates array every frame
    var message = $"HP: {health}";             // String allocation every frame
}

// ✅ Cache and reuse
private readonly List<Enemy> _enemyCache = new();
private readonly StringBuilder _sb = new();
```

### ❌ Magic numbers in game logic
```csharp
// ❌ What does 5 mean? What does 3 mean?
DrawCards(5);
energy = 3;

// ✅ Use ScriptableObject values or named constants
DrawCards(_combatConfig.drawPerTurn);
energy = _combatConfig.baseEnergy;
```

---

## 5. Recommended Packages & Libraries

### Required
| Package | Purpose | Why |
|---------|---------|-----|
| **TextMeshPro** | Text rendering | Superior text quality; Unity standard for UI text |
| **Universal RP (URP)** | Render pipeline | Best balance of performance and quality for 2D games |
| **Unity UI (uGUI)** | UI system | Mature, well-documented, good for card game UI |
| **DOTween** | Tweening/animation | Industry standard for programmatic animations (card movement, UI transitions). Free version sufficient |
| **Newtonsoft.Json (com.unity.nuget.newtonsoft-json)** | JSON serialization | Robust save/load, better than Unity's JsonUtility for complex objects |

### Recommended
| Package | Purpose | Why |
|---------|---------|-----|
| **Addressables** | Asset management | Efficient loading for large content (many cards, enemies). Use if asset count exceeds ~200 |
| **Cinemachine** | Camera | Smooth camera transitions between scenes/areas |
| **Unity Localization** | i18n | Steam requires multi-language support for broader market |
| **Steamworks.NET** | Steam integration | C# wrapper for Steamworks SDK — achievements, cloud saves, stats |

### Do NOT Use
| Package | Reason |
|---------|--------|
| DOTS/ECS | Overkill for a card game; adds massive complexity |
| Mirror/Netcode | Single-player game; no networking needed |
| Odin Inspector | Paid; DOTween + custom editors are sufficient |
| Rewired | For complex input; Unity's Input System is fine for mouse/keyboard card game |

---

## 6. Configuration Best Practices

### Unity Project Settings
- **Scripting Backend**: IL2CPP (required for Steam builds, better performance)
- **API Compatibility Level**: .NET Standard 2.1
- **Color Space**: Linear (better visual quality)
- **Target Platform**: Standalone (Windows/Mac/Linux)
- **Aspect Ratio**: Support 16:9 (primary) and 16:10, with letterboxing for other ratios
- **Resolution**: Default 1920x1080, support down to 1280x720
- **VSync**: On by default, let player toggle
- **Target Frame Rate**: 60 FPS (card game doesn't need more)

### Unity Editor Settings
- **Asset Serialization**: Force Text (required for version control)
- **Version Control Mode**: Visible Meta Files
- **Editor script compilation**: Assembly Definitions for all script folders

### .gitignore (Unity Standard)
```
# Unity
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
*.csproj
*.sln
*.suo
*.tmp
*.user
*.userprefs
*.pidb
*.booproj
*.svd
*.pdb
*.mdb
*.opendb
*.VC.db
*.pidb.meta
*.pdb.meta
*.mdb.meta

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vs/
.vscode/

# Build
*.apk
*.aab
*.unitypackage
*.app

# Secrets
.env
*.keystore
```

### Version Control
- Use **Git LFS** for binary assets (textures, audio, fonts, prefabs):
```
# .gitattributes
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.wav filter=lfs diff=lfs merge=lfs -text
*.ogg filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.ttf filter=lfs diff=lfs merge=lfs -text
*.otf filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
*.fbx filter=lfs diff=lfs merge=lfs -text
*.asset filter=lfs diff=lfs merge=lfs -text
*.prefab filter=lfs diff=lfs merge=lfs -text
*.unity filter=lfs diff=lfs merge=lfs -text
*.controller filter=lfs diff=lfs merge=lfs -text
*.anim filter=lfs diff=lfs merge=lfs -text
*.mat filter=lfs diff=lfs merge=lfs -text
```

---

## 7. Testing Framework & Patterns

### Unity Test Framework (built-in)
Use the Unity Test Framework package with NUnit:

#### Edit Mode Tests (Unit Tests — 70%)
For pure logic with no MonoBehaviour dependencies:

```csharp
// Tests/EditMode/DeckManagerTests.cs
[TestFixture]
public class DeckManagerTests
{
    private DeckManager _deck;
    private CardData _testCard;

    [SetUp]
    public void SetUp()
    {
        _testCard = ScriptableObject.CreateInstance<CardData>();
        _testCard.cardName = "Test Strike";
        _testCard.energyCost = 1;

        _deck = new DeckManager();
        _deck.Initialize(new List<CardData> { _testCard, _testCard, _testCard });
    }

    [TearDown]
    public void TearDown()
    {
        Object.DestroyImmediate(_testCard);
    }

    [Test]
    public void DrawCard_RemovesFromDrawPile_AddsToHand()
    {
        // Arrange
        int initialCount = _deck.DrawPileCount;

        // Act
        var card = _deck.DrawCard();

        // Assert
        Assert.IsNotNull(card);
        Assert.AreEqual(initialCount - 1, _deck.DrawPileCount);
        Assert.AreEqual(1, _deck.HandCount);
    }

    [Test]
    public void DrawCard_EmptyDrawPile_ShufflesDiscardIntoDraw()
    {
        // Arrange — draw all cards then discard them
        while (_deck.DrawPileCount > 0)
        {
            var c = _deck.DrawCard();
            _deck.DiscardCard(c);
        }

        // Act
        var card = _deck.DrawCard();

        // Assert
        Assert.IsNotNull(card);
        Assert.AreEqual(2, _deck.DrawPileCount); // 3 total - 1 drawn = 2
    }
}
```

#### Play Mode Tests (Integration Tests — 20%)
For tests requiring MonoBehaviour lifecycle, coroutines, or scene loading:

```csharp
// Tests/PlayMode/CombatIntegrationTests.cs
[TestFixture]
public class CombatIntegrationTests
{
    [UnitySetUp]
    public IEnumerator SetUp()
    {
        yield return SceneManager.LoadSceneAsync("Combat", LoadSceneMode.Single);
        yield return null; // Wait one frame for Awake/Start
    }

    [UnityTest]
    public IEnumerator PlayCard_ReducesEnergyAndDamagesEnemy()
    {
        // Arrange
        var combat = Object.FindFirstObjectByType<CombatManager>();
        var initialEnergy = combat.CurrentEnergy;
        var enemy = combat.GetFirstEnemy();
        var initialHP = enemy.CurrentHealth;

        // Act
        combat.PlayCard(combat.Hand[0], enemy);
        yield return null; // Wait for effects to resolve

        // Assert
        Assert.Less(combat.CurrentEnergy, initialEnergy);
        Assert.Less(enemy.CurrentHealth, initialHP);
    }
}
```

### Test Coverage Targets
- **Card effects**: Test every card effect individually (deal damage, apply block, draw cards, apply status)
- **Deck operations**: Draw, discard, shuffle, exhaust, add, remove
- **Combat math**: Damage calculation with block, status effects, vulnerable/weak multipliers
- **Save/Load**: Round-trip serialization of full game state
- **Map generation**: Verify valid paths, node distribution, boss placement

### Testability Guidelines
- **Separate logic from MonoBehaviour**: Keep game rules in pure C# classes, use MonoBehaviours only for Unity lifecycle hooks and rendering
- **Inject dependencies**: Pass references via constructor or Init() method, don't use `FindObjectOfType` in logic classes
- **Make RNG injectable**: Use `System.Random` with seedable constructor for deterministic tests

```csharp
// ✅ Testable — RNG is injectable
public class DeckManager
{
    private readonly System.Random _rng;

    public DeckManager(int? seed = null)
    {
        _rng = seed.HasValue ? new System.Random(seed.Value) : new System.Random();
    }

    public void Shuffle()
    {
        // Fisher-Yates using _rng — deterministic in tests
    }
}
```

---

## 8. Build & Deployment (Steam)

### Build Pipeline
1. **Development Build**: `File > Build Settings > Development Build` checked, for debugging
2. **Release Build**: IL2CPP, compression enabled, development build unchecked
3. **Steam Upload**: Use Steamworks SDK `steamcmd` with build depot configuration

### Build Checklist
- [ ] IL2CPP scripting backend selected
- [ ] Development Build unchecked
- [ ] Strip Engine Code enabled
- [ ] Managed Stripping Level: Medium (High can break reflection-based code)
- [ ] Resolution and Presentation: Fullscreen Window by default
- [ ] Player Settings > Product Name and Company Name set
- [ ] Icon set (256x256 minimum)
- [ ] Splash screen configured (or removed with Unity Pro)

### Steam Integration Checklist
- [ ] Steamworks.NET initialized on boot
- [ ] App ID configured (via `steam_appid.txt` in build root for dev)
- [ ] Achievements defined and tracked
- [ ] Cloud Save enabled (map Steam Cloud to save directory)
- [ ] Steam Input API configured (or fallback to Unity Input System)
- [ ] Rich Presence set for current game state
- [ ] Stats tracking (runs completed, cards played, enemies defeated)
- [ ] `steam_appid.txt` in `.gitignore` (contains your actual app ID)

### Platform-Specific
- **Windows**: Primary target. Test on Windows 10 and 11. DirectX 11 minimum.
- **macOS**: Secondary. Test on Apple Silicon and Intel. Metal renderer.
- **Linux**: Tertiary. Test on Ubuntu/SteamOS. Vulkan renderer.

---

## 9. Security Considerations

### Save File Integrity
```csharp
// Prevent trivial save file editing (not full DRM, just integrity)
public static class SaveSecurity
{
    public static string ComputeChecksum(string jsonData, string salt)
    {
        using var sha = System.Security.Cryptography.SHA256.Create();
        var bytes = System.Text.Encoding.UTF8.GetBytes(jsonData + salt);
        var hash = sha.ComputeHash(bytes);
        return Convert.ToBase64String(hash);
    }
}
```

### General Security
- Never use `System.Reflection` to execute player-provided strings
- Validate all deserialized save data (null checks, range checks)
- Do not store Steam API keys in source code — use Steamworks SDK callbacks
- Sanitize player-entered text (character names) before displaying — prevent TextMeshPro rich text injection
- Keep `steam_appid.txt` out of version control
- Do not log Steam session tickets or auth tokens

---

## 10. Performance Patterns

### Card Game Specific
- **Card UI**: Pool card visual objects. A hand of 10 cards = 10 pooled GameObjects, not Instantiate/Destroy per draw
- **Sprite Atlases**: Pack related sprites (all card frames, all icons) into atlases to reduce draw calls
- **Canvas optimization**: Separate frequently-updating UI (energy counter, health bars) from static UI (backgrounds, frames) using multiple Canvases
- **Animation**: Use DOTween for card movement/scaling rather than Animator — lighter weight, easier to chain

### Memory
- **ScriptableObject sharing**: Never duplicate ScriptableObject data at runtime. Store a reference to the SO asset, create lightweight runtime instances for mutable state
- **Texture compression**: Use Crunch compression for textures. Target < 200MB total build size for a 2D card game
- **Audio**: Use Ogg Vorbis for music, WAV for short SFX. Stream long music files, preload short SFX

### Profiling
- Use Unity Profiler (`Window > Analysis > Profiler`) before optimizing
- Target: < 2ms frame time for game logic (card game should be well under budget)
- Watch for GC allocation spikes — avoid allocations in Update/LateUpdate
- Use `Profiler.BeginSample("name")` / `Profiler.EndSample()` for custom profiling sections

---

## 11. Deck-Builder Specific Patterns

### Card Effect System (Strategy Pattern)
```csharp
// Base effect interface
public interface ICardEffect
{
    void Execute(CombatContext context, Character source, Character target);
    string GetDescription(int value);
}

// Concrete effects
public class DamageEffect : ICardEffect
{
    public int baseDamage;

    public void Execute(CombatContext context, Character source, Character target)
    {
        int finalDamage = DamageCalculator.Calculate(baseDamage, source, target);
        target.TakeDamage(finalDamage);
    }

    public string GetDescription(int value) => $"Deal {value} damage";
}

public class BlockEffect : ICardEffect
{
    public int baseBlock;

    public void Execute(CombatContext context, Character source, Character target)
    {
        source.GainBlock(baseBlock);
    }

    public string GetDescription(int value) => $"Gain {value} block";
}

// Cards compose effects
[CreateAssetMenu]
public class CardData : ScriptableObject
{
    public List<CardEffectEntry> effects;  // Multiple effects per card
}

[System.Serializable]
public class CardEffectEntry
{
    public CardEffectType effectType;
    public int value;
    public TargetType target;
}
```

### Status Effect System
```csharp
public class StatusEffect
{
    public StatusType Type { get; }
    public int Stacks { get; set; }
    public int Duration { get; set; }  // -1 for permanent until removed

    public void OnTurnStart(Character character) { }
    public void OnTurnEnd(Character character) { }
    public float ModifyDamageDealt(float damage) => damage;
    public float ModifyDamageReceived(float damage) => damage;
}
```

### Save System Structure
```csharp
[System.Serializable]
public class SaveData
{
    public int saveVersion;
    public string characterId;
    public int currentHP;
    public int maxHP;
    public int gold;
    public int currentFloor;
    public List<string> deckCardIds;        // Reference card SOs by ID
    public List<string> relicIds;
    public List<int> visitedNodeIndices;
    public int seed;                         // For reproducible runs
    public string checksum;
}
```

---

## 12. Unity-Specific Prohibited Practices

### Strictly Prohibited
- `GameObject.Find()` or `FindObjectOfType()` in gameplay code (use serialized refs)
- `Resources.Load()` as primary asset loading strategy (use direct refs or Addressables)
- Logic in `Update()` that should be event-driven
- Public fields for Inspector values (use `[SerializeField] private`)
- Committing `Library/`, `Temp/`, `Obj/` folders
- Committing `.csproj` or `.sln` files (auto-generated by Unity)
- Using `DontDestroyOnLoad` on more than 2-3 root objects
- Nested coroutines more than 2 levels deep (use async/await or state machines)

### Discouraged
- `SendMessage()` / `BroadcastMessage()` — use direct method calls or events
- `Invoke("MethodName", delay)` with string — use coroutines or DOTween sequences
- Multiple singletons (limit to GameManager, AudioManager, SaveSystem max)
- Deep prefab nesting (3+ levels of nested prefabs)
- Putting all scripts in one folder without Assembly Definitions

---

## 13. Git Workflow for Unity

### Commit Conventions
Follow Conventional Commits with Unity-specific scopes:

```
feat(cards): add Fireball and Ice Shield card data
fix(combat): correct block calculation when vulnerable
refactor(ui): extract card tooltip into reusable component
art(sprites): add enemy sprite sheet for skeleton warrior
audio(sfx): add card play and draw sound effects
chore(unity): update URP to 14.0.11
test(deck): add shuffle and draw pile exhaustion tests
```

### Branch Strategy
- `main` — stable, buildable at all times
- `develop` — integration branch
- `feature/card-system` — feature branches
- `fix/combat-damage-calc` — bug fixes

### Scene Merge Conflicts
Unity scenes (`.unity`) and prefabs (`.prefab`) are YAML but merge poorly.
- **Rule**: Only one person edits a scene at a time
- Use **Smart Merge** (Unity's YAML merge tool) in `.gitconfig`:
```
[merge]
    tool = unityyamlmerge
[mergetool "unityyamlmerge"]
    cmd = '<Unity Editor Path>/Data/Tools/UnityYAMLMerge' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```

---

**Version**: v1.0.0
**Last updated**: 2026-04-01
