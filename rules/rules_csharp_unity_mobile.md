# C# + Unity Mobile Coding Rules

> Framework-specific rules for Unity cross-platform mobile game development (iOS & Android), targeting board/strategy games with Korean localization.

---

## 1. Project Structure

```
Assets/
├── _Project/                  # All project-specific assets (prefixed to stay at top)
│   ├── Art/
│   │   ├── Sprites/           # 2D sprites, sprite atlases
│   │   │   ├── Board/         # Map board, route overlays, city markers
│   │   │   ├── Cards/         # Train car cards, destination tickets
│   │   │   ├── Trains/        # Train piece sprites per player color
│   │   │   └── UI/            # UI icons, buttons, backgrounds
│   │   ├── Animations/        # Animation clips and controllers
│   │   ├── Materials/
│   │   └── VFX/               # Particle systems (route claiming, scoring)
│   ├── Audio/
│   │   ├── Music/
│   │   ├── SFX/
│   │   └── Mixers/            # AudioMixer assets
│   ├── Data/
│   │   ├── Routes/            # ScriptableObject route definitions
│   │   ├── Cities/            # ScriptableObject city definitions
│   │   ├── DestinationTickets/# ScriptableObject destination ticket data
│   │   ├── BoardMaps/         # ScriptableObject board map configurations
│   │   └── GameConfig/        # ScriptableObject game settings (player counts, scoring)
│   ├── Prefabs/
│   │   ├── UI/
│   │   ├── Board/
│   │   ├── Cards/
│   │   ├── Trains/
│   │   └── Effects/
│   ├── Scenes/
│   │   ├── Boot.unity         # Initialization scene (splash, loading)
│   │   ├── MainMenu.unity     # Main menu (player count selection, settings)
│   │   ├── GameSetup.unity    # Player setup (names, colors)
│   │   ├── Game.unity         # Main game board scene
│   │   └── GameResult.unity   # End-game scoring and results
│   ├── Scripts/
│   │   ├── Core/              # Game manager, state machine, turn system
│   │   │   ├── GameManager.cs
│   │   │   ├── GameState.cs
│   │   │   ├── TurnManager.cs
│   │   │   ├── ScoreManager.cs
│   │   │   └── SceneLoader.cs
│   │   ├── Board/             # Board map, routes, cities
│   │   │   ├── BoardManager.cs
│   │   │   ├── RouteData.cs          # ScriptableObject
│   │   │   ├── CityData.cs           # ScriptableObject
│   │   │   ├── RouteSlot.cs          # Individual route segment
│   │   │   └── RouteClaimSystem.cs
│   │   ├── Cards/             # Train car cards, destination tickets
│   │   │   ├── TrainCardData.cs      # ScriptableObject (8 colors + locomotive)
│   │   │   ├── DestinationTicketData.cs # ScriptableObject
│   │   │   ├── CardDeck.cs
│   │   │   ├── CardHand.cs
│   │   │   └── FaceUpDisplay.cs      # 5 face-up cards management
│   │   ├── Players/           # Player data, scoring, train inventory
│   │   │   ├── Player.cs
│   │   │   ├── PlayerHand.cs
│   │   │   ├── TrainInventory.cs
│   │   │   └── DestinationTicketHolder.cs
│   │   ├── AI/                # AI opponents (optional)
│   │   │   ├── AIPlayer.cs
│   │   │   ├── AIStrategy.cs
│   │   │   └── RouteEvaluator.cs
│   │   ├── UI/                # All UI controllers and views
│   │   │   ├── Screens/              # Full-screen UI (menus, results)
│   │   │   ├── HUD/                  # In-game overlay (score, turn indicator)
│   │   │   ├── Cards/                # Card visual representation
│   │   │   ├── Popups/              # Dialogs (ticket selection, confirm)
│   │   │   ├── Touch/               # Touch input handlers, gestures
│   │   │   └── Common/              # Reusable UI components
│   │   ├── Input/             # Touch input, gestures, zoom/pan
│   │   │   ├── TouchInputManager.cs
│   │   │   ├── BoardPanZoom.cs
│   │   │   └── CardDragHandler.cs
│   │   ├── Localization/      # Korean string management helpers
│   │   ├── Audio/             # Audio manager, sound pooling
│   │   ├── Persistence/       # Save/load, player preferences
│   │   └── Utils/             # Extension methods, helpers
│   ├── Fonts/
│   │   ├── NotoSansKR/        # Korean font (Noto Sans KR or similar)
│   │   └── TMP_Fonts/         # TextMeshPro font assets generated from Korean fonts
│   ├── Localization/          # Unity Localization tables (ko, en fallback)
│   │   ├── StringTables/
│   │   └── AssetTables/
│   ├── Settings/              # URP settings, quality settings per platform
│   │   ├── URP_MobileHigh.asset
│   │   ├── URP_MobileLow.asset
│   │   └── QualitySettings/
│   └── StreamingAssets/       # External data files if needed
├── Plugins/
│   ├── Android/               # Android-specific native plugins
│   └── iOS/                   # iOS-specific native plugins
├── TextMesh Pro/              # TMP essentials
└── Resources/                 # Only for assets that MUST be loaded by name at runtime
                               # Keep this minimal — prefer direct references
```

