"""Xenobiology — generates the Kerbin birds & mammals expansion (clades, lifeforms, fossils) from one table.
Usage:  python kerbin_fauna_cfg.py > fragment.cfg     (the output is appended to Lifeforms/Stock/Kerbin.cfg)
MODEL clip names and speeds come from the creature factory's results (fauna_build.py, arch "bird" / "quad")."""

CLADES = [
    # name, parent, displayName, rank, era, threshold, colour, description
    ("kerbin_pennavia", "kerbin_aerokerba", "Pennavia", "Suborder", "~95 million years ago", 2, "0.45,0.62,0.85,1",
     "The feathered fliers. Where the older Aerokerba fly on stretched skin, pennavians grew feathers - light, replaceable, waterproof and, as it turned out, extremely good for showing off. They fold their wings neatly along their flanks on the ground and walk on two scaly legs."),
    ("kerbin_canoravia", "kerbin_pennavia", "Canoravia", "Family", "~30 million years ago", 1, "0.25,0.5,0.95,1",
     "The songsters. Small, loud, clever perching pennavians with a lot to say and no intention of saying it quietly."),
    ("kerbin_rapacia", "kerbin_pennavia", "Rapacia", "Family", "~55 million years ago", 1, "0.55,0.38,0.22,1",
     "Day hunters with hooked beaks, gripping talons and eyesight good enough to read a capsule's serial number from a kilometre up."),
    ("kerbin_noctavia", "kerbin_pennavia", "Noctavia", "Family", "~60 million years ago", 1, "0.62,0.52,0.36,1",
     "Night hunters. Their faces are dish-shaped sound collectors and their feather edges are fringed so they fly in near silence."),
    ("kerbin_natavia", "kerbin_pennavia", "Natavia", "Family", "~50 million years ago", 1, "0.2,0.5,0.4,1",
     "Waterfowl. Webbed feet, waterproofed feathers and broad, sieve-edged bills; as at home paddling on a lake as in the air above it."),
    ("kerbin_saccorostra", "kerbin_pennavia", "Saccorostra", "Family", "~35 million years ago", 1, "0.85,0.6,0.45,1",
     "Pouch-bills. Big coastal pennavians whose lower bill carries a stretchy throat pouch that doubles as a fishing net."),
    ("kerbin_cursoria", "kerbin_pennavia", "Cursoria", "Infraorder", "~70 million years ago", 2, "0.6,0.45,0.3,1",
     "Pennavians that gave flight back. Some became fast-running grazers of the open plains, some heavy ground foragers, and one lineage turned its wings into flippers and took to the polar seas."),
    ("kerbin_gallavia", "kerbin_cursoria", "Gallavia", "Family", "~40 million years ago", 1, "0.55,0.3,0.2,1",
     "Heavy-bodied ground foragers famous for their courtship displays. Most can still fly a short way, but would much rather run."),
    ("kerbin_ratipedes", "kerbin_cursoria", "Ratipedes", "Family", "~60 million years ago", 1, "0.3,0.28,0.26,1",
     "The giant runners. Flightless, long-necked and two-toed, they cover the plains in strides several metres long."),
    ("kerbin_pinnavia", "kerbin_cursoria", "Pinnavia", "Family", "~55 million years ago", 1, "0.15,0.2,0.3,1",
     "Flipper-wings. Cursorians that went back to the sea: they waddle on land and fly underwater."),
    ("kerbin_lactifera", "kerbin_quadrimembra", "Lactifera", "Class", "~200 million years ago", 2, "0.62,0.45,0.3,1",
     "Furred, warm-blooded quadrimembrans that feed their young on milk. Late arrivals on Kerbin that diversified fast once the big reptilian grazers declined."),
    ("kerbin_gliridentia", "kerbin_lactifera", "Gliridentia", "Order", "~55 million years ago", 1, "0.6,0.45,0.28,1",
     "The gnawers, whose front teeth never stop growing. Most are small; one is the size of a large dog and the calmest animal on the planet."),
    ("kerbin_ungulata", "kerbin_lactifera", "Ungulata", "Order", "~50 million years ago", 1, "0.45,0.32,0.2,1",
     "Hoofed grazers. They walk on the tips of their toes and live in herds that can run for hours."),
    ("kerbin_carnivorae", "kerbin_lactifera", "Carnivorae", "Order", "~45 million years ago", 2, "0.55,0.25,0.2,1",
     "The meat-eaters: shearing back teeth, forward-facing eyes and, in the larger species, a strong opinion about kerbals on EVA."),
    ("kerbin_ursoida", "kerbin_carnivorae", "Ursoida", "Family", "~20 million years ago", 1, "0.45,0.3,0.2,1",
     "Big, heavy, flat-footed omnivores that stand up on their hind legs to get a better look at things."),
    ("kerbin_lupoida", "kerbin_carnivorae", "Lupoida", "Family", "~25 million years ago", 1, "0.5,0.5,0.5,1",
     "Long-legged pack hunters that run their prey down and keep in touch with long-distance howls."),
]

