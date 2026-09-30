# Mobile Design Thinking

> Default mobile patterns worth questioning, and the questions that decide between them.

---

## 🚫 AI MOBILE DEFAULTS (FORBIDDEN LIST)

### Using These Patterns Automatically is FORBIDDEN!

The following patterns are "defaults" that AIs learned from training data.
Before using any of these, **QUESTION them and CONSIDER ALTERNATIVES!**

```
┌─────────────────────────────────────────────────────────────────┐
│                 🚫 AI MOBILE SAFE HARBOR                        │
│           (Default Patterns - Never Use Without Questioning)    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  NAVIGATION DEFAULTS:                                           │
│  ├── Tab bar for every project (Would drawer be better?)        │
│  ├── Fixed 5 tabs (Are 3 enough? For 6+, drawer?)               │
│  ├── "Home" tab on left (What does user behavior say?)          │
│  └── Hamburger menu (Is it outdated now?)                       │
│                                                                 │
│  STATE MANAGEMENT DEFAULTS:                                     │
│  ├── Redux everywhere (Is Zustand/Jotai sufficient?)            │
│  ├── Global state for everything (Isn't local state enough?)   │
│  ├── Context Provider hell (Is atom-based better?)              │
│  └── BLoC for every Flutter project (Is Riverpod more modern?)  │
│                                                                 │
│  LIST IMPLEMENTATION DEFAULTS:                                  │
│  ├── FlatList as default (Is FlashList more performant?)        │
│  ├── windowSize=21 (Is it really needed?)                       │
│  ├── removeClippedSubviews (Always?)                            │
│  └── ListView.builder (Is ListView.separated better?)           │
│                                                                 │
│  UI PATTERN DEFAULTS:                                           │
│  ├── FAB bottom-right (Is bottom-left more accessible?)         │
│  ├── Pull-to-refresh on every list (Is it needed everywhere?)   │
│  ├── Swipe-to-delete from left (Is right better?)               │
│  └── Bottom sheet for every modal (Is full screen better?)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔍 COMPONENT DECOMPOSITION (MANDATORY)

### Decomposition Analysis for Every Screen

Before designing any screen, perform this analysis:

```
SCREEN: [Screen Name]
├── PRIMARY ACTION: [What is the main action?]
│   └── Is it in thumb zone? [Yes/No → Why?]
│
├── TOUCH TARGETS: [All tappable elements]
│   ├── [Element 1]: [Size]pt → Sufficient?
│   ├── [Element 2]: [Size]pt → Sufficient?
│   └── Spacing: [Gap]pt → Accidental tap risk?
│
├── SCROLLABLE CONTENT:
│   ├── Is it a list? → FlatList/FlashList [Why this choice?]
│   ├── Item count: ~[N] → Performance consideration?
│   └── Fixed height? → Is getItemLayout needed?
│
├── STATE REQUIREMENTS:
│   ├── Is local state sufficient?
│   ├── Do I need to lift state?
│   └── Is global required? [Why?]
│
├── PLATFORM DIFFERENCES:
│   ├── iOS: [Anything different needed?]
│   └── Android: [Anything different needed?]
│
├── OFFLINE CONSIDERATION:
│   ├── Should this screen work offline?
│   └── Cache strategy: [Yes/No/Which one?]
│
└── PERFORMANCE IMPACT:
    ├── Any heavy components?
    ├── Is memoization needed?
    └── Animation performance?
