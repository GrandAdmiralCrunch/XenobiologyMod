# Xenobiology: Modder's Guide (v0.1)

Xenobiology adds living, animated wildlife to planets. It also adds fossils that scientists can study, and a Field Guide where each world's tree of life fills in as players gather evidence. Everything is set up in `.cfg` files, so a planet pack can add a full ecosystem without writing any C#.

Put your content anywhere in GameData. Worlds that aren't installed are skipped quietly, so you can ship the configs without conditions. ModuleManager patches work on every node.

```
GameData/YourPlanetPack/Xenobiology/MyWorld.cfg
```

Check your work with the bundled tool. It catches broken links and thresholds that can never be reached:

```
python Xenobiology/Tools/xeno_tool.py validate GameData
python Xenobiology/Tools/xeno_tool.py tree     GameData my_biosphere
python Xenobiology/Tools/xeno_tool.py outlines GameData          # draws field-guide silhouettes
```

In game, press **Alt+F8** to open the debug window. It lists any config problems, shows which species can live where you're standing, and lets you spawn any creature or fossil.

---

## The node types

```
XENO_BIOSPHERE   one per world: "this body has life"
XENO_CLADE       a branch of that world's tree of life (parent → child)
XENO_LIFEFORM    a species: a leaf on the tree that spawns and moves
XENO_FOSSIL      an outcrop scientists study; adds evidence toward clades or panspermia
XENO_PANSPERMIA  links a clade on one world to the root of another world's tree
XENO_LAIR        a fixed home (cave, nest...) placed on the surface for a unique resident
XENO_FEATURE     scenery that isn't alive: geysers and fumaroles that species can gather around
```

### XENO_BIOSPHERE
| key | default | meaning |
|---|---|---|
| `name` | required | unique id |
| `body` | required | CelestialBody name (Kopernicus names work) |
| `displayName` | "<body> Biosphere" | |
| `rootClade` | first clade with no parent | the base of the tree |
| `spawnDensity` | 1 | multiplies the population cap on this world |
| `extinct` | false | true = fossils only; nothing spawns alive |
| `microbeClade` | | catch-all clade for this world's microbes that no clade claims (Microbiology Expansion) |
| `description` | | shown in the field guide |