### File Naming Conventions
- **Scripts**: `PascalCase.cs` matching the primary class name — `TurnManager.cs`
- **Scenes**: `PascalCase.unity` — `MainMenu.unity`, `Game.unity`
- **Prefabs**: `PascalCase.prefab` — `TrainCard.prefab`, `RouteSlot.prefab`
- **ScriptableObjects**: `PascalCase.asset` — `SeoulToBusan.asset`, `RedTrainCard.asset`
- **Sprites/Textures**: `snake_case.png` — `board_map_korea.png`, `icon_train_red.png`
- **Audio**: `snake_case.wav/.ogg` — `sfx_claim_route.wav`, `music_game_01.ogg`
- **Animations**: `PascalCase.anim` — `TrainPlace.anim`, `CardDraw.anim`
- **Materials**: `PascalCase.mat` — `RouteHighlight.mat`
- **Localization**: `snake_case` keys — `ui_main_menu`, `msg_your_turn`, `label_score`

### Assembly Definitions
Use Assembly Definition files (`.asmdef`) to organize code into modules:
```
Scripts/Core/       → Game.Core.asmdef
Scripts/Board/      → Game.Board.asmdef
Scripts/Cards/      → Game.Cards.asmdef
Scripts/Players/    → Game.Players.asmdef
Scripts/AI/         → Game.AI.asmdef
Scripts/UI/         → Game.UI.asmdef
Scripts/Input/      → Game.Input.asmdef
Scripts/Utils/      → Game.Utils.asmdef
Tests/EditMode/     → Game.Tests.EditMode.asmdef
Tests/PlayMode/     → Game.Tests.PlayMode.asmdef
```
This enforces dependency boundaries and speeds up compilation.

---

## 2. C# / Unity Naming Conventions