```

---

## 🎯 PATTERN QUESTIONING MATRIX

Ask these questions for every default pattern:

### Navigation Pattern Questioning

| Assumption | Question | Alternative |
|------------|----------|-------------|
| "I'll use tab bar" | How many destinations? | 3 → minimal tabs, 6+ → drawer |
| "5 tabs" | Are all equally important? | "More" tab? Drawer hybrid? |
| "Bottom nav" | iPad/tablet support? | Navigation rail alternative |
| "Stack navigation" | Did I consider deep links? | URL structure = navigation structure |

### State Pattern Questioning

| Assumption | Question | Alternative |
|------------|----------|-------------|
| "I'll use Redux" | How complex is the app? | Simple: Zustand, Server: TanStack |
| "Global state" | Is this state really global? | Local lift, Context selector |
| "Context Provider" | Will re-render be an issue? | Zustand, Jotai (atom-based) |
| "BLoC pattern" | Is the boilerplate worth it? | Riverpod (less code) |

### List Pattern Questioning

| Assumption | Question | Alternative |
|------------|----------|-------------|
| "FlatList" | Is performance critical? | FlashList (faster) |
| "Standard renderItem" | Is it memoized? | useCallback + React.memo |
| "Index key" | Does data order change? | Use item.id |
| "ListView" | Are there separators? | ListView.separated |

### UI Pattern Questioning

| Assumption | Question | Alternative |
|------------|----------|-------------|
| "FAB bottom-right" | User handedness? | Accessibility settings |
| "Pull-to-refresh" | Does this list need refresh? | Only when necessary |
| "Modal bottom sheet" | How much content? | Full screen modal might be better |
| "Swipe actions" | Discoverability? | Visible button alternative |

---

## 📊 CONTEXT-BASED DECISION PROTOCOL

### Think Differently Based on Project Type

```
DETERMINE PROJECT TYPE:
        │
        ├── E-Commerce App
        │   ├── Navigation: Tab (Home, Search, Cart, Account)
        │   ├── Lists: Product grids (memoized, image optimized)
        │   ├── Performance: Image caching CRITICAL
        │   ├── Offline: Cart persistence, product cache
        │   └── Special: Checkout flow, payment security
        │
        ├── Social/Content App
        │   ├── Navigation: Tab (Feed, Search, Create, Notify, Profile)
        │   ├── Lists: Infinite scroll, complex items
        │   ├── Performance: Feed rendering CRITICAL
        │   ├── Offline: Feed cache, draft posts
        │   └── Special: Real-time updates, media handling
        │
        ├── Productivity/SaaS App
        │   ├── Navigation: Drawer or adaptive (mobile tab, tablet rail)
        │   ├── Lists: Data tables, forms
        │   ├── Performance: Data sync
        │   ├── Offline: Full offline editing
        │   └── Special: Conflict resolution, background sync
        │
        ├── Utility App
        │   ├── Navigation: Minimal (stack-only possible)
        │   ├── Lists: Probably minimal
        │   ├── Performance: Fast startup
        │   ├── Offline: Core feature offline
        │   └── Special: Widget, shortcuts
        │
        └── Media/Streaming App
            ├── Navigation: Tab (Home, Search, Library, Profile)
            ├── Lists: Horizontal carousels, vertical feeds
            ├── Performance: Preloading, buffering
            ├── Offline: Download management
            └── Special: Background playback, casting
```

---

## 🔄 INTERACTION BREAKDOWN

### Analysis for Every Gesture

Before adding any gesture:

```
GESTURE: [Gesture Type]
├── DISCOVERABILITY:
│   └── How will users discover this gesture?
│       ├── Is there a visual hint?
│       ├── Will it be shown in onboarding?
│       └── Is there a button alternative? (MANDATORY)
│
├── PLATFORM CONVENTION:
│   ├── What does this gesture mean on iOS?
│   ├── What does this gesture mean on Android?
│   └── Am I deviating from platform convention?
│
├── ACCESSIBILITY:
│   ├── Can motor-impaired users perform this gesture?
│   ├── Is there a VoiceOver/TalkBack alternative?
│   └── Does it work with switch control?
│
├── CONFLICT CHECK:
│   ├── Does it conflict with system gestures?
│   │   ├── iOS: Edge swipe back
│   │   ├── Android: Back gesture
│   │   └── Home indicator swipe
│   └── Is it consistent with other app gestures?
│
└── FEEDBACK:
    ├── Is haptic feedback defined?
    ├── Is visual feedback sufficient?
    └── Is audio feedback needed?
```

---

## 🎭 SPIRIT OVER CHECKLIST (Mobile Edition)

### Passing the Checklist is Not Enough!

| ❌ Self-Deception | ✅ Honest Assessment |
|-------------------|----------------------|
| "Touch target is 44px" (but on edge, unreachable) | "Can user reach it one-handed?" |
| "I used FlatList" (but didn't memoize) | "Is scroll smooth?" |
| "Platform-specific nav" (but only icons differ) | "Does iOS feel like iOS, Android like Android?" |
| "Offline support exists" (but error message is generic) | "What can user actually do offline?" |
| "Loading state exists" (but just a spinner) | "Does user know how long to wait?" |

> 🔴 **Passing the checklist is NOT the goal. Creating great mobile UX IS the goal.**