### XENO_CLADE
| key | default | meaning |
|---|---|---|
| `name`, `biosphere` | required | |
| `parent` | (none = root) | must be in the **same** biosphere; use panspermia for links between worlds |
| `displayName`, `rank`, `era`, `description` | | `rank` is free text: Domain, Phylum, Order… |
| `revealThreshold` | 2 | evidence needed before the branch is named |
| `color` | 0.6,0.8,0.6,1 | node colour in the tree view |
| `grouping` | false | not a real clade: unrelated lineages that share a world (e.g. Laythe's animals and fungi). Drawn with dotted links and "no common ancestor" |
| `microbes` | | comma list of exact MICROBE names (Microbiology Expansion) shown as leaves here |
| `microbeCategories` | | e.g. `Bacteria, Archaea`: this world's unplaced microbes of these categories land on the deepest matching clade |

**How branches are revealed.** A clade's evidence is the number of discovered species anywhere below it, plus the `evidence` points of every studied fossil type that names it (or a clade below it) in `evidenceFor`. A lab analysis adds 1 more for that species or fossil type. With any evidence at all, the branch appears as *"Unknown lineage"*. Once evidence reaches `revealThreshold`, the branch is named. A named clade also shows a "? N undescribed" leaf for species that haven't been found yet.

### XENO_LIFEFORM
| key | default | meaning |
|---|---|---|
| `name`, `body`, `clade` | required | |
| `displayName`, `scientificName`, `description` | | |
| `silhouette` | | texture path without extension, e.g. `MyMod/Textures/beast` |
| `portrait` | | optional picture shown in the field guide once the species is discovered |
| `habitat` | Ground | `Ground`, `Water` (swims at the surface), `Underwater`, `Air`, `Flyer` (walks, takes off, glides, lands) |
| `biomes` | any | comma list; spaces and case are ignored (`Ice Caps` = `icecaps`) |
| `activeTime` | Any | `Any`, `Day`, `Night`; checked when the creature spawns |
| `temperament` | Skittish | `Skittish` flees · `Passive` barely reacts · `Curious` approaches · `Territorial` approaches and holds its ground |
| `groupSize` | 1 | `min, max`. Followers stay in formation around a leader |
| `rarity` | 1 | spawn weight against other species that can live in the same spot |
| `territoryChance` | 0.6 | chance that a given ~3 km "territory" holds this species at all. Lower values make the species patchier |
| `size` | 1 | the creature's length in metres. Used for spacing, water depth and the field guide. It also scales `PROCEDURAL` bodies; `MODEL`s are used at their authored size × `scale` |
| `speed`, `fleeSpeed` | 2, 6 | m/s |
| `alertDistance`, `fleeDistance` | 60, 30 | metres from the nearest vessel or kerbal |
| `observeRange` | 40 | how close a kerbal must be to observe it |
| `minAltitude`, `maxAltitude` | 10, 80 | Air: height above ground or sea. Underwater: depth range below the surface. On a gas giant (no terrain, no ocean) they are absolute altitudes, e.g. 120000–175000 on Jool; creatures appear only round vessels flying inside the band and start near the vessel's altitude |
| `scienceValue` | 10 | base science for observing it, per biome |
| `sessile` | false | never moves (corals, fungi, floating mats). Implied by a `BURST` block |
| `seafloor` | false | Underwater: lives on the seabed; `minAltitude` = height above the bottom |
| `amphibious` | false | Ground: also walks into the sea and along the seabed |
| `walkOnWater` | false | Ground: runs across the water surface |
| `swims` | false | Ground/Flyer: over water deeper than `waterline` it floats and paddles at the surface (waterfowl, penguins, capybaras). Flyers may also land on water and take off from it |
| `swimSpeed` | = speed | m/s while paddling; a fleeing swimmer manages 1.6× this |
| `waterline` | 15% of size | Water: depth of the creature's centre below the surface. With `swims`: depth of the model origin (the feet) below the surface, default 30% of size |
| `groupSpread` | 2.5 × size | metres between group members; small values give dense schools. Groups of 8+ count ¼ each against the spawn cap |
| `circling` | true | Air: lazy circles while wandering. `false` = long, nearly straight drifts with the wind |
| `turnRate` | 0 (default rates) | deg/s; very slow values make huge drifters turn majestically |
| `maxClimbRate` | 0 (no cap) | m/s cap on height changes, so giant floaters drift sideways instead of bobbing up and down |
| `cruiseChangeTime` | 5, 15 | Air: seconds between picking a new cruising height |
| `diet` | | comma list of lifeform names, MICROBE names or plain text, shown as "Feeds on" (unknown organisms stay anonymous until discovered) |
| `lifeStageOf`, `lifeStage` | | marks a larva/juvenile form of another lifeform, e.g. `lifeStageOf = laythe_screwtail`, `lifeStage = Larva`; both pages link to each other |

Then add **one** look node:

```
PROCEDURAL                  // built from primitives and animated in code; no art needed
{
    bodyPlan = Quadruped     // Quadruped, Hexapod, Serpent, Avian, Fish, Floater, Blob
    color = r,g,b,a
    accentColor = r,g,b,a
    glowColor = r,g,b,a      // optional emissive (eyes, bells, abdomens)
    bodyLength = 1   bodyWidth = 0.45   legLength = 0.5   headSize = 0.3
    tailLength = 0.5 wingSpan = 2       segments = 8      eyes = 2
}

MODEL                       // your own .mu (or other GameDatabase model) with legacy Animation clips
{
    path = MyMod/Models/beast          // without extension
    scale = 1
    rotationOffset = 0,0,0             // the creature must face +Z and stand on its feet at y = 0
    positionOffset = 0,0,0
    idleAnim = idle
    moveAnim = walk
    fleeAnim = run                     // defaults to moveAnim
    alertAnim = look                   // defaults to idleAnim
    moveAnimSpeed = 1.2                // m/s at which the walk clip plays at 1x (prevents foot sliding)
    fleeAnimSpeed = 3.5                // same for the flee clip; 0 = always play at 1x
}
```
If a `MODEL` can't be loaded, the creature falls back to its `PROCEDURAL` body, so it's good practice to give both.

`MODEL` can also name clips for the optional behaviours below: `sleepAnim`, `glideAnim`, `takeoffAnim`, `landAnim` and `attackAnim`. Take-off, landing and attack clips play once and are stretched to the matching duration.

Flyers can add `flapAnim`, played instead of `glideAnim` while climbing, fleeing or alarmed in the air. Swimmers can add `swimAnim` (paddling, scaled by `swimAnimSpeed` m/s) and `floatAnim` (resting on the water; defaults to `swimAnim`); they replace the walk/run/idle/alert clips while the creature is on the water.

**Flocks of Flyers** (`groupSize` > 1) take off a moment after their leader and fly in a loose V behind it, matching its height, and come down when it lands. Ducks lift off a lake together and land together.

#### Ocean-world behaviour blocks
```
LIGHT  { range = 300  aggroTime = 25  chaseSpeed = 11  darkOnly = true  darkDepth = 40 }
    // provoked by lit vessels (any ModuleLight switched on) and kerbal helmet lamps within range, while it is dark
    // where the creature is (night, or deeper than darkDepth). It hunts the light down and uses its ATTACK
    // (set onlyWhenProvoked = true so it only attacks then). Turn your lights off and it loses interest after aggroTime.
    // Without an ATTACK it just circles the light (duskmoths). Optional `message = ...` replaces the warning text.
LEAP   { height = 3  length = 14  duration = 1.6  chance = 0.2  whenFleeing = true  cooldown = 5 }
    // Water/Underwater swimmers jump clear of the surface in a ballistic arc, with splashes; `leapAnim` in MODEL.
    // Ground creatures hop over the terrain instead (springhoppers)
BURST  { triggerRange = 1.4  duration = 0.8  regrowTime = 600  message = ... }
    // sessile organisms that burst when something comes close (plays `burstAnim`, fires Burst emitters,
    // nearby ones of the same species are primed), then stay hidden until they regrow
EMITTER { kind = Bubbles  when = Always  offset = 0,0.1,0  rate = 14  burst = 0  lifetime = 5  speed = 0.15
          size = 0.2  sizeGrow = 1.4  radius = 0.7  gravity = -0.02  color = r,g,b,a  colorEnd = r,g,b,a
          transform =   underwaterOnly = false  surfaceOnly = false }
    // any number of particle effects. kind: Bubbles, Spores, Motes (additive glow), Splash, Steam.
    // when: Always, Idle, Moving, Fleeing, Night, Provoked, Leap, Burst (Leap/Burst use `burst` = particles at once)
    // kind = Smoke: billowing, lobed puffs from a narrow upward cone, slowly tumbling, with turbulence; they swell
    // to `sizeGrow` and thin out. Use it with a PLUME for vents, fumaroles and chimneys.
PLUME   { offset = 0,3.5,0  height = 15  radius = 0.22  spread = 2.8  rise = 0.9  lean = 0.12  sheets = 3
          color = r,g,b,a  colorTop = r,g,b,a }
    // a continuous, fake-volumetric smoke column (Source/VentPlume.cs). A few vertical sheets turn about the column
    // axis to face the camera, each carrying tileable turbulence that scrolls upward at its own speed. It widens
    // from `radius` to `spread`, bends downstream by `lean` x height and fades out toward the top. A few quads,
    // hidden with the creature's LOD. Example: the Smoker Tubeworms' black smoker.
```

#### Giants seen from afar
| key | default | meaning |
|---|---|---|
| `spawnDistance` | | `min, max` metres. The species is left out of the normal 150–1200 m ring and instead appears this far out, one at a time, so it can be seen coming |
| `despawnDistance` | global | per-species despawn range (raised automatically to at least `spawnDistance` max + 1500) |
| `farSpawnChance` | 0.05 | chance per 20-second check while none is around (times the density setting) |
| `farSpawnMessage` | | screen message on appearing; distance and compass bearing are appended |
| `maxWadeDepth` | 0 | `amphibious` walkers turn back from water deeper than this (0 = any depth) |

A wild creature with a `ROAR` block now rears up and bellows at anything inside `range` (using `roarAnim` and the `roar` sound), and wildlife within `scareRadius` flees. Before this, only lair residents roared.

`SOUNDS` also takes `pitch` (1 = normal; 0.45 makes the Sky Leviathan's song deep and slow).

#### METAMORPHOSIS (a larva changing into its next stage)
```
METAMORPHOSIS { into = laythe_skyleviathan_pupa  chance = 0.02  watchRange = 1500  swellTime = 15  swellScale = 2.5  riseSpeed = 4  message = ... }
```
While a vessel is within `watchRange`, each individual has `chance` per minute to start. It swells to `swellScale` over `swellTime` seconds, floats up at `riseSpeed`, and at the surface is replaced by the `into` species. That species starts at the waterline and climbs through its altitude band at its `maxClimbRate`. Give the next stage a very long `cruiseChangeTime` so it keeps rising.

#### COLONY (a host carrying smaller creatures)
```
COLONY { species = jool_crestfly  min = 6  max = 12  perchHeight = 16  perchRadius = 7  perchDrop = 0.03
         orbitRadius = 32  orbitHeight = 20  tendrilDepth = 35  tendrilRadius = 18
         sortieChance = 0.45  preyChance = 0.12  regrowTime = 60  swarmDistance = 90  feedMessage = ... }
```
The host spawns with `min`–`max` colonists perched on a domed disc `perchHeight` metres above its origin. Colonists rest, fly loops round the host (`orbitRadius`, `orbitHeight`), and a vessel within `swarmDistance` sends them all up. On a fraction `preyChance` of loops one flies down into the feeding zone (`tendrilDepth` below the host, within `tendrilRadius`), gets caught, is hauled up and eaten (`feedMessage` is shown if you are within 600 m). The host hatches one replacement every `regrowTime` seconds while below `max`. Colonist species never spawn on their own, and they count as 0.1 against the creature cap. If the host despawns, its colonists carry on as ordinary flyers.

#### Optional behaviour blocks (inside XENO_LIFEFORM)
```
FLIGHT      // for habitat = Flyer
{
    cruiseSpeed = 13   minSpeed = 7   maxSpeed = 26     // m/s
    sinkRate = 1.6     climbRate = 4                    // m/s down while gliding / up while flapping
    takeoffTime = 1.2  landTime = 1.2                   // seconds (clip length is stretched to fit)
    takeoffChance = 0.2                                 // AI: chance per wander decision to take off
    minGlideTime = 20  maxGlideTime = 50  cruiseHeight = 45
    flapImpulse = 6    flapStamina = 4                  // rider flaps; stamina recharges on the ground
}
SLEEP
{
    sleepsAt = Night        // Night, Day, or Any (naps only)
    napChance = 0.1         // chance per idle decision to doze off outside sleep-time
    minNap = 30  maxNap = 90
    wakeDistance = 4  wakeChance = 0.2    // per-second chance to wake while something is that close
}
ATTACK      // swipes at EVA kerbals that come within range (knockback, non-lethal)
{
    range = 5.5  knockback = 9  cooldown = 5  duration = 1.0  hitTime = 0.42
    onlyWhenProvoked = false              // true = only when the rider orders it
}
MOUNT       // makes the creature rideable
{
    seat = saddle             // transform (bone) in the model the kerbal is pinned to
    seatOffset = 0,0.3,0
    mountRange = 5
    requireAsleep = true      // kerbals must sneak up while it sleeps
    requiredTrait =           // e.g. Pilot; empty = anyone
    walkSpeed = 2.2  runSpeed = 5.5  turnRate = 80
}
```
```
BURROW      // escape by digging in, tunnelling away and resurfacing (needs digAnim / emergeAnim)
{
    digTime = 1.5  emergeTime = 1.2  depth = 1.9
    minUnderground = 6  maxUnderground = 12  tunnelSpeed = 5
    moundColor = 0.88,0.9,0.93,1  moundLife = 120     // spoil heaps left at both ends
}
FLYBY       // habitat = Air: dives at kerbals / landed vessels for one low pass, then leaves
{
    detectRange = 300  diveSpeed = 22  passHeight = 4  screechDistance = 28  passDuration = 1.8
    retreatSpeed = 18  climbRate = 7  singlePass = true  cooldown = 90
}
SOUNDS      // 3D sounds: GameDatabase audio paths (.wav/.ogg), without extension
{
    idle = MyMod/Sounds/call   idleInterval = 25
    alert =   attack =   flee =   flyby =   dig =
    roar =   throw =   impact =          // ROAR / THROW events and boulder landing
    footstep =   stepInterval = 1.3      // footstep every N seconds while walking at moveAnimSpeed
    volume = 1  range = 250
}
ROAR        // bellows at intruders before engaging; nearby wildlife scatters (needs roarAnim)
{
    duration = 3  cooldown = 40  range = 450  scareRadius = 200
}
THROW       // hurls a boulder at kerbals / vessels in range (needs throwAnim)
{
    minRange = 45  maxRange = 280  launchSpeed = 58   // the flatter ballistic arc that reaches is used
    cooldown = 9  duration = 3.2  releaseTime = 0.63  // the rock leaves the hand at 63% of the clip
    hand = handL  releaseOffset = 0,0,0               // transform holding the rock until release
    radius = 1.6  mass = 6  lead = 0.8  spread = 5    // lead: 0 = aim at target, 1 = at its predicted position
    color = 0.45,0.43,0.38,1
}
```
Extra `MODEL` clip names: `digAnim`, `emergeAnim`, `diveAnim`, `screechAnim`, `roarAnim`, `throwAnim`.

`unique = true` on a lifeform keeps it out of random spawns. Use it for a creature that only lives in its `XENO_LAIR`.
Giants (`size` of 10 or more) also hit vessels with their `ATTACK`, not just kerbals. The shove is weaker for heavier vessels.
Thrown boulders are real physics objects, so they can break parts. Set `projectileDamage = false` in `XENOBIOLOGY_SETTINGS` and they only push things instead.

**Riding:**
- Mount and dismount with **Y**, or with the kerbal's right-click menu.
- On the ground: **WASD** to move, **Shift** to run, **Space** to take off, **T** to attack.
- In the air: **W** dives (faster, more sink), **S** pulls up (slower; it stalls if too slow), **A/D** banks, **Space** flaps. Touching down plays the landing clip.
- Other wildlife ignores a mounted kerbal, so riding is a good way to get close to a herd.

### XENO_FOSSIL
| key | default | meaning |
|---|---|---|
| `name`, `body` | required | |
| `form` | Shell | `Shell`, `Bones`, `Trackway`, `Stromatolite`, `Amber` (procedural outcrop shape, used when there is no `MODEL`) |
| `kind` | = form | free-text type shown in the Field Guide, e.g. `Trace fossil`, `Reef cups`, `Impression` |
| `portrait` | | texture path; shown on the fossil's Field Guide page once it has been studied |
| `biomes` | any | |
| `evidenceFor` | | comma list of clade and/or panspermia names |
| `evidence` | 1 | points added the first time this fossil type is studied |
| `requiredTrait` | Scientist | empty = any kerbal can study it |
| `minLevel` | 0 | minimum experience level, for fragile specimens |
| `studyTime` | 20 | seconds at level 0; each level is 35% faster |
| `rarity` | 1 | 1 ≈ a 50% chance of one outcrop per territory cell |
| `age`, `color`, `size`, `scienceValue`, `silhouette`, `description` | | |
| `MODEL {}` | | optional custom outcrop model (same keys as above, no animations). Model in real metres, Z up, bedding plane near +0.1 m, edges sunk to −0.17 m so slopes never show a gap |

Fossil outcrops always sit in the same places. A studied site stays studied, and its green beacon goes out.

#### Landmark fossils (one huge site per game)
Set `landmark = true` for a single enormous set of remains, such as Kerbin's Fallen Titan. A landmark is never scattered by the territory system. Instead, the plugin picks one spot per save and stores it in the scenario (`Lairs["landmark:<name>"]`). The spot is either within `searchRadius` of `searchCenter`, or found by a whole-body scan for points deep inside one of the fossil's `biomes`, preferring flat ground about 400 km from KSC. The model's facing is chosen along the least terrain variation unless `heading` is set. The model sits level at the terrain height (it is not tilted to match the slope), so build it with sediment mounds that sink below Z = 0.

| key | default | meaning |
|---|---|---|
| `landmark` | false | turns on everything below |
| `searchCenter` | | `lat, lon`. Search here instead of scanning the body |
| `searchRadius` | 0 | metres around `searchCenter` |
| `footprint` | 1000 | half-size of the model in metres; used to score how flat the ground is |
| `discoverRange` | 25000 | metres. Within this range (and below 40 km altitude), the player gets `discoverMessage` and a waypoint |
| `loadRange` | 40000 | the model is built inside this range and destroyed beyond it |
| `studyPoint` | | repeatable `x, y, z` in the model's Unity frame (x right, y up, z forward = Blender +Y). A green beacon marks each point; a scientist studies the remains from any of them |
| `studyRange` | 40 | metres from a study point at which study is possible |
| `beaconSize` | 3 | beacon scale, for sites seen from far off |
| `heading` | auto | degrees, fixed facing |
| `discoverMessage` | | screen message on discovery |

`evidenceFor` may be left empty: a landmark can be lore alone, with no link to any tree of life. KSP meshes use 16-bit indices, so a kilometre-scale model has to be split into chunks of under 65 535 exported vertices. `titan_build.py` cuts its mesh by loop count after baking.

### XENO_LAIR
A model placed on the surface at a fixed spot, plus a unique resident that lives there.
Example: the Cyclops' cave in `Lifeforms/Stock/Kerbin.cfg`.

| key | default | meaning |
|---|---|---|
| `name`, `body`, `model` | required | `model` is a GameDatabase path (.mu) |
| `displayName`, `description` | | `displayName` is also the waypoint name |
| `latitude`, `longitude`, `searchRadius` | 0, 0, 6000 | The flattest spot inside this circle is picked once per save and stored in the save file. |
| `minAltitude`, `maxAltitude` | 50, 3000 | Altitude limits for the site, so it isn't placed in the sea or on a summit. |
| `footprint` | 70 | radius (m) that should be flat |
| `sink` | 0.6 | how far the model is lowered into the ground |
| `heading` | -1 | Direction the model's +Z axis (Blender +Y) faces. -1 = downhill. |
| `loadRange` | 12000 | the model exists within this distance of the active vessel |
| `residentRange` | 3500 | the resident is simulated within this distance |
| `discoverRange` | 30000 | coming this close reveals the lair and adds a waypoint |
| `resident` | | lifeform name (usually `unique = true`) |
| `leash` | 450 | the resident never strays further than this from the entrance |
| `entrance`, `den`, `pen` | entrance, den, pen | Names of empty transforms in the model. The resident walks to `entrance`, then to `den` at night, where it sleeps. By day it grazes around `pen`. |
| `doorOpenAnim`, `doorCloseAnim` | open, close | Optional clips. The door closes once the resident is asleep and opens when it wakes. |
| `flock`, `flockSize` | | lifeform kept by the lair, spawned around `pen` by day |
| `scienceValue`, `surveyText` | 40 | science and message for the EVA **Survey Lair** action, available while a kerbal is inside |
| `waypoint` | true | |
| `discoverMessage` | | screen message when a vessel first comes within `discoverRange` (default: boulders being moved around) |
| `anomaly` | true | list the lair as a surface anomaly: it is added to the body's `pqsSurfaceObjects`, so KerbNet's anomaly scan (and SCANsat) finds it. Landmark fossils are listed too |

If the config moves a lair (its search centre ends up more than ~4.5 × `searchRadius` from the stored site), existing saves pick a new site. If nothing in the search circle is dry ground inside the altitude band, the search widens up to 4×.

**Sessile residents.** If the resident is `sessile = true` (e.g. the Lantern Glowworms in the Glowworm Grotto), it is spawned once at `den`, stays there and never walks the entrance/pen routine; the door clips, if any, still follow its sleep cycle. Example: `kerbin_glowworm_grotto` in `Kerbin.cfg`.

All colliders in a lair model are moved to layer 15 (Local Scenery). Kerbals and rovers can then stand on them, and creatures walk on them like terrain.
**Mesh colliders must not be convex.** io_object_mu exports `MU_COL_MESH` as convex by default, and a convex mesh collider is the solid hull of the mesh: it seals tunnels and fills caves. Set `muproperties.isConvex = False` (the plugin also forces lair mesh colliders non-convex at load). Keep the cave floor a rock slab *above* the terrain (terrain would otherwise show through it) and give the collider its own decimated mesh.
Use mesh colliders for walls and floors.

**Underwater and open lairs (the Glimmering Reef).** These keys make a lair suit a sea-floor site and add ambient life to the model:

| key | default | meaning |
|---|---|---|
| `underwater` | false | Site on the sea floor. `minAltitude`/`maxAltitude` are then terrain heights below sea level (e.g. -40 and -16). The search runs outward from the centre in rings (up to 10 × `searchRadius`) and takes the nearest flat patch whose whole `footprint` stays in the band. A stored site that falls outside the band is re-sited automatically. **Survey Lair** needs the kerbal under the surface |
| `surveyRadius` | 0 | If greater than 0, "inside" means within this many metres of the centre. Use it for open sites without an entrance axis. 0 keeps the cave box |
| `lightsNightOnly` | false | Point lights only switch on at night (and within `lairLightRange`) |
| `glowPulse`, `dayGlow` | 0, 1 | `glowPulse` makes every emissive material (`_EmissiveColor`) "breathe" by this fraction. `dayGlow` scales the glow by day. The phases differ per material, so give different areas their own material copies |
| `swayAngle` | 4 | degrees. Child transforms named `sway…` rock slowly about their own origin (sea fans, kelp). Put the origin at the holdfast |
| `clearScatters`, `scatterClearRadius` | true, 1.5 × footprint | With Parallax Continued installed, terrain scatters (kelp, grass, rocks, trees) are kept off the site. This uses Parallax's own `PQSMod_MapDecalVertexRemoveScatter`, the mod that keeps trees off the KSC, added at runtime because the site is chosen per save |
| `detailRange` | 0 | If greater than 0, renderers on objects named `coral_…`, `sway…` or `dayonly…` are switched off beyond this distance |
| `detailRangeSmall` | 0.3 × detailRange | Objects named `coral_s_…` (small corals, polyps, anemones) are switched off beyond this distance |
| `catalogueScience` | 0 | A science bonus (a Lair Survey subject named `<lair>_catalogue`) once every species with a specimen marker in the model has been observed |
| `FLOCK { lifeform, size = a, b, spread }` | | Extra visitor groups, any number. Each spawns once per visit by day, within `spread` metres of `pen`. The single `flock` key still works |
| (naming) | | Objects named `dayonly…` are hidden at night, for example sun shafts made with KSP/Particles/Additive quads |

**Fixed life in a lair (specimen markers).** Corals, sponges and other life that is part of the lair model become Field Guide species:
- Put empty transforms named `spec_<lifeform>_##` in the model where specimens grow.
- The lifeform needs `unique = true` and `sessile = true`. It needs no MODEL or PROCEDURAL node, because it is never spawned. `guideCategory = coral` names it while it is still unidentified ("Unidentified coral").
- **Observe Lifeform** (O) on EVA picks the nearest marker within the species' `observeRange`, preferring undiscovered species. It records the discovery and gives `xenoObservation` science.
- The EVA "Nearest life" field shows the specimen and the lair's catalogue progress, for example `[9/15]`. A hint is shown the first time a kerbal swims close to an unknown species.
- Example: the Glimmering Reef's 15 corals, anemones and sponges (clades Anthozoida, Hydrocorallia and Porobionta in `Kerbin.cfg`). Portraits and silhouettes come from `Tools/reef/reef_specimens.py` and `Tools/blender/reef_portraits.py`, then `xeno_tool.py stylize`.

**Lair fossils.** Empty transforms named `fossil_<fossil>_##` in a lair model become studyable fossil sites:
- Each site is pinned exactly at its marker (cave floors work, even under a rock roof), loaded and unloaded with the lair, and saved as studied per marker.
- Give the XENO_FOSSIL `unique = true` so it is never scattered at random. Example: `kerbin_reefcore`, the Fossil Reef Core on the reef cavern's floor, which is evidence for Anthozoida and Lithocorallia.

**Underwater ambience** (`underwater = true` lairs, `Source/ReefAmbience.cs`). While the camera is underwater within 450 m:
- marine snow drifts around the camera;
- at night, plankton sparks trail the active vessel, more of them the faster it moves.

**Diving.** Stock EVA kerbals float, so `XenoDiving` lets a swimming kerbal dive:
- Hold jetpack-down (Left Ctrl) to sink, and jetpack-up (Left Shift) to rise. With neither held, the kerbal holds its depth.
- Underwater swimming is 1.6× faster.
- Stock buoyancy returns at the surface.
- A hint is shown the first time a kerbal swims within 3 km of an underwater lair.
- `kerbalDiving = false` in Settings.cfg turns diving off.

**How the reef is made** (`Tools/reef/`, run in plain Python with numpy, scipy, scikit-image and Pillow):
1. `reef_sdf.py <dir> 0.3` builds the rock as a signed distance field. It contains the crest, spurs, bommies, arches and about 700 encrusting heads. The field gets a domain warp, noise and crevices. Tunnels, the cavern and skylights, and the slot canyon are cut afterwards with only light noise, so they stay at least 4 m wide. Marching cubes then writes `reef_high.npz`, about 1.3M triangles.
2. `reef_textures.py <dir>` writes the coral atlas (4×4 cells, see its docstring), its glow map, the alpha-cut sea fan sheet and the sun-shaft gradient.
3. `reef_corals.py <dir>` samples the rock and grows the six coral types with atlas UVs. They are grouped by the same 8-chunk grid as the rock, and the biggest sea fans become separate `sway_fan_##` objects.
4. Copy the npz/json files to `XenobiologyDev\reef` and the textures to `Models/Kerbin/CoralReef`.
5. Run `Tools/blender/reef_build.py` in Blender. It decimates the rock to about 90k triangles, splits it into 8 chunks and bakes each one (Cycles on the GPU): a diffuse map (rock, dead coral, coralline algae, colony patches, sponges, sand and ambient occlusion) and a tangent-space normal map from the high-poly plus procedural bump. The rock uses KSP/Bumped. It then exports the `.mu`.
6. Convert with `Tools/xeno_dds.py`. Files ending in `_NRM` become DXT5nm normal maps.


#### Generated forests (`FOREST {}` inside a XENO_LAIR) — experimental
> **Experimental.** The forest system is in the plugin but no stock forest ships in v0.1. The Emberwood (an autumn forest on Kerbin) is held back for a later release; its config, textures and build scripts are kept in the source repository under `Extras/Emberwood/`. Use `FOREST` at your own risk: the format may still change.

A lair can grow a whole forest around its site instead of (or as well as) a model. The plugin samples the PQS terrain and plans the forest on a worker thread (`Source/ForestLayout.cs`, pure C#, testable outside KSP). It draws the forest as 80 m chunks and 40 m cells (`Source/XenoForest.cs`). A second worker thread merges each cell's meshes, and the main thread only uploads finished meshes, about 3 ms' worth per frame. The plan is cached in `PluginData/ForestCache` so a save reloads its forest instantly. Example: the Emberwood (`Extras/Emberwood/Kerbin_Emberwood.cfg` in the source repository).

What gets planned:
- **Forest floor.** The PQS terrain is lifted by `lift` metres and carries a tiled leaf-litter mesh, which hides the stock ground. It dips back under the terrain past the wobbly edge.
- **Water.** A stream finds its way downhill from a spring pool (with a small cascade) to a pond. The water level never rises downstream. The channel is cut into the floor, and a streambed ribbon and a scrolling water ribbon are laid over it.
- **Trail.** A trail runs from the edge facing the space centre to a clearing with a giant "elder" tree, crosses the stream on a footbridge at a straight reach, and ends at the spring. A side trail runs down to the pond. Trails are levelled lengthways and drawn as alpha-cut ribbons.
- **Trees.** Scattered on a jittered grid, with species chosen by grove noise and habitat (`wet`, `high`, `edge`, `pathside`). Big crowns get more room (`footprint`).
- **Undergrowth.** Ferns, shrubs, saplings, logs, rocks, mushrooms, stumps, leaf drifts, reeds and lily pads.

| FOREST key | default | meaning |
|---|---|---|
| `kit`, `bridge`, `spring` | | Model URLs. The kit holds meshes only: `t_<model>_<variant>_0` / `_1` (full and simplified tree), `t_<model>_imp` (three crossed cards), `p_<prop>_<variant>`, and `elder_0`, `elder_1`, `elder_imp`. `bridge` has its span along +x with its deck ends at ±5.5 m. `spring` faces +z toward the pool. Both carry their own colliders |
| `radius`, `spacing`, `lift`, `propDensity`, `seed` | 500, 6.6, 1.3, 1, hash of the lair name | Size, mean tree spacing, floor lift, undergrowth density, random seed. Near the vessel the plugin also casts rays at the stock terrain colliders. If the ground KSP actually draws comes within 0.3 m of the floor (in hollows the PQS mesh sits above the sampled heights), it raises the whole forest, up to 3 m. The raise is saved next to the layout cache |
| `entranceBearing` | -1 | Where the trail starts (degrees). -1 means facing the space centre |
| `nearRange`, `midRange` | 50, 190 | Full trees, which are the only ones that cast shadows, are drawn in 40 m cells closer than `nearRange`. Simplified trees are drawn per cell out to `midRange`, with one card mesh per 80 m chunk beyond that |
| `propRange`, `colliderRange` | 100, 60 | Undergrowth draw distance (40 m cells, no shadows). Floor colliders (2 m mesh), trunk and big-rock colliders exist only this close to the active vessel |
| `groundFine`, `groundMid`, `groundCoarse`, `floorTile` | 110, 320, 700, 6 | The floor mesh uses 1, 2, 4 or 8 m steps by distance. `floorTile` is the litter texture's tile size |
| `leafRate` | 26 | Falling leaves per second around the camera. They come in gusts every 20 to 45 s |
| `fernLifeform`, `shrubLifeform`, `reedLifeform`, `elderFossil` | | The Field Guide entries for the undergrowth, and a `unique` fossil placed between the elder's roots |
| `SPECIES { name, model, lifeform, weight, wet, high, edge, pathside, cluster, minScale, maxScale, footprint, variants, trunkRadius, trunkHeight }` | | One per tree type. Up to six trees of each species beside the trail get `spec_` markers for Observe. The elder counts for the species whose `model = copperoak` |

**FLOCK additions** (any lair): `at = <spot>` spawns the group at a named place. Forests define `clearing`, `bridge`, `pond`, `pool`, `stream`, `elder` and `entrance`; model lairs can name any child transform. `leash = <m>` makes the group turn back when it strays further than that. Groups now spawn at their own `activeTime`, so owls arrive at night.

**Creatures and the floor.** Creatures walk and land on the forest floor even far from the vessel, where it has no colliders (`XenoForest.Floor`).

**Ambience.** Falling leaves tumble around the camera (mesh particles using `forest_fallleaves`, 4×4 frames), and die when they touch the floor. On nights near the water, lantern-motes hang over the pond and stream. Mist rises at the cascade.

**How the Emberwood is made:**
1. `Tools/forest/forest_textures.py <dir>` paints the bark strips, foliage atlas (4×4 sprigs, needle sprays, ferns, shrub, reeds), leaf litter (+ normal map), path, streambed, water, cascade, planks and falling leaves.
2. `Tools/blender/forest_build.py` grows the trees: 6 species, 3 variants each, with recursive branches, leaf cards and LOD1 from the same skeleton. It also builds the undergrowth, elder, bridge and spring, renders the impostor atlas and exports the three `.mu` files.
3. `Tools/blender/forest_icons.py` renders the plant portraits and silhouette masks. Then run `xeno_tool.py stylize`.
4. `test/LayoutTest.cs` with `Tools/forest/layout_map.py` draws a plan view of a layout. `Tools/blender/forest_preview.py` rebuilds part of it in Blender for beauty shots.
5. Convert with `xeno_dds.py`. Foliage and impostor atlases keep their alpha coverage in the smaller mips, so trees don't thin out with distance.

### XENO_FEATURE
Geysers and fumaroles: scenery placed by the same deterministic 3 km cells as territories, so a geyser field is always in the same place. They are not catalogued and give no science, but a feature can `attracts` a species, which is then often found circling it (the Laythe geyserkites).

```
XENO_FEATURE
{
    name = laythe_geyser
    body = Laythe
    kind = Geyser                 // Geyser (erupts now and then) or Fumarole (steams all the time)
    biomes = Peaks, Crater Island
    chance = 0.3                  // chance a 3 km cell holds a field
    minCount = 2                  // vents per field
    maxCount = 4
    fieldRadius = 160
    jetHeight = 28                // geysers: eruption height (m), duration (s), quiet time between (s)
    duration = 9
    intervalMin = 40
    intervalMax = 110
    sound = Xenobiology/Sounds/laythe_geyser
    attracts = laythe_geyserkite
    attractChance = 0.7           // per field
    attractLeash = 260            // residents turn back when further than this
    PLUME { ... }                 // optional: the steam column (same keys as a lifeform's PLUME)
    EMITTER { ... }               // optional: the steam particles (same keys as a lifeform's EMITTER)
}
```

| key | default | meaning |
|---|---|---|
| `minAltitude` | 1 | vents are never placed lower than this above sea level |
| `viewDistance` | 5000 | vents are created and drawn within this distance (m) of the vessel |
| `moundRadius`, `moundHeight` | 4, 0.7 | size of the sinter mound |
| `sinterColor`, `matColor`, `poolColor` | white, orange, blue | mound colours: fresh sinter at the lip, thermophile mats on the slope, the hot pool (geysers) |
| `volume`, `soundRange` | 0.8, 600 | eruption sound |

### XENO_PANSPERMIA
| key | default | meaning |
|---|---|---|
| `name`, `sourceClade`, `targetBiosphere` | required | |
| `displayName`, `mechanism`, `age`, `description` | | |
| `revealThreshold` | 3 | evidence = fossil points + 1 if the source clade is named + 1 if the target clade is named + 1 per discovered `microbeEvidence` microbe |
| `targetClade` | the target's root | the lineage that was seeded, when a world has more than one origin (Laythe: animals from Kerbin, fungi from Jool) |
| `microbeEvidence` | | comma list of MICROBE names (Microbiology Expansion) that count as evidence once discovered |

While the evidence is partial, the target tree shows an "Anomalous origin?" node. Once the threshold is met, the event is announced. A dashed purple link then joins the two trees, and you can click it to jump between worlds.

---

## Microbiology Expansion compatibility
Xenobiology reads MicrobiologyExpansion's `MICROBE` nodes directly and asks its save data (by reflection, no hard dependency) which microbes have been discovered and lab-processed.
- **Microbes become leaves** on the trees of life (shown with a µ tag, or "microfossil"). Click one for its codex icon, category, hazard, biomes, lab state, and what it eats and is eaten by.
- **Evidence:** a discovered microbe adds 1 to its clade and every clade above it. Lab-processing it in a Mobile Processing Lab adds 1 more.
- **Placement**, in this order: an explicit `microbes =` list on a clade, then the deepest clade of the microbe's home world whose `microbeCategories` match, then the biosphere's `microbeClade`. `Debris` and `Unknown` entries are never placed unless listed explicitly.
- `Lifeforms/Stock/MicrobiologyExpansion.cfg` places all 64 living stock microbes. It adds microbial kingdoms to Kerbin, Duna (surviving relicts of the extinct biosphere), Eve and Laythe, plus a microbes-only Joolian Aerobiosphere. Everything in it is behind `:NEEDS[MicrobiologyExpansion]`.
- `Lifeforms/Stock/Moons.cfg` gives the microbe-only worlds (Mun, Minmus, Dres, Eeloo, Tylo) small trees of their own, plus two crossings: the Munar Splash (Kerbin microbes thrown onto the Mun) and the Chlorine Rain (Tylo cells falling into Jool, where the Joolmoeba eats them). Microbes on any other world without an XENO_BIOSPHERE are not shown; give it a biosphere with a `microbeClade` and they appear.
- `xeno_tool.py validate` reads MICROBE nodes and honours `:NEEDS[]` and simple `@` patches. `--mods A,B` simulates a mod list.

## Gameplay loop (what players do)
1. Land or splash down, then go on EVA. Creatures spawn 150–1200 m away and react to you according to their temperament.
2. Press **O**, or right-click the kerbal and choose **Observe**, within `observeRange` of a creature. The species is catalogued at once, and field-notes science goes into the kerbal's container. Recover or transmit it like any other EVA science.
3. Scientists choose **Study Fossil** at outcrops marked by a faint green glow. They must stay within 6 m until the study finishes.
4. **Capture Specimen** (EVA) puts a small creature, within 40 m of the kerbal, into a CO-Z Containment Unit within 150 m. Anything over the unit's `maxSpecimenSize`, anything `unique`, and anything over 8 m (megafauna) is refused. Recover the vessel with the specimens still alive for triple science.
5. **Lab analysis.** Every science lab (anything with `ModuleScienceLab`, such as the Mobile Processing Lab) gets an analysis bench. With a scientist inside, **Start Xeno Analysis** works through the CO-Z specimens and fossil samples (Palaeontological Survey data) aboard the vessel, about 3 hours each, faster with more experienced scientists. Each species or fossil type analysed for the first time gives Xenobiology Lab Analysis science and adds 1 evidence to its lineage, which can resolve branches of the tree of life.
6. Instruments discover life without EVA. The **Xenofauna Tracking Camera** photographs creatures in line of sight. The **Hydrophone** hears aquatic species up to 4 km away while submerged.
7. Open the **Field Guide** from the toolbar. Its Species, Tree of Life and Fossils tabs fill in as evidence comes in, and panspermia discoveries tie the trees together.

## Parts and their modules
The three parts live in `Parts/`. Their modules can be added to any part, so other mods can make their own variants.

| Module | Key fields (defaults) | Notes |
|---|---|---|
| `ModuleXenoTracker` | `range` 1500, `maxHeight` 6000, `ecPerSecond` 0.06, `lockTime` 3, `scienceMultiplier` 0.6, `slewRate` 60, `minTilt` -20, `maxTilt` 100, `panTransform` pan, `tiltTransform` tilt, `lensTransform` lens, `experimentID` xenoTelephoto | Picks the nearest undiscovered creature in line of sight (terrain and the water surface block the view) and photographs it after `lockTime` seconds. "pan" rotates about local Z, the mount normal. "tilt" rotates about X, and the lens looks along +Y at rest. The part needs a `ModuleScienceContainer`. |
| `ModuleXenoHydrophone` | `range` 4000, `minDepth` 1.5, `ecPerSecond` 0.12, `scanInterval` 6, `bearings` 16, `ringStep` 500, `scienceMultiplier` 0.5, `lightTransform` status_light, `experimentID` xenoHydrophone | Hears `Water`/`Underwater` creatures that are already spawned. It also samples the territory cells on rings around the vessel, which reach species too far away to be spawned. Water shallower than 2 m does not carry sound. The part needs a `ModuleScienceContainer`. |
| `ModuleXenoAnalysis` | `hoursPerItem` 3, `ecPerSecond` 1.5, `specimenMultiplier` 2, `fossilMultiplier` 2, `experimentID` xenoAnalysis, `fossilExperimentID` xenoFossilStudy | Added to every part with `ModuleScienceLab` by `Patches/XenoLab.cfg`. Work rate = 1 + 0.5 × level per scientist in the part. Results go into a science container aboard when `requireRecoveryForScience` is on, and are transmitted otherwise. Work continues while the vessel is unloaded. |
| `ModuleXenoContainment` | `capacity` 4 (volume = 0.08 × size³), `maxSpecimenSize` 3.5, `ecPerSpecimen` 0.03, `survivalTime` 60, `liveMultiplier` 3, `deadMultiplier` 1.2, `experimentID` xenoSpecimen | Saves its specimens as `ScienceData` nodes, so stock vessel recovery pays out. A specimen dies after `survivalTime` seconds without power. **Release Specimens** lets living ones go. |

## Example content
`Lifeforms/Stock/` contains a complete worked example. **Duna** (extinct, fossils only) seeded **Kerbin**, Kerbin's ocean life later seeded **Laythe**, and **Eve** is an independent second genesis. Copy it as a template.

---

## Performance and asset rules

KSP keeps every texture and model under GameData in memory, and every creature is a skinned, animated mesh. Follow these rules for anything you add:

- **Textures are DDS.** Model textures (`Models/**`, `Parts/**`) ship as DXT1 `.dds` with mipmaps, stored vertically flipped, as KSP expects. The Blender scripts still bake PNGs; afterwards run `python Tools/xeno_dds.py --dir Models/<Body>/<Species>` (needs numpy, Pillow and `pip install etcpak`) and **delete the PNG**, or KSP loads both copies. As DXT1, a 2048 texture takes about 2.8 MB instead of 16 MB.
- **Field-guide images live in `PluginData/`.** Portraits and silhouettes go in `PluginData/Portraits` and `PluginData/Silhouettes`, which KSP's GameDatabase skips. The plugin loads each one the first time the field guide shows it. Configs keep the usual paths (`silhouette = Xenobiology/Textures/Silhouettes/<name>`). `xeno_tool.py outlines` writes to the new place.
- **Nothing else goes under GameData.** Blender saves (`.blend`) go to `XenobiologyDev/blend`, and the butterfly wing atlases go to `XenobiologyDev/lepid`. Any PNG anywhere under GameData is loaded as a texture.
- **Polygon budgets** (exported vertices per skinned mesh):

  | creature | vertices |
  |---|---|
  | herd animals and anything spawned in groups | ≤ 15k |
  | single creatures | ≤ 25k |
  | unique giants | ≤ 50k |
  | any single mesh | ≤ 65,534 (KSP's limit) |

  Mammal pelts use `peltScale` (default 0.55: fewer, wider, 2-row cards). Glowworm beads are 6-vertex octahedra.
- **Creature level of detail** (plugin, `CreatureLod.cs`, tunable in `Settings.cfg`). Every half second each creature measures its distance to the camera:

  | level | distance | what changes |
  |---|---|---|
  | near | < `lodNearDistance` + 10 m per metre of size | full detail: shadows if size ≥ `shadowMinSize`, ground contact every frame |
  | mid | < `lodFarDistance` + 25 m per metre | no shadows, 2-bone skinning, ground probe 5× a second |
  | far | beyond mid | 1-bone skinning; AI and motion every 3rd frame (time accumulated) |
  | culled | beyond `lodCullDistance` + `lodCullPerMetre` per metre | hidden, no animation, AI every 8th frame, no placement |

  Other per-frame savings:
  - Animation and skinning only run on screen. The plugin pads the rest-pose bounds so spread wings never get culled by mistake.
  - Flying and air species sample PQS terrain 5–10× a second instead of every frame.
  - Lair lights cast no shadows and switch on only within `lairLightRange`.
  - Fossil outcrops are glued to the planet once they are placed.
- **Population:** `maxActiveCreatures` (default 30; herds and schools count ¼ each) plus a hard limit of `maxCreatureObjects` (default 60) on creature objects.

## Making a `MODEL` creature in Blender
Blender is needed only for `MODEL` creatures; `PROCEDURAL` ones don't need it. `Tools/blender/` holds the full scripted pipeline used to build the Greater Mossback, and it works as a template:

| script | does |
|---|---|
| `mossback_1_model.py` | Metaball body → voxel remesh → armature with automatic weights → sails, moss, eyes, claws and frills |
| `mossback_2_texture.py` | UV unwrap, procedural material, Cycles bake to `_diffuse.png` and `_glow.png`, KSP shader setup |
| `mossback_3_animate.py` | Procedural `idle` / `walk` / `run` / `alert` clips as NLA tracks (track name = clip name) |
| `mossback_4_export.py` | Exports the empty-rooted hierarchy to `.mu` with taniwha's **io_object_mu** add-on |
| `glider_1..3_*.py` | The same pipeline with membranes, `saddle` bone and flight clips. `VARIANT = spiketail / tritail` builds both related species from one script |
| `export_mu.py` | Generic exporter: set `ROOT` (empty name) and `OUT_PATH` |
| `fauna_giants.py` | Dedicated builders for Laythe's giants: `cetacean` (whale body, gaping jaw with filter combs, billowing pleated cheek pouches, humpback flippers, swept flukes; `idle` feeding gape, `swim`, `breach`), `seadragon` (wedge head with jaw, horns, teeth, frill fans, spined dorsal sail, paddles, tail fan, photophores; rolling surface `idle`/`move` humps, rearing `alert`) and `skysac` (lobed, veined lifting-gas airship with a hanging reef keel, spiracles and clustered beaded tendril curtains that trail behind it; 20-second `idle`/`drift` breathing cycles) |
| `fauna_extra.py` | Factory extensions: the `ceph` archetype (squids, krakens; arms, tentacles, fins; `idle/swim/jet/attack/alert`), the `sessile` archetype (`form = puffball / coral / mat`; `idle/alert/burst`) and species features for the classic archetypes (whale flukes and cheek pouches, rotor tails, turtle shells, insect wings, exposed ribs, reef crowns...). Bones can now animate scale |
| `fossils_build.py` | **Fossil outcrops.** Every stock fossil is a small bedded rock slab (≤ 1 m, trackways 2 m) built as a heightfield whose edges sink into the ground. Impressions, trackways and burrows are carved into the bedding plane as relief; shells, teeth, crystals, cups and coral sit half-weathered out of it as solid pieces (planispiral and high-spired shell generators, straight cones, brachiopod valves, revolved domes/cups/teeth, swept tubes). One `@fossil` spec per fossil. `STEP = "model"` renders reviews only; `"all"` bakes a 1024 texture with ambient occlusion, exports `Models/Fossils/<Body>/<name>.mu` and renders the portrait and a top-down silhouette mask of just the fossil. Run with `FOSSIL = "<name>"`, a body name, a list, or `"all"` |
| `fauna_giants.py` `form = "bloat"` | The skysac builder's round variant (Bloatfloater): a lumpy, over-filled bag of seven bulges and four blisters, a flattened crown covered in papery nest cells and holes, spiracles in a ring, feeding frills and glowing digestive sacs underneath, and clusters of beaded tendrils that splay outward (`splay`). New hex features: `jumplegs`, `tegmina`, `rhinohorn`, `nolantern` |
| `fauna_giants.py` arch `skylev` | The Sky Leviathan family. `form = adult`: an arching, drooping canopy of `nr` segmented, knobbed ribs (`ribL`, `ribSpan`, `droop`), with photophores and scalloped double-sided membrane between them, bare spines and ragged streamers hanging under the wing (`ribStreamers`), a baleen filter comb round the throat (`combN`), and `nc` clusters of trailing tentacles (`TL`); slow 30-second canopy wave. `form = pupa`: gas sac with crumpled canopy ribs, the grub body slung beneath, tentacle buds, breathing clip. `form = larva`: segmented seafloor grub with prolegs, glow spots and a mouth comb |
| `fauna_giants.py` arch `colossus` | The Tidewalker: a wrinkled, many-eyed metaball head (`headScale`) with a forward lobe, `legs` S-curved walking tentacles reaching the ground (`legR`), `feeders` hanging feeding tentacles, two raised arms, rimmed black eyes with ember irises (`eyes`), and bony crown ridges. Tentacles are Catmull-Rom tubes with explicit weights and suckers. Clips: `idle`, `walk` (two alternating leg groups), `roar` |
| `titan_build.py` | **The Fallen Titan** (landmark fossil, 1.4 × 2.6 km). Uses the `fossils_build.py` helpers at kilometre scale. Built from: a 44-vertebra spine with a curved neck; 15 towering rib arches on one side, with four broken ones lying in the dirt, and flat ribs on the fallen side; a metal lance through the chest; the pelvis and legs; the reaching arm, with five fingers curled over a cracked, glowing orb in a broken two-band cage; a scorched glass crater; the torn-off arm; 70 pieces of battle debris; and an elongated metaball skull with boolean sockets and teeth. It bakes a 2048 diffuse and a 1024 glow map (`KSP/Emissive/Diffuse`), splits the mesh into four chunks of under 60k loops, and exports `Models/Fossils/Kerbin/fallen_titan.mu`. Note: `ellipsoid` jitter is a fraction of the unit sphere, not metres |
| `../laythe_cfg.py` | Generates the Laythe expansion's XENO_LIFEFORM / XENO_FOSSIL blocks from one table, filling MODEL clip speeds from the factory's results JSON |
| art options (factory) | Wings: `tipRound` (fraction of span rounded off at the tip; default 0.16, 0 with `fingers`), automatic camber and dihedral bow; species with `hindwings` get teardrop insect wings pinched at the root, and `hindChord` sizes the hind pair (default 0.85 × `chordRoot`). Membranes: `memSpots = (ring, pupil)` with `memSpotScale` paints moth eyespots. Every eye gets a baked catchlight and a lighter lower iris. Winged species' portraits are taken at the top of the upstroke |
| `fauna_birds.py` | The `bird` archetype (Kerbin's Pennavia): metaball torso, neck chain and head, explicit legs with backward ankles, toes, webs and talons, and **two sets of wings** - a spread wing on `wing1-3` bones and a folded wing lying on the flank (`fold` bone). Ground clips scale the spread wing to nothing, flight clips scale the folded one away, so cross-fades read as the wings opening. Built in flight posture; ground clips pitch the torso up by `perch` and counter-rotate the thighs (simple FK keeps the lower foot on the ground). Beaks `cone / hook / bill / pouch / short`; features `crest facedisc eartufts snood wattle beard fan plumes pouch knob flippers webbed talons fingers bareshins dabble hophop graze runwings`; hood/collar colour regions measured along the neck (`hoodStart`, `headCol`, `collarCol`, `collarW`); `restPitch` builds upright birds (penguins). Clips: `idle walk alert sleep` (+`run`), flyers `glide flap takeoff land`, swimmers `swim float`. It also extends `quad` with `roundears bisonhorns mbeard claws brush`, a `hump`, `furFront`/`furLen`, and the clips `rears` (alert: stands on the hind legs), `swipe` (attack), `howl` (roar) and `swim/float`. New texture options: patterns `feathers` and `bars`, `shadeFront` for upright animals |
| `fauna_mammals.py` | The `mammal` archetype (bison, bear, wolf): an anatomical quadruped whose body is a table of named metaball points (`pts`: torso masses, hump, brisket, neck, skull, muzzle, leg joints; leg names are mirrored) joined by `chains`. Bone names match `quad`, so its clips and the rear / swipe / howl extras work unchanged. Fur is a `pelt` of overlapping hair cards per region (`n`, `len`, `w`, `box`, gravity `g`, `lift`, `outward`); cards are part 7, take the body's surface normal as custom normals and sample the body texture at their root (`squeezePart = 7`), so they shade and colour like the coat beneath. Also: `face` mask + `headCol`, `sock` height + `collarCol`, `ears` pointy/round, `horns`, `hooves` or paws with `claws`, a dark nose pad, `eyeR/eyeSpread/eyeFwd/eyeUp` |
| `fauna_mammals.py` extras | `saddle = (forward, up)` adds a non-deforming `saddle` bone (rideable horse; pair with a `MOUNT` block). A pelt region with `fur = True` is built as part-4 strands in its own colour (manes, tails) instead of coat cards; `furBands = False` gives plain, unbanded fur |
| `fauna_kerbin2.py` | Builders for Kerbin's second wave: `whale` (beluga: melon head, flippers, flukes; `idle/swim/alert`), `shark` (megalodon: hinged jaw with tooth rows, pectoral/dorsal/caudal fins; adds `bite`), `siphon` (man o' war: gas float with crested sail and hanging tentacle chains; `idle/move/alert/sting`), `nautilus` (log-spiral chambered shell, hood and arm ring), `vent` (tubeworms: a smoking chimney with per-worm bones that scale down to retract on `alert`), `glowworm` (beaded glowing threads hanging from height `S`, reeled in on `alert`). Also the avian feature `tails` (swallowtail hindwing streamers) |
| `grotto_build.py` | **The Glowworm Grotto** lair (v2): a bedded limestone outcrop (stepped strata ledges, joints) carved by a metaball void: a winding stream passage, a lobed domed chamber with ceiling pockets and a side alcove; a raised rock floor that ramps below ground at the mouth; pool basin, stream groove and water; stalactites along ceiling joints with stalagmites under their drips, columns, soda straws, banded flowstone curtains, rimstone dams, breakdown boulders, ferns and hanging roots at the mouth; ~900 glowing threads densest over water (two meshes, each under the vertex limit); two dim teal point lights; separate exterior/interior/decor/flora textures; a decimated non-convex collider. Prints a walkability probe. Exports `Models/Kerbin/GlowwormGrotto/glowworm_grotto.mu` |
| `../synth_calls.py` | Synthesizes the Kerbin bird and mammal calls (quack, scream, hoot, honk, gobble, bray, boom, purr, grunt, growl, howl, whinny, beluga song, hiss) into `Sounds/` |
| `../kerbin_fauna_cfg.py` | Generates the Kerbin birds & mammals block of `Kerbin.cfg` (clades, lifeforms, fossils) from one table |
| `fauna_kerbin3.py` | `lepid` (butterflies: furry thorax, segmented abdomen, clubbed antennae, coiled proboscis, folded legs, and four separate wings built from the painted outlines with Blender's constrained Delaunay; each wing has a root and a tip bone so it flexes; clips `glide` = three fluttering beats then a glide, `flap` = continuous flutter; `flapAnim` is used while climbing). `turtle` (sea tortoise: one closed shell surface - carapace with vertebral/costal/marginal scutes, grooved seams, raised scutes, serrated rear marginals, curled rim, plastron - with the per-vertex attribute `sc` = seam distance, scute id, angle, from which the shader draws growth rings, radiating streaks and per-scute tone; beaked head with plates, paddle flippers with claws; idle/walk/run/alert/swim/float). `nautilus2` (radial flame stripes as lines of constant coil angle bent toward the venter, fading on the newest part of the body whorl; growth lines; warty hood, siphon, ocular tentacles, ~90 sheathed tentacles; big pinhole eyes textured from an `eyeuv` attribute). Hooks: `post_nodes(N, c, g)` (added at the end of `fauna_nodes`) and a chained `post_uv` that maps `lepid` wings straight onto the painted atlas (top 3/4 of the texture; everything else in the bottom-left quarter) |
| `../lepid_wings.py` | **Butterfly wing painter** (numpy, scipy, Pillow). Per species: forewing/hindwing outlines (Catmull-Rom through control points, optional scalloping), a shared venation template whose vein ends snap to the outline, and a style (`monarch`, `peacock`, `swallowtail`) that paints top and underside of both wings into a 2048 atlas using per-pixel interspace index, radial position, distance to the margin and distance to the nearest vein: bordered dots, eyespots, bands, lunules, fringes and scale shimmer. Writes `blender/lepid/<name>_wings.png` + `.json` |
| `fauna_kerbin2.py` fins | `_fin` now builds a closed blade, thick at the root and thinning to sharp edges (shark, beluga flukes, man o' war sail). The megalodon has sickle-shaped pectorals and a proper crescent tail |
| `../kerbin_fauna2_cfg.py` | Generates the second Kerbin block (butterfly, moth, anaconda, sea tortoise, beluga, man o' war, nautilus, tubeworms, glowworm, horse, megalodon, anomalocaris, the megalodon-tooth fossil and the Glowworm Grotto lair). `patch()` re-homes the Duskmoth into Squamipennia and adds Cephaloconchia to the Thalassoshell fossil's evidence |
| `fauna_build.py` + `fauna_species.py` | **Creature factory.** Eight archetypes (`quad`, `hex`, `serpent`, `avian`, `bird`, `fish`, `floater`, `blob`) with per-species proportions, colours, patterns and features. One spec dict per species produces the model, texture, clips, `.mu`, silhouette mask and portrait. Run with `VARIANT = "<species>"` |
| `cyclops_build.py`, `cave_build.py` | The megafauna and its lair (the cave includes colliders and `open` / `close` door clips) |
| `parts_build.py` | The three part models (`PART = "camera" / "hydrophone" / "coz" / "all"`): hard-surface builder, one baked texture per part, and pan/tilt pivots for the camera |
| `preview.py` | Review renders |

Rules the plugin relies on:
- The creature faces **+Y** in Blender (+Z in Unity) and stands on **Z = 0**.
- Each NLA track becomes one `.mu` animation clip, and the track name is the clip name.
- Use `KSP/Diffuse` or `KSP/Emissive/Diffuse`. Keep the texture PNGs next to the `.mu`.
- Render a flat-white alpha silhouette, then run `python xeno_tool.py stylize mask.png out.png` to turn it into a field-guide outline (save it under `PluginData/Silhouettes`).
- Convert the baked textures to DDS (`Tools/xeno_dds.py`) and delete the PNGs.
- Don't run `outlines --force` afterwards: it overwrites hand-made silhouettes with procedural ones.

On Blender 4.4+ the add-on needs a one-line fix for the new layered-action API (`action.fcurves` was removed). `export_mu/animation.py` must collect fcurves from `action.layers[].strips[].channelbags[]`.