### General
- **Classes/Structs/Enums**: `PascalCase` — `TurnManager`, `CardColor`, `GamePhase`
- **Interfaces**: `IPascalCase` — `IClaimable`, `IScoreable`, `ITouchHandler`
- **Methods**: `PascalCase` — `ClaimRoute()`, `DrawCards()`, `CalculateScore()`
- **Properties**: `PascalCase` — `CurrentPlayer`, `RemainingTrains`, `IsGameOver`
- **Public fields**: `camelCase` (only when required by Unity serialization)
- **Private fields**: `_camelCase` — `_currentPlayer`, `_faceUpCards`, `_turnCount`
- **Constants**: `PascalCase` (C# convention) — `MaxPlayers`, `InitialTrainCount`, `LongestRouteBonus`
- **Static readonly**: `PascalCase` — `EmptyHand`, `DefaultConfig`
- **Enums**: `PascalCase` for type and members — `CardColor.Red`, `GamePhase.Playing`
- **Parameters**: `camelCase` — `int routeLength`, `Player targetPlayer`
- **Local variables**: `camelCase` — `var remainingTrains`, `var selectedCards`
- **Events/Delegates**: `PascalCase` with `On` prefix — `OnRouteClaimed`, `OnTurnChanged`
- **Namespaces**: `PascalCase`, matching folder structure — `Game.Board`, `Game.Cards`

### Unity-Specific
- **MonoBehaviour classes**: Name matches file name exactly
- **SerializeField**: Use `[SerializeField]` with private fields, not public fields
- **Tooltip**: Add `[Tooltip("...")]` for inspector-editable fields
- **Header/Space**: Use `[Header("Section")]` and `[Space]` to organize inspector fields

```csharp
// Good
public class TurnManager : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private PlayerHUD _playerHUD;
    [SerializeField] private FaceUpDisplay _faceUpDisplay;

    [Header("Settings")]
    [SerializeField, Tooltip("Number of destination tickets dealt at game start")]
    private int _initialTicketCount = 3;

    [SerializeField, Tooltip("Minimum tickets a player must keep")]
    private int _minimumTicketsToKeep = 2;

    private int _currentPlayerIndex;
    private readonly List<Player> _players = new();

    public Player CurrentPlayer => _players[_currentPlayerIndex];
    public bool IsLastRound { get; private set; }

    public event Action<Player> OnTurnChanged;
    public event Action OnLastRoundTriggered;
}
```

---

## 3. Unity Mobile-Specific Patterns

### Touch Input First Design
All interactions must be designed for touch input on mobile:

```csharp
// Board pan and zoom for mobile
public class BoardPanZoom : MonoBehaviour
{
    [SerializeField] private Camera _camera;
    [SerializeField] private float _zoomSpeed = 0.5f;
    [SerializeField] private float _minZoom = 3f;
    [SerializeField] private float _maxZoom = 10f;
    [SerializeField] private Vector2 _panLimitMin;
    [SerializeField] private Vector2 _panLimitMax;

    private Vector2 _lastPanPosition;
    private float _lastPinchDistance;
    private bool _isPanning;

    private void Update()
    {
        if (UnityEngine.Input.touchCount == 1)
            HandlePan();
        else if (UnityEngine.Input.touchCount == 2)
            HandlePinchZoom();
    }

    private void HandlePan()
    {
        var touch = UnityEngine.Input.GetTouch(0);
        if (touch.phase == TouchPhase.Began)
        {
            _lastPanPosition = touch.position;
            _isPanning = true;
        }
        else if (touch.phase == TouchPhase.Moved && _isPanning)
        {
            Vector2 delta = touch.position - _lastPanPosition;
            Vector3 move = _camera.ScreenToWorldPoint(Vector3.zero)
                         - _camera.ScreenToWorldPoint(new Vector3(delta.x, delta.y, 0));
            _camera.transform.position = ClampPosition(_camera.transform.position + move);
            _lastPanPosition = touch.position;
        }
    }

    private void HandlePinchZoom()
    {
        var touch0 = UnityEngine.Input.GetTouch(0);
        var touch1 = UnityEngine.Input.GetTouch(1);
        float currentDistance = Vector2.Distance(touch0.position, touch1.position);

        if (touch1.phase == TouchPhase.Began)
        {
            _lastPinchDistance = currentDistance;
            return;
        }

        float delta = _lastPinchDistance - currentDistance;
        _camera.orthographicSize = Mathf.Clamp(
            _camera.orthographicSize + delta * _zoomSpeed * Time.deltaTime,
            _minZoom, _maxZoom);
        _lastPinchDistance = currentDistance;
    }

    private Vector3 ClampPosition(Vector3 pos)
    {
        pos.x = Mathf.Clamp(pos.x, _panLimitMin.x, _panLimitMax.x);
        pos.y = Mathf.Clamp(pos.y, _panLimitMin.y, _panLimitMax.y);
        return pos;
    }
}
```

### ScriptableObject for Game Data
Use ScriptableObjects for all game data definitions:

```csharp
[CreateAssetMenu(fileName = "NewRoute", menuName = "Game/Route Data")]
public class RouteData : ScriptableObject
{
    [Header("Route Info")]
    public CityData cityA;
    public CityData cityB;
    public int length;             // 1-6 train cars needed
    public CardColor requiredColor; // Gray = any single color

    [Header("Scoring")]
    public int points;             // Based on length: 1→1, 2→2, 3→4, 4→7, 5→10, 6→15

    [Header("Double Route")]
    public bool isDoubleRoute;     // Two parallel routes between same cities
    public RouteData pairedRoute;  // Reference to the other route (null if single)
}

[CreateAssetMenu(fileName = "NewCity", menuName = "Game/City Data")]
public class CityData : ScriptableObject
{
    public string cityId;
    public string cityNameKey;      // Localization key for Korean name
    public Vector2 boardPosition;   // Position on the board map
}

[CreateAssetMenu(fileName = "NewTicket", menuName = "Game/Destination Ticket")]
public class DestinationTicketData : ScriptableObject
{
    public CityData startCity;
    public CityData endCity;
    public int pointValue;
}
```

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

**Limit singletons to:** GameManager, AudioManager.
**Do NOT make singletons for:** TurnManager, BoardManager, ScoreManager, UI controllers.
Use dependency injection or scene references for everything else.

### State Machine Pattern
Use for game flow:

```csharp
public enum GamePhase
{
    Setup,           // Dealing initial cards and tickets
    Playing,         // Main game loop (turns)
    LastRound,       // Triggered when a player has 0-2 trains left
    FinalScoring,    // Calculate destination tickets + longest route
    GameOver         // Display results
}

public enum TurnAction
{
    None,            // Waiting for player to choose action
    DrawingCards,    // Player is drawing train car cards
    ClaimingRoute,   // Player is selecting and claiming a route
    DrawingTickets   // Player is drawing destination tickets
}

public enum CardColor
{
    Red,
    Blue,
    Green,
    Yellow,
    Black,
    White,
    Orange,
    Purple,
    Locomotive       // Wild card
}
```

### Event System
Use C# events for decoupling:

```csharp
public static class GameEvents
{
    public static event Action<Player, RouteData> OnRouteClaimed;
    public static event Action<Player, int> OnScoreChanged;
    public static event Action<Player> OnTurnStarted;
    public static event Action<Player> OnTurnEnded;
    public static event Action<Player> OnLastRoundTriggered;
    public static event Action<Player, TrainCardData> OnCardDrawn;
    public static event Action<Player, DestinationTicketData> OnTicketKept;
    public static event Action<List<PlayerScore>> OnFinalScoresCalculated;

    public static void RouteClaimed(Player player, RouteData route)
        => OnRouteClaimed?.Invoke(player, route);

    public static void ScoreChanged(Player player, int newScore)
        => OnScoreChanged?.Invoke(player, newScore);

    // Always unsubscribe in OnDisable/OnDestroy to prevent memory leaks
}
```

---

## 4. Korean Localization

### Unity Localization Package
Use the official Unity Localization package (`com.unity.localization`) for all user-facing strings:

```csharp
// Use LocalizedString references in UI components
[SerializeField] private LocalizedString _yourTurnMessage;
[SerializeField] private LocalizedString _routeClaimedMessage;

// String tables organized by feature:
// - UI_MainMenu (메인 메뉴)
// - UI_Game (게임 화면)
// - UI_Cards (카드)
// - UI_Scoring (점수)
// - Messages (메시지)
```

### Korean Font Setup
- Use **Noto Sans KR** (Google Fonts, OFL license) as primary Korean font
- Generate TMP font atlas with Korean character sets (KS X 1001 covers 2,350 common Hangul)
- Set font atlas size to **4096x4096** for crisp text on high-DPI mobile screens
- Include fallback font chain: Noto Sans KR → system font

```csharp
// Font atlas generation settings for Korean:
// - Sampling Point Size: 48 (balances quality and atlas size)
// - Padding: 5
// - Atlas Resolution: 4096 x 4096
// - Character Set: Custom Range (AC00-D7A3 for Hangul Syllables + basic ASCII)
// - Render Mode: SDF (Signed Distance Field) for scalable text
```

### Localization Keys Convention
```
# Format: {category}_{screen}_{element}
ui_main_start_game = 게임 시작
ui_main_settings = 설정
ui_main_how_to_play = 게임 방법
ui_game_your_turn = {0}님의 차례입니다
ui_game_draw_cards = 카드 뽑기
ui_game_claim_route = 노선 점령
ui_game_draw_tickets = 목적지 카드 뽑기
ui_game_remaining_trains = 남은 기차: {0}
ui_score_route_points = 노선 점수
ui_score_ticket_complete = 목적지 완료 (+{0})
ui_score_ticket_failed = 목적지 미완료 (-{0})
ui_score_longest_route = 최장 노선 보너스
ui_result_winner = {0}님이 승리했습니다!
msg_last_round = 마지막 라운드입니다!
msg_cannot_claim = 이 노선을 점령할 수 없습니다
label_players = 플레이어 수
label_player_name = 플레이어 {0}
```

---

## 5. Mobile-Specific Anti-Patterns to Avoid

### ❌ Using `Find()` at runtime
```csharp
// ❌ Never do this — slow, fragile, breaks on rename
var player = GameObject.Find("Player");
var manager = FindObjectOfType<TurnManager>();

// ✅ Use serialized references or dependency injection
[SerializeField] private Player _player;
[SerializeField] private TurnManager _turnManager;
```

### ❌ Heavy logic in `Update()`
```csharp
// ❌ Runs every frame — wastes mobile battery
void Update()
{
    scoreText.text = $"점수: {currentScore}";  // Only changes on route claim
}

// ✅ Update only when value changes
public void OnScoreChanged(int newScore)
{
    _scoreText.text = string.Format(_scoreFormat, newScore);
}
```

### ❌ Ignoring safe area on mobile
```csharp
// ❌ UI overlaps notch/home indicator
// Just placing UI at screen edges

// ✅ Respect safe area
public class SafeAreaAdapter : MonoBehaviour
{
    private RectTransform _rectTransform;

    private void Awake()
    {
        _rectTransform = GetComponent<RectTransform>();
        ApplySafeArea();
    }

    private void ApplySafeArea()
    {
        var safeArea = Screen.safeArea;
        var anchorMin = safeArea.position;
        var anchorMax = safeArea.position + safeArea.size;
        anchorMin.x /= Screen.width;
        anchorMin.y /= Screen.height;
        anchorMax.x /= Screen.width;
        anchorMax.y /= Screen.height;
        _rectTransform.anchorMin = anchorMin;
        _rectTransform.anchorMax = anchorMax;
    }
}
```

### ❌ Large uncompressed textures
```csharp
// ❌ 4096x4096 uncompressed board texture = 64MB VRAM
// ❌ No sprite atlas = excessive draw calls

// ✅ Use ASTC compression (iOS & Android), max 2048x2048 per atlas
// ✅ Pack related sprites into atlases to reduce draw calls
// ✅ Use multiple smaller textures with tiling for the board map
```

### ❌ Allocating in hot paths
```csharp
// ❌ Creates garbage every frame
void Update()
{
    var message = $"점수: {score}";  // String allocation every frame
}

// ✅ Cache and reuse
private readonly StringBuilder _sb = new();
```

### ❌ Magic numbers in game logic
```csharp
// ❌ What does 45 mean? What does 10 mean?
player.trains = 45;
longestRouteBonus = 10;

// ✅ Use ScriptableObject values or named constants
player.trains = _gameConfig.initialTrainCount;  // 45
longestRouteBonus = _gameConfig.longestRouteBonus;  // 10
```

---

## 6. Recommended Packages & Libraries

### Required
| Package | Version | Purpose | Why |
|---------|---------|---------|-----|
| **TextMeshPro** | Built-in | Text rendering | Superior quality for Korean Hangul; SDF scaling |
| **Universal RP (URP)** | 17.x (Unity 6.3) | Render pipeline | Optimized for mobile 2D; battery efficient |
| **Unity UI (uGUI)** | Built-in | UI system | Mature, good touch support for card/board game UI |
| **DOTween** | 1.2.x | Tweening/animation | Industry standard for smooth animations (card draw, train placement, scoring) |
| **Newtonsoft.Json** | `com.unity.nuget.newtonsoft-json` | JSON serialization | Robust save/load for game state |
| **Unity Localization** | 1.5.x | i18n | Korean string tables, font management, future expansion |

### Recommended
| Package | Purpose | Why |
|---------|---------|-----|
| **Addressables** | Asset management | Efficient loading on mobile (memory constrained) |
| **Unity Advertisements** | Monetization | If free-to-play model is used |
| **Unity In-App Purchasing** | IAP | For additional map packs or content |
| **Firebase Analytics** | Analytics | Cross-platform analytics for iOS & Android |

### Do NOT Use
| Package | Reason |
|---------|--------|
| DOTS/ECS | Overkill for a turn-based board game |
| Mirror/Netcode for GameObjects | Local multiplayer only; no networking needed for pass-and-play |
| Rewired | Unity Input System + touch handling is sufficient |
| Odin Inspector | Paid; not needed for this scope |
| DOTS Physics | 2D board game has no physics requirements |

---

## 7. Configuration Best Practices

### Unity Project Settings (Mobile)
- **Scripting Backend**: IL2CPP (required for iOS, recommended for Android)
- **API Compatibility Level**: .NET Standard 2.1
- **Color Space**: Linear (better visual quality)
- **Target Platforms**: iOS (minimum iOS 15.0) and Android (minimum API level 26 / Android 8.0)
- **Orientation**: Landscape Left + Landscape Right (board game works best in landscape)
- **Resolution Scaling**: Use adaptive resolution with `Screen.SetResolution()`
- **Target Frame Rate**: 30 FPS default (board game doesn't need 60; saves battery)
  - Allow 60 FPS toggle in settings for high-end devices
- **VSync**: Off on mobile (use `Application.targetFrameRate` instead)
- **Graphics API**: 
  - iOS: Metal
  - Android: Vulkan (primary), OpenGL ES 3.0 (fallback)

### Build Profiles (Unity 6.3)
Use Unity 6.3's Build Profiles feature to manage platform-specific settings:
```
Build Profiles/
├── iOS_Debug.buildprofile
├── iOS_Release.buildprofile
├── Android_Debug.buildprofile
└── Android_Release.buildprofile
```

### Quality Settings
Define at least two quality tiers for mobile:
- **Low**: For older devices. Reduce sprite resolution, disable particles, simpler shaders
- **High**: For modern devices. Full resolution sprites, particles, post-processing

### .gitignore (Unity Mobile)
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
*.ipa
*.unitypackage
*.app

# Secrets
.env
*.keystore
*.p12
*.mobileprovision
*.provisionprofile
google-services.json
GoogleService-Info.plist

# Gradle (Android)
ExportedProject/
launcherTemplate.gradle.bak
```

### Version Control
- Use **Git LFS** for binary assets:
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
*.asset filter=lfs diff=lfs merge=lfs -text
*.prefab filter=lfs diff=lfs merge=lfs -text
*.unity filter=lfs diff=lfs merge=lfs -text
*.controller filter=lfs diff=lfs merge=lfs -text
*.anim filter=lfs diff=lfs merge=lfs -text
*.mat filter=lfs diff=lfs merge=lfs -text
```

---

## 8. Testing Framework & Patterns

### Unity Test Framework (built-in)
Use the Unity Test Framework package with NUnit:

#### Edit Mode Tests (Unit Tests — 70%)
For pure logic with no MonoBehaviour dependencies:

```csharp
// Tests/EditMode/RouteClaimTests.cs
[TestFixture]
public class RouteClaimTests
{
    private RouteData _testRoute;
    private Player _testPlayer;

    [SetUp]
    public void SetUp()
    {
        _testRoute = ScriptableObject.CreateInstance<RouteData>();
        _testRoute.length = 3;
        _testRoute.requiredColor = CardColor.Red;
        _testRoute.points = 4;

        _testPlayer = new Player("테스트", PlayerColor.Red, 45);
    }

    [TearDown]
    public void TearDown()
    {
        Object.DestroyImmediate(_testRoute);
    }

    [Test]
    public void ClaimRoute_WithMatchingCards_ReducesTrainsAndScoresPoints()
    {
        // Arrange
        _testPlayer.AddCards(CardColor.Red, 3);
        int initialTrains = _testPlayer.RemainingTrains;

        // Act
        bool claimed = _testPlayer.TryClaimRoute(_testRoute);

        // Assert
        Assert.IsTrue(claimed);
        Assert.AreEqual(initialTrains - 3, _testPlayer.RemainingTrains);
        Assert.AreEqual(4, _testPlayer.Score);
    }

    [Test]
    public void ClaimRoute_WithLocomotives_AllowsWildSubstitution()
    {
        // Arrange
        _testPlayer.AddCards(CardColor.Red, 1);
        _testPlayer.AddCards(CardColor.Locomotive, 2);

        // Act
        bool claimed = _testPlayer.TryClaimRoute(_testRoute);

        // Assert
        Assert.IsTrue(claimed);
    }

    [Test]
    public void ClaimRoute_InsufficientCards_ReturnsFalse()
    {
        // Arrange
        _testPlayer.AddCards(CardColor.Red, 1);

        // Act
        bool claimed = _testPlayer.TryClaimRoute(_testRoute);

        // Assert
        Assert.IsFalse(claimed);
        Assert.AreEqual(45, _testPlayer.RemainingTrains);
    }
}
```

#### Play Mode Tests (Integration Tests — 20%)
For tests requiring MonoBehaviour lifecycle or scene loading:

```csharp
// Tests/PlayMode/GameFlowTests.cs
[TestFixture]
public class GameFlowTests
{
    [UnitySetUp]
    public IEnumerator SetUp()
    {
        yield return SceneManager.LoadSceneAsync("Game", LoadSceneMode.Single);
        yield return null;
    }

    [UnityTest]
    public IEnumerator EndGame_TriggeredWhenPlayerHasTwoOrFewerTrains()
    {
        // Arrange
        var turnManager = Object.FindFirstObjectByType<TurnManager>();
        var player = turnManager.CurrentPlayer;
        player.SetRemainingTrains(2);  // Test helper

        // Act
        turnManager.EndTurn();
        yield return null;

        // Assert
        Assert.AreEqual(GamePhase.LastRound, GameManager.Instance.CurrentPhase);
    }
}
```

### Test Coverage Targets
- **Route claiming**: All card color combinations, locomotive substitution, insufficient cards, double routes
- **Scoring**: Route points by length (1→1, 2→2, 3→4, 4→7, 5→10, 6→15), destination ticket completion/failure, longest route calculation
- **Card drawing**: Face-up card replacement, locomotive draw restriction (only 1 card if locomotive), 3-locomotive reset
- **Destination tickets**: Initial deal (keep ≥2), mid-game draw (keep ≥1), path connectivity check
- **Turn management**: Turn rotation, last round trigger (0-2 trains), final scoring
- **Graph algorithms**: Shortest path for ticket completion check, longest continuous path calculation

### Testability Guidelines
- **Separate logic from MonoBehaviour**: Keep game rules in pure C# classes
- **Inject dependencies**: Pass references via constructor or Init() method
- **Make RNG injectable**: Seedable random for deterministic shuffling in tests

---

## 9. Build & Deployment (Mobile)

### iOS Build
- **Minimum iOS Version**: 15.0
- **Xcode**: Latest stable (Xcode 16.x)
- **Signing**: Use automatic signing during development, manual for distribution
- **App Store**: Use Xcode Organizer or Transporter for upload
- **Bitcode**: Disabled (Unity does not support Bitcode)
- **Architecture**: arm64 only (32-bit devices no longer supported)

### Android Build
- **Minimum API Level**: 26 (Android 8.0)
- **Target API Level**: 35 (latest required by Google Play)
- **Build Format**: AAB (Android App Bundle) for Google Play, APK for testing
- **Keystore**: Store signing keystore outside of repo, reference via environment variable
- **Split APKs**: Enable for smaller download size per device

### Build Checklist
- [ ] IL2CPP scripting backend selected (both platforms)
- [ ] Development Build unchecked for release
- [ ] Managed Stripping Level: Medium
- [ ] Orientation locked to Landscape
- [ ] App icons set for all required sizes (iOS + Android)
- [ ] Splash screen configured
- [ ] Safe area handling tested on notched devices
- [ ] Korean font renders correctly at all UI sizes
- [ ] Touch input responsive on both phones and tablets
- [ ] Memory usage < 300MB on target minimum devices
- [ ] App size < 150MB (initial download)
- [ ] Battery usage acceptable (30 FPS target)

### Platform Testing Matrix
| Device Category | iOS | Android |
|----------------|-----|---------|
| Phone (small) | iPhone SE 3rd gen | Galaxy A series |
| Phone (large) | iPhone 15/16 | Galaxy S24/Pixel 9 |
| Tablet | iPad (10th gen) | Galaxy Tab S9 |
| Older device | iPhone 11 | Galaxy S10 |

---

## 10. Security Considerations

### Save Data Integrity
```csharp
// Prevent trivial save file editing
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

### General Mobile Security
- Never store sensitive data in `PlayerPrefs` (plaintext on device)
- Validate all deserialized save data (null checks, range checks)
- Do not log game state details in production builds
- Sanitize player-entered text (player names) before displaying — prevent TMP rich text injection
- Keep signing keystores and provisioning profiles out of version control
- Do not include debug/cheat menus in release builds
- Use `Application.genuine` check on Android for tamper detection

### Privacy
- Declare camera/microphone permissions only if used
- Include privacy policy URL in app store listings
- GDPR/CCPA compliance if collecting analytics
- Do not collect personal data without consent

---

## 11. Performance Patterns (Mobile)

### Board Game Specific
- **Board map**: Use a single high-quality 2D sprite or tilemap for the board. Pre-render route slots as part of the board texture where possible; use overlay sprites only for interactive elements
- **Card UI**: Pool card visual objects. Maximum 110 train cards + 30 destination tickets — pool the visual representation, not the data
- **Sprite Atlases**: Pack related sprites (all card faces, all train colors, UI elements) into atlases to reduce draw calls. Target < 5 draw calls for the board + < 10 for UI
- **Canvas optimization**: Separate dynamic UI (score counters, turn indicator, card hand) from static UI (board background, city labels) using multiple Canvases
- **Animation**: Use DOTween for card movement/train placement rather than Animator — lighter weight for mobile

### Memory (Mobile-Critical)
- **Target memory budget**: < 300MB total on mobile
- **Texture compression**: Use ASTC (both iOS and Android). Target < 80MB for all textures
- **Sprite atlas max size**: 2048x2048 per atlas on mobile
- **Audio**: Use Ogg Vorbis for music (stream, don't preload), WAV for short SFX
- **ScriptableObject sharing**: Never duplicate SO data at runtime. Reference the asset, create lightweight instances for mutable state
- **Unload unused assets**: Call `Resources.UnloadUnusedAssets()` on scene transitions

### Battery Optimization
- **30 FPS default**: Board games don't need 60 FPS. Use `Application.targetFrameRate = 30`
- **Reduce GPU work when idle**: Lower rendering quality during opponent's turn or when player is reading cards
- **Avoid continuous Update loops**: Use event-driven updates. A board game has long idle periods — don't poll
- **Screen dimming**: Do not prevent screen from sleeping (unless mid-turn timer is active)

### Profiling
- Use Unity Profiler connected to device via USB
- Test on minimum spec devices (iPhone 11, Galaxy A series)
- Watch for GC allocation spikes — avoid allocations in Update/LateUpdate
- Monitor thermal throttling on long game sessions
- Target: < 5ms frame time for game logic at 30 FPS (33ms budget per frame)

---

## 12. Ticket to Ride Game Constants

### Route Scoring Table
```csharp
public static class ScoringTable
{
    // Route length → points
    private static readonly Dictionary<int, int> RoutePoints = new()
    {
        { 1, 1 },
        { 2, 2 },
        { 3, 4 },
        { 4, 7 },
        { 5, 10 },
        { 6, 15 }
    };

    public const int LongestRouteBonus = 10;
    public const int InitialTrainCount = 45; // per player
    public const int InitialHandSize = 4;    // train car cards
    public const int InitialTicketDeal = 3;  // destination tickets
    public const int MinTicketsToKeepInitial = 2;
    public const int MidGameTicketDraw = 3;
    public const int MinTicketsToKeepMidGame = 1;
    public const int FaceUpCardCount = 5;
    public const int MaxLocomotivesInFaceUp = 2; // 3+ triggers reset
    public const int LastRoundTrainThreshold = 2; // 0-2 trains triggers last round

    public static int GetRoutePoints(int length) => RoutePoints[length];
}
```

### Player Configuration
```csharp
public static class PlayerConfig
{
    public const int MinPlayers = 2;
    public const int MaxPlayers = 5;

    // Player colors matching train piece colors
    public enum PlayerColor
    {
        Red,
        Blue,
        Green,
        Yellow,
        Black
    }
}
```

### Card Distribution
```csharp
// Standard deck: 110 train car cards
// 12 of each color (8 colors × 12 = 96) + 14 locomotives
public static class CardDistribution
{
    public const int CardsPerColor = 12;
    public const int LocomotiveCount = 14;
    public const int TotalTrainCards = 110; // 96 + 14
    public const int TotalDestinationTickets = 30;
}
```

---

## 13. Unity Mobile Prohibited Practices

### Strictly Prohibited
- `GameObject.Find()` or `FindObjectOfType()` in gameplay code (use serialized refs)
- `Resources.Load()` as primary asset loading strategy (use direct refs or Addressables)
- Logic in `Update()` that should be event-driven (wastes battery on mobile)
- Public fields for Inspector values (use `[SerializeField] private`)
- Committing `Library/`, `Temp/`, `Obj/` folders
- Committing `.csproj` or `.sln` files (auto-generated by Unity)
- Using `DontDestroyOnLoad` on more than 2-3 root objects
- Uncompressed textures larger than 2048x2048 on mobile
- Storing secrets (API keys, signing passwords) in source code
- Ignoring safe area / screen notch on UI layout
- Using `System.Threading.Thread` directly (use Unity Jobs or coroutines)
- Hardcoded Korean strings in code (use localization system)

### Discouraged
- `SendMessage()` / `BroadcastMessage()` — use direct method calls or events
- `Invoke("MethodName", delay)` with string — use coroutines or DOTween sequences
- Multiple singletons (limit to GameManager, AudioManager max)
- Deep prefab nesting (3+ levels of nested prefabs)
- Putting all scripts in one folder without Assembly Definitions
- 60 FPS target without explicit user toggle (wastes battery)
- Synchronous asset loading that blocks the main thread
- Large JSON deserialization on the main thread (use async or background)

---

## 14. Git Workflow

### Commit Conventions
Follow Conventional Commits with game-specific scopes:

```
feat(board): add route claiming logic with card validation
feat(cards): implement face-up card display with locomotive reset
feat(scoring): add destination ticket completion check using BFS
feat(i18n): add Korean string table for main menu
fix(touch): correct pinch zoom sensitivity on Android tablets
refactor(ui): extract card hand layout into reusable component
art(sprites): add Korean city map board texture
audio(sfx): add train placement and card draw sounds
chore(unity): update URP to 17.0.x
test(routes): add scoring table and locomotive substitution tests
```

### Branch Strategy
- `main` — stable, buildable at all times
- `develop` — integration branch
- `feature/route-claiming` — feature branches
- `fix/touch-input-tablet` — bug fixes
- `release/1.0.0` — release preparation

---

**Version**: v1.0.0
**Last updated**: 2026-04-05