BIRD_CLIPS = "idleAnim = idle, moveAnim = walk, fleeAnim = walk, alertAnim = alert, sleepAnim = sleep, glideAnim = glide, flapAnim = flap, takeoffAnim = takeoff, landAnim = land"
SPECIES = [
    dict(name="bluejeb", clade="kerbin_canoravia", display="Bluejeb", sci="Cyanojebus clamator", habitat="Flyer", biomes="Grasslands, Highlands, Shores",
         active="Day", temper="Skittish", group="2, 5", rarity=3, territory=0.75, size=0.28, speed=0.35, flee=1, alert=45, fleeD=10, observe=30, science=6,
         diet="kerbin_springhopper, kerbin_glintwing, seeds, other birds' eggs, anything left on a lander's ladder",
         desc="A loud, crested blue songster with a black necklace, named (inevitably) after Jebediah: noisy, fearless, and convinced every rocket on the pad is its personal property. Flocks hop about the grass scolding anything that moves, and flee in a squawking blue burst if you walk right up to them.",
         flight=dict(cruiseSpeed=9, minSpeed=5, maxSpeed=16, sinkRate=1.0, climbRate=3, takeoffTime=0.6, landTime=0.7, takeoffChance=0.25, minGlideTime=8, maxGlideTime=25, cruiseHeight=12),
         sleep=dict(sleepsAt="Night", napChance=0.02, wakeDistance=6, wakeChance=0.4),
         sounds=dict(idle="bluejeb_call", alert="bluejeb_call", idleInterval=12, volume=0.8, range=180),
         model=dict(BIRD_CLIPS=1, moveAnimSpeed=0.21, fleeAnimSpeed=0.21), proc=("Avian", "0.22,0.45,0.88,1", "0.93,0.94,0.96,1", 0.4)),
    dict(name="hawk", clade="kerbin_rapacia", display="Ridgetail Hawk", sci="Rapax caudirufus", habitat="Flyer", biomes="Grasslands, Highlands, Mountains, Badlands, Deserts",
         active="Day", temper="Skittish", group="1, 1", rarity=1.2, territory=0.6, size=0.55, speed=0.45, flee=1, alert=80, fleeD=35, observe=70, science=12,
         diet="kerbin_ribbonsnake, kerbin_bluejeb, kerbin_springhopper, kerbin_scuttler",
         desc="A broad-winged hunter that spends most of the day circling on thermals with barely a wingbeat, then drops like a stone on anything small that moves in the grass. Its scream carries for a kilometre. Perched, it sits bolt upright on a rock and watches you with an expression of mild disappointment.",
         flight=dict(cruiseSpeed=11, minSpeed=7, maxSpeed=24, sinkRate=0.45, climbRate=3, takeoffTime=1.0, landTime=1.0, takeoffChance=0.45, minGlideTime=40, maxGlideTime=120, cruiseHeight=60),
         sleep=dict(sleepsAt="Night", napChance=0.0, wakeDistance=10, wakeChance=0.5),
         sounds=dict(idle="hawk_scream", alert="hawk_scream", idleInterval=25, volume=1.0, range=700),
         model=dict(BIRD_CLIPS=1, moveAnimSpeed=0.5, fleeAnimSpeed=0.5), proc=("Avian", "0.45,0.29,0.16,1", "0.92,0.86,0.74,1", 1.2)),
    dict(name="owl", clade="kerbin_noctavia", display="Hollow Owl", sci="Strigops cavicola", habitat="Flyer", biomes="Grasslands, Highlands, Tundra, Mountains, Badlands",
         active="Night", temper="Skittish", group="1, 2", rarity=1.5, territory=0.55, size=0.45, speed=0.35, flee=0.8, alert=50, fleeD=8, observe=40, science=12,
         diet="kerbin_duskmoth, kerbin_scuttler, kerbin_ribbonsnake, kerbin_bluejeb",
         desc="A tufted night hunter with a face like a satellite dish and enormous orange eyes. It can turn its head almost all the way round, and when a kerbal walks past it does exactly that, slowly, without blinking. It flies in near silence and hoots from the ridges until dawn, then sleeps the day away in rock hollows.",
         flight=dict(cruiseSpeed=8, minSpeed=5, maxSpeed=14, sinkRate=0.8, climbRate=2.5, takeoffTime=1.0, landTime=1.0, takeoffChance=0.3, minGlideTime=15, maxGlideTime=40, cruiseHeight=18),
         sleep=dict(sleepsAt="Day", napChance=0.0, wakeDistance=5, wakeChance=0.3),
         sounds=dict(idle="owl_hoot", idleInterval=20, volume=0.9, range=450),
         model=dict(BIRD_CLIPS=1, moveAnimSpeed=0.37, fleeAnimSpeed=0.37), proc=("Avian", "0.55,0.44,0.3,1", "0.86,0.78,0.62,1", 1.1)),
    dict(name="duck", clade="kerbin_natavia", display="Greenhead Duck", sci="Anatella viridiceps", habitat="Flyer", biomes="Shores, Water, Grasslands",
         active="Any", temper="Skittish", group="3, 8", rarity=3, territory=0.7, size=0.6, speed=0.4, flee=1, alert=50, fleeD=22, observe=45, science=7,
         swims=True, swimSpeed=1.0, waterline=0.064, spread=2.0,
         diet="pond weed, seeds, kerbin_springhopper, small fry",
         desc="The drake has a glossy green head and white collar; the whole flock paddles about the shallows, dabbling tail-up for weed, and waddles ashore to graze. Approach and they burst off the water with a clatter of wings and a chorus of complaints, circle once, and land again somewhere just out of reach.",
         flight=dict(cruiseSpeed=14, minSpeed=9, maxSpeed=22, sinkRate=1.4, climbRate=4, takeoffTime=0.8, landTime=1.0, takeoffChance=0.12, minGlideTime=20, maxGlideTime=60, cruiseHeight=30),
         sleep=dict(sleepsAt="Night", napChance=0.05, wakeDistance=8, wakeChance=0.5),
         sounds=dict(idle="duck_quack", alert="duck_quack", idleInterval=14, volume=0.8, range=250),
         model=dict(BIRD_CLIPS=1, moveAnimSpeed=0.34, fleeAnimSpeed=0.34, swimAnim="swim", floatAnim="float", swimAnimSpeed=1.1), proc=("Avian", "0.62,0.6,0.57,1", "0.04,0.34,0.16,1", 1.6)),
    dict(name="swan", clade="kerbin_natavia", display="Lake Swan", sci="Cygnella regalis", habitat="Flyer", biomes="Water, Shores",
         active="Any", temper="Territorial", group="1, 4", rarity=1.2, territory=0.45, size=1.5, speed=0.6, flee=1.5, alert=45, fleeD=12, observe=50, science=12,
         swims=True, swimSpeed=0.9, waterline=0.161,
         diet="pond weed, water plants",
         desc="Elegant, enormous and white, with an S-curved neck and an orange bill. Pairs mate for life and defend their stretch of water against everything, rockets included. A swan will paddle straight at a splashed-down capsule, hissing and buffeting with its wings, and it does not appear to understand that it is outweighed by several tonnes. Taking off needs a long run across the water.",
         flight=dict(cruiseSpeed=15, minSpeed=10, maxSpeed=22, sinkRate=1.2, climbRate=3, takeoffTime=2.0, landTime=1.5, takeoffChance=0.06, minGlideTime=30, maxGlideTime=80, cruiseHeight=40),
         attack=dict(range=2.6, knockback=4, cooldown=6, duration=0.9, hitTime=0.4),
         sleep=dict(sleepsAt="Night", napChance=0.03, wakeDistance=6, wakeChance=0.5),
         sounds=dict(idle="swan_honk", alert="swan_honk", attack="swan_honk", idleInterval=30, volume=1.0, range=500),
         model=dict(BIRD_CLIPS=1, moveAnimSpeed=0.84, fleeAnimSpeed=0.84, swimAnim="swim", floatAnim="float", swimAnimSpeed=1.0, attackAnim="alert"), proc=("Avian", "0.95,0.95,0.93,1", "0.92,0.42,0.1,1", 1.65)),
    dict(name="pelican", clade="kerbin_saccorostra", display="Shore Pelican", sci="Saccorostrum litoralis", habitat="Flyer", biomes="Shores, Water",
         active="Day", temper="Skittish", group="2, 6", rarity=1.8, territory=0.55, size=1.4, speed=0.6, flee=1.2, alert=60, fleeD=20, observe=55, science=10,
         swims=True, swimSpeed=0.9, waterline=0.179,
         diet="kerbin_glassfin, other small fish",
         desc="A big grey seabird with a white head and a bill nearly as long as its body, slung with a stretchy pink pouch. Squadrons glide low along the surf in single file, rising and falling with the swell without a wingbeat, then crash-dive for fish. Ashore they stand about the beaches looking like committee members.",
         flight=dict(cruiseSpeed=12, minSpeed=8, maxSpeed=20, sinkRate=0.7, climbRate=3, takeoffTime=1.5, landTime=1.4, takeoffChance=0.25, minGlideTime=40, maxGlideTime=100, cruiseHeight=25),
         sleep=dict(sleepsAt="Night", napChance=0.05, wakeDistance=8, wakeChance=0.5),
         sounds=dict(idle="pelican_grunt", idleInterval=40, volume=0.7, range=120),
         model=dict(BIRD_CLIPS=1, moveAnimSpeed=0.83, fleeAnimSpeed=0.83, swimAnim="swim", floatAnim="float", swimAnimSpeed=1.0), proc=("Avian", "0.56,0.53,0.49,1", "0.93,0.91,0.84,1", 2.25)),
    dict(name="turkey", clade="kerbin_gallavia", display="Wild Turkey", sci="Gallavis superbus", habitat="Ground", biomes="Grasslands, Highlands",
         active="Day", temper="Territorial", group="3, 9", rarity=2.5, territory=0.6, size=1.1, speed=1.0, flee=7, alert=40, fleeD=12, observe=40, science=8,
         diet="seeds, roots, kerbin_springhopper, kerbin_scuttler",
         desc="Bronze-feathered ground birds with a bare blue head, a dangling red wattle and an ego to match. When a kerbal comes near, the toms fan their striped tails into a huge semicircle, drop their wings and strut. If that fails they gobble. If that fails they run, surprisingly fast.",
         sleep=dict(sleepsAt="Night", napChance=0.0, wakeDistance=6, wakeChance=0.4),
         sounds=dict(idle="turkey_gobble", alert="turkey_gobble", idleInterval=20, volume=0.9, range=300),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", sleepAnim="sleep", moveAnimSpeed=1.1, fleeAnimSpeed=4.44), proc=("Avian", "0.33,0.22,0.13,1", "0.62,0.72,0.88,1", 0)),
    dict(name="penguin", clade="kerbin_pinnavia", display="Collared Penguin", sci="Pinnavis torquata", habitat="Ground", biomes="Ice Caps, Northern Ice Shelf, Southern Ice Shelf, Tundra",
         active="Any", temper="Curious", group="4, 14", rarity=3, territory=0.7, size=0.9, speed=0.4, flee=0.9, alert=30, fleeD=6, observe=35, science=9,
         swims=True, swimSpeed=3.5, waterline=0.105, spread=1.6,
         diet="kerbin_glassfin, krill, kerbin_moonjelly (reluctantly)",
         desc="Upright black-and-white seabirds with a bright golden collar and an orange bill. Colonies stand about on the polar ice shelves and waddle over in a group to inspect anything new - landers, flags, kerbals - before losing interest all at once. On land they are slow and wobbly; in the sea they fly through the water faster than a kerbal can swim.",
         sounds=dict(idle="penguin_bray", idleInterval=18, volume=0.8, range=200),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="walk", alertAnim="alert", sleepAnim="sleep", moveAnimSpeed=0.39, fleeAnimSpeed=0.39, swimAnim="swim", floatAnim="float", swimAnimSpeed=3.5), proc=("Avian", "0.08,0.08,0.1,1", "0.96,0.96,0.93,1", 0)),
    dict(name="ostrich", clade="kerbin_ratipedes", display="Plains Ostrich", sci="Struthiops velox", habitat="Ground", biomes="Grasslands, Deserts, Badlands",
         active="Day", temper="Skittish", group="2, 6", rarity=1.5, territory=0.5, size=2.4, speed=1.5, flee=19, alert=120, fleeD=60, observe=90, science=14,
         diet="grass, seeds, succulents, small stones (for digestion), kerbin_springhopper",
         desc="The tallest bird on Kerbin: a black-plumed giant on two bare pink legs, with a long neck and a small, perpetually startled head. It cannot fly, and does not need to. A spooked flock sprints away at nearly 70 km/h with its white wing-plumes spread for balance, faster than most rovers. At dusk the males boom like distant engines.",
         sleep=dict(sleepsAt="Night", napChance=0.0, wakeDistance=12, wakeChance=0.6),
         sounds=dict(idle="ostrich_boom", idleInterval=30, volume=1.0, range=450),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", sleepAnim="sleep", moveAnimSpeed=1.61, fleeAnimSpeed=14.38), proc=("Avian", "0.08,0.07,0.07,1", "0.84,0.62,0.56,1", 0)),
    # ---------------- mammals
    dict(name="capybara", clade="kerbin_gliridentia", display="Capybara", sci="Hydrochoerus tranquillus", habitat="Ground", biomes="Shores, Grasslands, Water",
         active="Day", temper="Passive", group="1, 4", rarity=0.35, territory=0.25, size=1.2, speed=0.7, flee=2.4, alert=20, fleeD=6, observe=30, science=25,
         swims=True, swimSpeed=1.2, waterline=0.383,
         diet="grass, water plants",
         desc="A rare, barrel-shaped, entirely unbothered rodent of the riverbanks and lagoons, the largest of the gnawers. It spends its days grazing, soaking up to its eyes in warm water, and being sat on by bluejebs. Nothing on Kerbin seems to want to hurt it, and it returns the favour. Kerbals who find one usually stay much longer than they meant to.",
         sounds=dict(idle="capybara_purr", idleInterval=25, volume=0.6, range=80),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", moveAnimSpeed=0.81, fleeAnimSpeed=2.44, swimAnim="swim", floatAnim="float", swimAnimSpeed=1.2),
         proc=("Quadruped", "0.56,0.4,0.24,1", "0.45,0.3,0.18,1", 0)),
    dict(name="bison", clade="kerbin_ungulata", display="Plains Bison", sci="Bisonta magnidorsa", habitat="Ground", biomes="Grasslands, Highlands, Tundra",
         active="Any", temper="Skittish", group="8, 20", rarity=2, territory=0.5, size=3.0, speed=0.9, flee=8, alert=90, fleeD=40, observe=90, science=12, spread=7,
         diet="grass, sedges",
         desc="Huge shaggy grazers with a towering shoulder hump, a dark woolly cape and short curved horns. They move across the plains in herds of a dozen or more, grunting to one another. Startle one and the whole herd stampedes, a rolling wall of fur that shakes the ground and is best watched from inside a sturdy rover.",
         sounds=dict(idle="bison_grunt", alert="bison_grunt", idleInterval=22, volume=1.0, range=350),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", moveAnimSpeed=0.99, fleeAnimSpeed=8.9), proc=("Quadruped", "0.33,0.23,0.15,1", "0.27,0.17,0.1,1", 0)),
    dict(name="bear", clade="kerbin_ursoida", display="Highland Bear", sci="Ursops montanus", habitat="Ground", biomes="Highlands, Mountains, Tundra, Grasslands",
         active="Any", temper="Territorial", group="1, 2", rarity=0.8, territory=0.45, size=2.4, speed=1.0, flee=5, alert=60, fleeD=15, observe=60, science=16,
         diet="roots, berries, kerbin_glassfin, kerbin_ironhorn grubs, the snack locker of any unattended rover",
         desc="A massive brown omnivore with a shaggy coat, small round ears and long digging claws. It ambles over to investigate anything that smells interesting, rears up on its hind legs to get a better look, and will swat a kerbal who gets within arm's reach - hard enough to send them tumbling, though it means it as a warning. Back away slowly.",
         attack=dict(range=3.5, knockback=8, cooldown=6, duration=1.0, hitTime=0.45),
         sleep=dict(sleepsAt="Night", napChance=0.1, minNap=40, maxNap=120, wakeDistance=8, wakeChance=0.25),
         sounds=dict(alert="bear_growl", attack="bear_growl", volume=1.0, range=250),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", attackAnim="swipe", moveAnimSpeed=1.19, fleeAnimSpeed=6.97), proc=("Quadruped", "0.33,0.22,0.14,1", "0.38,0.26,0.16,1", 0)),
    dict(name="wolf", clade="kerbin_lupoida", display="Tundra Wolf", sci="Lupops borealis", habitat="Ground", biomes="Tundra, Highlands, Grasslands, Mountains, Ice Caps",
         active="Any", temper="Curious", group="3, 7", rarity=1.2, territory=0.45, size=1.9, speed=1.4, flee=9, alert=120, fleeD=25, observe=70, science=14, spread=5,
         diet="kerbin_bison, kerbin_glimmerback, kerbin_capybara, kerbin_snortle",
         desc="Grey pack hunters with long legs and amber eyes. A pack will shadow a kerbal across the tundra at a careful distance, stopping when they stop. When it first finds you the pack sits back and howls - a long, rising chorus that carries for kilometres and sends every grazer in earshot running. They rarely come close; when they do, a warning nip is all you get.",
         attack=dict(range=2.0, knockback=4, cooldown=8, duration=0.8, hitTime=0.4),
         roar=dict(duration=4, cooldown=120, range=400, scareRadius=250),
         sounds=dict(roar="wolf_howl", idle="wolf_howl", idleInterval=90, volume=1.0, range=1500),
         model=dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert", roarAnim="howl", moveAnimSpeed=1.62, fleeAnimSpeed=5.97), proc=("Quadruped", "0.46,0.45,0.43,1", "0.8,0.78,0.74,1", 0)),
]

FOSSILS = [
    dict(name="kerbin_feather_impression", display="Feathered Wing Impression", form="Bones", kind="Impression", biomes="Mountains, Highlands",
         evidence="kerbin_pennavia", age="88 million years", color="0.72,0.70,0.64,1", rarity=0.8, minLevel=1, study=25, science=18,
         desc="A slab of fine lake-bed shale holding a single spread wing, every feather printed down to its barbs. The finger bones show it belonged to an aerokerban, so feathers came after flight, not before."),
    dict(name="kerbin_egg_clutch", display="Fossil Egg Clutch", form="Shell", kind="Eggs", biomes="Deserts, Badlands, Grasslands",
         evidence="kerbin_cursoria", age="45 million years", color="0.86,0.8,0.68,1", rarity=0.7, minLevel=0, study=20, science=16,
         desc="A nest of eggs the size of fuel cells, half of them hatched and broken. The shell structure matches today's ostriches, but the clutch is twice as large: a giant runner once nested on these plains."),
    dict(name="kerbin_bear_skull", display="Short-faced Bear Skull", form="Bones", kind="Skull", biomes="Tundra, Highlands, Mountains",
         evidence="kerbin_carnivorae, kerbin_lactifera", age="1.2 million years", color="0.84,0.8,0.7,1", rarity=0.6, minLevel=1, study=25, science=20,
         desc="A broad, blunt-snouted skull with canines as long as a kerbal's finger, from an ice-age bear half again the size of today's Highland Bear. Wear on the molars says it ate mostly plants. Mostly."),
]

def blk(name, d, ind="    "):
    out = [ind + name, ind + "{"]
    for k, v in d.items(): out.append(ind + "    %s = %s" % (k, v))
    out.append(ind + "}"); return out

def emit():
    L = ["", "// ============================================================ KERBIN BIRDS & MAMMALS",
         "// Feathered fliers (Pennavia, under Aerokerba) and furred milk-bearers (Lactifera, under Quadrimembra).",
         "// Generated by Tools/kerbin_fauna_cfg.py; models by the creature factory (fauna_birds.py: arch \"bird\", quad extras).",
         "// `swims = true` lets Ground/Flyer species paddle at the surface (and Flyers land on water); flocks of Flyers take",
         "// off together and fly in formation behind their leader. Clips: flapAnim (climbing), swimAnim / floatAnim (on water).", ""]
    for n, par, disp, rank, era, th, col, desc in CLADES:
        L += ["XENO_CLADE", "{", "    name = " + n, "    parent = " + par, "    biosphere = kerbin_biosphere", "    displayName = " + disp,
              "    rank = " + rank, "    era = " + era, "    revealThreshold = %d" % th, "    color = " + col, "    description = " + desc, "}", ""]
    for s in SPECIES:
        n = "kerbin_" + s["name"]; cap = s["name"][0].upper() + s["name"][1:]
        L += ["XENO_LIFEFORM", "{", "    name = " + n, "    body = Kerbin", "    clade = " + s["clade"], "    displayName = " + s["display"],
              "    scientificName = " + s["sci"], "    silhouette = Xenobiology/Textures/Silhouettes/" + n, "    portrait = Xenobiology/Textures/Portraits/" + n,
              "    habitat = " + s["habitat"], "    biomes = " + s["biomes"]]
        if s["active"] != "Any": L.append("    activeTime = " + s["active"])
        L += ["    temperament = " + s["temper"], "    groupSize = " + s["group"], "    rarity = %g" % s["rarity"], "    territoryChance = %g" % s["territory"],
              "    size = %g" % s["size"], "    speed = %g" % s["speed"], "    fleeSpeed = %g" % s["flee"], "    alertDistance = %g" % s["alert"],
              "    fleeDistance = %g" % s["fleeD"], "    observeRange = %g" % s["observe"], "    scienceValue = %g" % s["science"]]
        if s.get("swims"): L += ["    swims = true", "    swimSpeed = %g" % s["swimSpeed"], "    waterline = %g" % s["waterline"]]
        if s.get("spread"): L.append("    groupSpread = %g" % s["spread"])
        L += ["    diet = " + s["diet"], "    description = " + s["desc"]]
        if "flight" in s: L += blk("FLIGHT", s["flight"])
        if "sleep" in s: L += blk("SLEEP", s["sleep"])
        if "attack" in s: L += blk("ATTACK", s["attack"])
        if "roar" in s: L += blk("ROAR", s["roar"])
        if "sounds" in s: L += blk("SOUNDS", {k: ("Xenobiology/Sounds/" + v if isinstance(v, str) else v) for k, v in s["sounds"].items()})
        m = dict(s["model"]); md = {"path": "Xenobiology/Models/Kerbin/%s/%s" % (cap, s["name"])}
        if m.pop("BIRD_CLIPS", None):
            for kv in BIRD_CLIPS.split(", "):
                k, v = kv.split(" = "); md[k] = v
        md.update(m)
        L += blk("MODEL", md)
        plan, c1, c2, span = s["proc"]
        pr = {"bodyPlan": plan, "color": c1, "accentColor": c2}
        if plan == "Avian": pr.update(bodyLength=0.5, bodyWidth=0.25, legLength=0.15, headSize=0.15, tailLength=0.2, wingSpan=span or 0.8)
        else: pr.update(bodyLength=0.9, bodyWidth=0.45, legLength=0.4, headSize=0.3, tailLength=0.15)
        L += blk("PROCEDURAL", pr)
        L += ["}", ""]
    L.append("// ------------------------------------------------------------ fossils")
    for f in FOSSILS:
        L += ["XENO_FOSSIL", "{", "    name = " + f["name"], "    body = Kerbin", "    displayName = " + f["display"],
              "    silhouette = Xenobiology/Textures/Silhouettes/fossil_" + f["name"], "    portrait = Xenobiology/Textures/Portraits/fossil_" + f["name"],
              "    form = " + f["form"], "    kind = " + f["kind"], "    biomes = " + f["biomes"], "    evidenceFor = " + f["evidence"], "    evidence = 1",
              "    age = " + f["age"], "    color = " + f["color"], "    rarity = %g" % f["rarity"], "    minLevel = %d" % f["minLevel"],
              "    studyTime = %d" % f["study"], "    scienceValue = %d" % f["science"], "    description = " + f["desc"]]
        L += blk("MODEL", {"path": "Xenobiology/Models/Fossils/Kerbin/" + f["name"]})
        L += ["}", ""]
    return "\n".join(L)

if __name__ == "__main__":
    print(emit())
