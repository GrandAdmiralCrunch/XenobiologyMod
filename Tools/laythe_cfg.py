# Generates the XENO_LIFEFORM / XENO_FOSSIL blocks for the Laythe expansion (appended to Lifeforms/Stock/Laythe.cfg).
# Usage: python laythe_cfg.py [factory_results.json] > laythe_new.cfg
# The optional JSON (variant -> cfg dict from fauna_build.py) supplies the MODEL animation speeds.
import json, sys

ANIMS = {
    "fish":     dict(idleAnim="idle", moveAnim="swim", fleeAnim="swim", alertAnim="idle", leapAnim="swim"),
    "ceph":     dict(idleAnim="idle", moveAnim="swim", fleeAnim="jet", alertAnim="alert", attackAnim="attack"),
    "serpent":  dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="alert"),
    "avian":    dict(idleAnim="glide", moveAnim="glide", fleeAnim="flap", alertAnim="flap"),
    "quad":     dict(idleAnim="idle", moveAnim="walk", fleeAnim="run", alertAnim="alert"),
    "floater":  dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="idle"),
    "blob":     dict(idleAnim="idle", moveAnim="move", fleeAnim="move", alertAnim="idle"),
    "sessile":  dict(idleAnim="idle", moveAnim="idle", fleeAnim="idle", alertAnim="alert"),
}

OVERRIDE = {"thrumwing": dict(idleAnim="flap", moveAnim="flap")}   # insects never glide

# name: (variant, folder, arch, fields, blocks)   fields are written in order; blocks are raw text
S = []
def sp(name, variant, arch, look, f, blocks=""):
    S.append((name, variant, arch, look, f, blocks))

# ------------------------------------------------------------------ Pinnata
sp("laythe_leviathan", "leviathan", "fish", ("Fish", "0.35,0.45,0.55,1", "0.75,0.85,0.9,1"), dict(
    clade="laythe_cetopinnata", displayName="Veilcheek Leviathan", scientificName="Velobucca magna",
    habitat="Water", biomes="The Sagen Sea, Degrasse Sea, Crescent Bay", temperament="Passive", groupSize="1, 3",
    rarity=0.35, territoryChance=0.35, size=38, speed=3, fleeSpeed=5, fleeDistance=25, alertDistance=140, waterline=4, observeRange=300, scienceValue=45,
    diet="Planktarchae Laythensis, Photocyanus Laythensis, laythe_bloomjelly",
    description="A 38-metre filter feeder that cruises Laythe's open seas with its mouth agape. Its cheeks are vast translucent pouches; when it feeds you can see the water - and whatever was in it - being sieved through rows of pale combs. It breaches without warning, and the sound carries for kilometres."),
    """    LEAP
    {
        height = 8
        length = 50
        duration = 4.5
        chance = 0.06
        whenFleeing = false
        cooldown = 90
    }
    SOUNDS
    {
        idle = Xenobiology/Sounds/leviathan_song
        idleInterval = 40
        volume = 1.0
        range = 1500
    }
""")
sp("laythe_shasta", "shasta", "fish", ("Fish", "0.3,0.38,0.42,1", "0.8,0.8,0.75,1"), dict(
    clade="laythe_rhynchopinna", displayName="Longsnout Shasta", scientificName="Rhynchopinna shastae",
    habitat="Underwater", biomes="The Sagen Sea, Degrasse Sea, Shallows, Crescent Bay", temperament="Territorial", groupSize="1, 2",
    rarity=0.5, size=18, speed=4, fleeSpeed=11, fleeDistance=12, alertDistance=90, minAltitude=4, maxAltitude=45, observeRange=150, scienceValue=32,
    diet="laythe_silverfin, laythe_nebcrest, laythe_slimeeel",
    description="A sleek marine predator with a needle snout as long as a kerbal is tall, lined with interlocking teeth. It drives into slime-eel schools at speed and comes out with a mouthful. It treats swimming kerbals as rivals rather than prey - which is not as reassuring as it sounds."),
    """    ATTACK
    {
        range = 12
        knockback = 9
        cooldown = 8
        duration = 1.0
        hitTime = 0.45
    }
""")
sp("laythe_trifin", "trifin", "serpent", ("Serpent", "0.55,0.75,0.8,1", "0.95,0.7,0.35,1"), dict(
    clade="laythe_trigonopinna", displayName="Trifin Skimmer", scientificName="Trigonopinna saltatrix",
    habitat="Water", biomes="Shallows, Crater Bay, Crescent Bay, The Sagen Sea", temperament="Passive", groupSize="2, 6",
    rarity=1.2, size=2.6, speed=3, fleeSpeed=9, fleeDistance=20, alertDistance=40, waterline=0.4, observeRange=60, scienceValue=14,
    description="An eel-like fish with a flat, disc-shaped head and three fins at the tail. Docile and curious, it spends its life just under the surface - until something startles it, when it shoots out of the water and skips across the waves in long arcing leaps."),
    """    LEAP
    {
        height = 3
        length = 14
        duration = 1.6
        chance = 0.2
        whenFleeing = true
        cooldown = 5
    }
""")
sp("laythe_screwtail", "screwtail", "fish", ("Fish", "0.6,0.7,0.75,1", "0.95,0.5,0.25,1"), dict(
    clade="laythe_trigonopinna", displayName="Screwtail", scientificName="Cochleopinna rotor",
    habitat="Underwater", biomes="Shallows, Crater Bay, Crescent Bay, The Sagen Sea, Degrasse Sea", temperament="Skittish", groupSize="2, 5",
    rarity=0.9, size=1.3, speed=3, fleeSpeed=15, fleeDistance=25, alertDistance=40, minAltitude=2, maxAltitude=35, observeRange=35, scienceValue=20,
    description="The fastest fish on Laythe. In place of a tail fin it has a living propeller: a helical, bony tail that genuinely rotates on a ring-shaped joint, driven by muscle bands in its hindbody. It is the only known animal with a true rotary joint - an evolutionary wonder that began as a sac on the back of a bottom-crawling larva."),
    """    LEAP
    {
        height = 1.5
        length = 9
        duration = 0.9
        chance = 0.04
        whenFleeing = true
        cooldown = 10
    }
""")
sp("laythe_screwlarva", "screwlarva", "serpent", ("Serpent", "0.55,0.5,0.4,1", "0.8,0.6,0.4,1"), dict(
    clade="laythe_trigonopinna", displayName="Screwtail Larva", scientificName="Cochleopinna rotor (larva)",
    lifeStageOf="laythe_screwtail", lifeStage="Larva",
    habitat="Underwater", seafloor="true", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Passive", groupSize="2, 6", groupSpread=2,
    rarity=0.8, size=0.6, speed=0.4, fleeSpeed=1, fleeDistance=4, alertDistance=10, minAltitude=0.1, maxAltitude=0.3, observeRange=12, scienceValue=10,
    diet="Biofilmar Laythensis",
    description="A slow, grub-like bottom feeder that grazes biofilm off rocks. As it matures a swollen sac grows on its back end. One day the sac splits, and out unfolds the screw-shaped tail of an adult screwtail."),
    "")
sp("laythe_geyserkite", "geyserkite", "avian", ("Avian", "0.45,0.3,0.25,1", "0.95,0.6,0.25,1"), dict(
    clade="laythe_trigonopinna", displayName="Geyserkite", scientificName="Aerorhombus fumivorus",
    habitat="Air", biomes="Peaks, Crater Island, Poles", temperament="Passive", groupSize="1, 4",
    rarity=0.8, size=3, speed=6, fleeSpeed=10, fleeDistance=30, alertDistance=60, minAltitude=30, maxAltitude=220, observeRange=120, scienceValue=24,
    diet="Deepanaero Laythensis, volcanic gases",
    description="A flat, kite-shaped flier descended from leaping skimmers. It rides the hot columns above Laythe's fumaroles and geysers, straining sulfur-eating microbes out of the exhaust through gill-slits on its underside. It trails a faint plume of its own vapour."),
    """    EMITTER
    {
        kind = Steam
        when = Always
        offset = 0,0,-1.5
        rate = 5
        lifetime = 4
        speed = 0.2
        size = 0.8
        sizeGrow = 3
        radius = 0.3
        color = 0.85,0.85,0.8,0.25
        colorEnd = 0.9,0.9,0.9,0
    }
""")
sp("laythe_voidmaw", "voidmaw", "fish", ("Fish", "0.08,0.08,0.12,1", "0.3,0.7,0.9,1"), dict(
    clade="laythe_abyssopinna", displayName="Voidmaw", scientificName="Abyssostoma inane",
    habitat="Underwater", biomes="The Sagen Sea, Degrasse Sea", temperament="Passive", groupSize="1, 2",
    rarity=0.7, size=1.8, speed=1.2, fleeSpeed=4, fleeDistance=6, alertDistance=15, minAltitude=60, maxAltitude=400, observeRange=30, scienceValue=20,
    description="A deep-water fish that is almost entirely mouth, ringed with glass-clear fangs and dotted with blue photophores. It looks like a nightmare and behaves like a lamp: it drifts, gapes, and swallows whatever glowing plankton blunders in. Completely harmless to anything larger than its own head."),
    "")
sp("laythe_nebcrest", "nebcrest", "fish", ("Fish", "0.95,0.9,0.7,1", "0.1,0.1,0.12,1"), dict(
    clade="laythe_pinnata", displayName="Nebcrest", scientificName="Vexillopinna laythensis",
    habitat="Underwater", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Skittish", groupSize="3, 8", groupSpread=2,
    rarity=1.4, size=0.7, speed=1.5, fleeSpeed=6, fleeDistance=10, alertDistance=20, minAltitude=2, maxAltitude=20, observeRange=20, scienceValue=10,
    description="A tall, flat reef fish banded in cream, black and gold, with a long trailing pennant fin streaming from its crest. Small groups patrol the chalk coral, picking at polyps with their tube-snouts."),
    "")
sp("laythe_slimeeel", "slimeeel", "serpent", ("Serpent", "0.5,0.6,0.4,1", "0.75,0.8,0.55,1"), dict(
    clade="laythe_myxopinna", displayName="Swarm Slime Eel", scientificName="Myxopinna gregaria",
    habitat="Underwater", biomes="Shallows, Crater Bay, Crescent Bay, The Sagen Sea, Degrasse Sea", temperament="Skittish", groupSize="14, 24", groupSpread=1.6,
    rarity=1.0, size=1.1, speed=2, fleeSpeed=6, fleeDistance=12, alertDistance=25, minAltitude=3, maxAltitude=30, observeRange=25, scienceValue=10,
    description="Pale, slick eels that travel in dense, writhing schools. When threatened the whole school releases a cloud of mucus that clogs the gills of anything trying to eat them - which is why the shastas hit them so fast."),
    "")
# ------------------------------------------------------------------ Cephalothalassa
sp("laythe_colossalsquid", "colossalsquid", "ceph", ("Floater", "0.55,0.12,0.15,1", "0.9,0.4,0.3,1"), dict(
    clade="laythe_lampteuthida", displayName="Colossal Squid", scientificName="Lampteuthis colossus",
    habitat="Underwater", biomes="The Sagen Sea, Degrasse Sea, Crescent Bay", temperament="Passive", groupSize="3, 6", groupSpread=28,
    rarity=0.5, size=14, speed=2.5, fleeSpeed=9, fleeDistance=20, alertDistance=60, minAltitude=30, maxAltitude=220, observeRange=120, scienceValue=36,
    description="Fourteen-metre squids that hunt in packs in the dark water below 30 metres. Their eyes are the size of dinner plates and tuned for near-total darkness - so a lamp is agony to them. Show a light at night or in the deep and the whole pack comes for it, flashing red. TURN YOUR LIGHTS OFF."),
    """    LIGHT
    {
        range = 300
        aggroTime = 25
        chaseSpeed = 11
        darkOnly = true
        darkDepth = 40
    }
    ATTACK
    {
        range = 16
        knockback = 9
        cooldown = 7
        duration = 1.4
        hitTime = 0.5
        onlyWhenProvoked = true
    }
    EMITTER
    {
        kind = Motes
        when = Provoked
        rate = 30
        lifetime = 0.8
        speed = 0.5
        size = 1.2
        radius = 3
        color = 1,0.15,0.1,0.8
        colorEnd = 0.6,0,0,0
    }
""")
sp("laythe_kraken", "kraken", "ceph", ("Floater", "0.2,0.12,0.18,1", "0.4,0.8,0.9,1"), dict(
    clade="laythe_lampteuthida", displayName="Abyssal Kraken", scientificName="Bathykraken laythensis",
    habitat="Underwater", seafloor="true", biomes="The Sagen Sea, Degrasse Sea", temperament="Passive", groupSize="1",
    rarity=0.15, territoryChance=0.25, size=55, speed=1.2, fleeSpeed=4, fleeDistance=15, alertDistance=120, minAltitude=6, maxAltitude=6, observeRange=350, scienceValue=90,
    description="The largest predator on Laythe: a 55-metre squid that lies on the deep seafloor with its arms spread like a starfish, invisible except for slow ripples of blue light along its arms. It ignores everything - except light. A lit submarine or a diver's lamp anywhere within half a kilometre will bring it up off the bottom, and it does not give up easily."),
    """    LIGHT
    {
        range = 600
        aggroTime = 40
        chaseSpeed = 9
        darkOnly = true
        darkDepth = 80
    }
    ATTACK
    {
        range = 45
        knockback = 18
        cooldown = 10
        duration = 2.4
        hitTime = 0.55
        onlyWhenProvoked = true
    }
    SOUNDS
    {
        alert = Xenobiology/Sounds/kraken_rumble
        attack = Xenobiology/Sounds/kraken_rumble
        volume = 1.0
        range = 900
    }
""")
sp("laythe_capwright", "capwright", "ceph", ("Floater", "0.75,0.45,0.35,1", "0.85,0.8,0.7,1"), dict(
    clade="laythe_cephalothalassa", displayName="Capwright", scientificName="Manipulus modificapus",
    habitat="Underwater", seafloor="true", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Curious", groupSize="1",
    rarity=0.8, size=1.2, speed=0.8, fleeSpeed=3, fleeDistance=3, alertDistance=15, minAltitude=0.2, maxAltitude=0.4, observeRange=15, scienceValue=24,
    description="A small, many-armed reef dweller that builds itself a hat. Its arms are tipped with fine manipulating pads, and it spends its life chipping fragments off chalk coral, shells and bright stones and cementing them onto its own head-cap, rebuilding it whenever it outgrows it. No two caps are alike. It is fascinated by kerbals and will happily inspect a diver's boots for decorating material."),
    "")
sp("laythe_slughorn", "slughorn", "blob", ("Blob", "0.85,0.55,0.3,1", "0.4,0.2,0.5,1"), dict(
    clade="laythe_limacomorpha", displayName="Slughorn", scientificName="Limacoceras planum",
    habitat="Underwater", seafloor="true", biomes="Shallows, Crater Bay, Crescent Bay, The Sagen Sea", temperament="Passive", groupSize="1, 2",
    rarity=1.0, size=4.5, speed=0.6, fleeSpeed=1.2, fleeDistance=4, alertDistance=8, minAltitude=0, maxAltitude=0.2, observeRange=25, scienceValue=15,
    diet="Biofilmar Laythensis, Thalassobacter Laythensis",
    description="A large, flattened sea slug that glides over the seabed on a rippling foot, grazing a clean stripe through the biofilm. Two tall horns on its head taste the water; a ruff of orange-and-violet cerata along its back is full of borrowed stinging cells."),
    "")
sp("laythe_saponator", "saponator", "blob", ("Blob", "0.9,0.85,0.95,1", "0.6,0.75,0.95,1"), dict(
    clade="laythe_limacomorpha", displayName="Saponator", scientificName="Spumifex lavator",
    habitat="Water", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Passive", groupSize="1, 3",
    rarity=0.9, size=1.8, speed=0.4, fleeSpeed=1, fleeDistance=5, alertDistance=10, waterline=0.25, observeRange=20, scienceValue=14,
    diet="Biofilmar Laythensis",
    description="A pale floating slug that lives at the surface and is obsessively clean. Glands along its sides secrete surfactants that lift fouling organisms off its skin - and froth up a constant fizz of bubbles around it. Startle one and it vanishes in a cloud of foam."),
    """    EMITTER
    {
        kind = Bubbles
        when = Always
        offset = 0,0.1,0
        rate = 14
        lifetime = 5
        speed = 0.15
        size = 0.18
        sizeGrow = 1.4
        radius = 0.7
        gravity = -0.02
        color = 0.9,0.95,1,0.7
        colorEnd = 1,1,1,0
    }
    EMITTER
    {
        kind = Bubbles
        when = Fleeing
        rate = 120
        lifetime = 3
        speed = 0.6
        size = 0.3
        sizeGrow = 2
        radius = 1
        gravity = -0.03
        color = 1,1,1,0.85
        colorEnd = 1,1,1,0
    }
""")
# ------------------------------------------------------------------ Raptopoda
sp("laythe_rakeclaw", "rakeclaw", "serpent", ("Serpent", "0.75,0.4,0.3,1", "0.95,0.75,0.5,1"), dict(
    clade="laythe_raptopoda", displayName="Rakeclaw", scientificName="Anomalopinna rapax",
    habitat="Underwater", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Curious", groupSize="1, 2",
    rarity=0.8, size=3.2, speed=2, fleeSpeed=5, fleeDistance=5, alertDistance=25, minAltitude=3, maxAltitude=40, observeRange=30, scienceValue=22,
    diet="laythe_slimeeel, laythe_nebcrest, laythe_screwlarva",
    description="A flattened, segmented swimmer that rows itself along with a skirt of overlapping lobes down each side. Two spiny raking limbs fold under its head; stalked compound eyes give it all-round vision. It looks like something out of the deepest fossil record - because, in a sense, it is."),
    "")
sp("laythe_thrumwing", "thrumwing", "avian", ("Avian", "0.2,0.3,0.2,1", "0.8,0.75,0.2,1"), dict(
    clade="laythe_raptopoda", displayName="Thrumwing", scientificName="Rhombopteron vesparius",
    habitat="Air", biomes="Peaks, Dunes, Crater Island, Shores", temperament="Curious", groupSize="2, 5", groupSpread=6,
    rarity=0.9, size=1.6, speed=7, fleeSpeed=12, fleeDistance=10, alertDistance=40, minAltitude=4, maxAltitude=35, observeRange=40, scienceValue=18,
    description="A big, armoured flying raptopod with four glassy wings that beat so fast they blur into a deep drone you feel in your chest. Thrumwings hunt in loose packs over the islands and will hover a few metres from a kerbal, mandibles clicking, before losing interest."),
    "")
sp("laythe_tidalcrawler", None, None, None, None, None)   # existing, moved to Raptopoda
# ------------------------------------------------------------------ Litoripedes
sp("laythe_archelon", "archelon", "quad", ("Quadruped", "0.35,0.45,0.35,1", "0.55,0.5,0.35,1"), dict(
    clade="laythe_chelonomorpha", displayName="Tidal Archelon", scientificName="Pseudarchelon laythensis",
    habitat="Ground", amphibious="true", biomes="Shores, Shallows, Crater Island, Crater Bay, Crescent Bay, Dunes", temperament="Passive", groupSize="1, 2",
    rarity=1.0, size=4.2, speed=0.7, fleeSpeed=1.6, fleeDistance=6, alertDistance=15, observeRange=30, scienceValue=18,
    description="A heavy, high-domed shell-back that hauls out on Laythe's beaches by day and walks along the seabed to feed. Its shell is crusted with chalk coral and seamat; its flippers end in blunt claws for digging. Some individuals are thought to be over three centuries old."),
    """    SLEEP
    {
        sleepsAt = Night
        napChance = 0.15
        wakeDistance = 3
        wakeChance = 0.3
    }
""")
sp("laythe_shorestega", "shorestega", "quad", ("Quadruped", "0.45,0.42,0.3,1", "0.25,0.3,0.25,1"), dict(
    clade="laythe_stegopoda", displayName="Shorestega", scientificName="Pseudostega litoralis",
    habitat="Ground", amphibious="true", biomes="Shores, Dunes, Crater Island, Shallows", temperament="Skittish", groupSize="1, 3",
    rarity=1.1, size=2.4, speed=0.9, fleeSpeed=3, fleeDistance=12, alertDistance=25, observeRange=25, scienceValue=14,
    description="A broad-headed, low-slung walker with a finned tail, sprawled limbs and a gulping mouth. It basks at the waterline and lurches into the surf when disturbed - the living image of the first animals that ever crawled out of Laythe's sea."),
    "")
sp("laythe_tidestilt", "tidestilt", "quad", ("Quadruped", "0.6,0.55,0.5,1", "0.3,0.45,0.55,1"), dict(
    clade="laythe_stegopoda", displayName="Tidestilt", scientificName="Grallator thalassicus",
    habitat="Ground", amphibious="true", biomes="Shores, Shallows, Crater Bay, Crescent Bay, Dunes", temperament="Passive", groupSize="1, 3",
    rarity=0.7, size=7, speed=1.4, fleeSpeed=3.5, fleeDistance=10, alertDistance=35, observeRange=60, scienceValue=26,
    description="A towering, slow-moving wader on four stilt-like legs, its small body slung high above the waves. Tidestilts wander between islands across the seabed, walking straight down into the sea and out again on the far side, sifting the bottom with a long, drooping proboscis."),
    "")
sp("laythe_wavesprinter", "wavesprinter", "quad", ("Quadruped", "0.25,0.55,0.5,1", "0.95,0.85,0.3,1"), dict(
    clade="laythe_hydrodromi", displayName="Wavesprinter", scientificName="Hydrodromus velox",
    habitat="Ground", walkOnWater="true", biomes="Shores, Shallows, Crater Bay, Crescent Bay, Crater Island", temperament="Skittish", groupSize="1, 4",
    rarity=1.1, size=1.4, speed=2, fleeSpeed=16, fleeDistance=40, alertDistance=70, observeRange=40, scienceValue=15,
    description="A slim, long-tailed lizard-like runner whose feet are fringed with water-repellent scales. When it panics it simply runs out to sea - pattering across the surface at a ridiculous speed and leaving a trail of spray."),
    """    EMITTER
    {
        kind = Splash
        when = Fleeing
        offset = 0,0,-0.3
        rate = 30
        lifetime = 0.7
        speed = 1.5
        size = 0.15
        sizeGrow = 2
        radius = 0.25
        gravity = 0.5
        color = 0.9,0.95,1,0.6
        colorEnd = 1,1,1,0
    }
""")
sp("laythe_skullkite", "skullkite", "avian", ("Avian", "0.85,0.82,0.72,1", "0.2,0.18,0.2,1"), dict(
    clade="laythe_ossipteryx", displayName="Skullkite", scientificName="Ossipteryx calvaria",
    habitat="Air", biomes="Peaks, Dunes, Crater Island, Shores", temperament="Curious", groupSize="1, 3",
    rarity=0.9, size=2.2, speed=9, fleeSpeed=15, fleeDistance=20, alertDistance=80, minAltitude=20, maxAltitude=120, observeRange=70, scienceValue=17,
    description="A gaunt flier whose skin is so thin that its pale skeleton shows through - skull, ribs, finger bones and all - with dark wing membranes stretched between. It circles silently over anything that might die soon. Kerbals find this unsettling."),
    "")
sp("laythe_peakglider", None, None, None, None, None)   # existing, moved to Ossipteryx
# ------------------------------------------------------------------ Aeromedusae
sp("laythe_skyreef", "skyreef", "floater", ("Floater", "0.75,0.55,0.6,1", "0.95,0.75,0.45,1"), dict(
    clade="laythe_aeromedusae", displayName="SkyReef", scientificName="Aerocorallium pendulum",
    habitat="Air", biomes="The Sagen Sea, Degrasse Sea, Shallows, Crescent Bay, Crater Bay, Shores", temperament="Passive", groupSize="1",
    rarity=0.08, territoryChance=0.12, size=80, speed=1.8, fleeSpeed=2.5, fleeDistance=30, alertDistance=100, minAltitude=320, maxAltitude=420, observeRange=700, scienceValue=65,
    circling="false", turnRate=2, maxClimbRate=0.25, cruiseChangeTime="150, 400",
    diet="Sporothrix Laythensis, Blastomyces Laythensis, airborne microbes",
    description="From a distance it looks like a drifting island turned upside down. The body is a huge, lobed, veined sac of lifting gas more than a hundred metres long, breathing slowly as it rides the wind. A whole reef of feeding colonies - branching corals, fans and polyps - hangs from its underside, and curtains of sticky, beaded tendrils up to 250 metres long trail behind it, filtering microbes and fungal spores out of Laythe's air. It almost never changes height. Its veins and tendrils glimmer at night."),
    """    EMITTER
    {
        kind = Motes
        when = Night
        offset = 0,-110,-40
        rate = 40
        lifetime = 6
        speed = 0.2
        size = 1.5
        radius = 60
        color = 0.6,1,0.75,0.7
        colorEnd = 0.4,0.9,0.6,0
    }
""")
# ------------------------------------------------------------------ Mycota
sp("laythe_bloomjelly", "bloomjelly", "floater", ("Floater", "0.85,0.75,0.4,1", "0.95,0.55,0.2,1"), dict(
    clade="laythe_siphonomycetes", displayName="Bloomjelly", scientificName="Siphonomyces florens",
    habitat="Underwater", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Passive", groupSize="10, 20", groupSpread=2.5,
    rarity=1.2, size=1.0, speed=0.4, fleeSpeed=0.8, fleeDistance=2, alertDistance=5, minAltitude=1, maxAltitude=8, observeRange=20, scienceValue=12,
    description="Not a jellyfish at all but a floating fungal colony: a chain of small golden bells strung along a hollow stem, each unit specialised to swim, sting, digest or release spores. They bloom by the million in sheltered bays, turning the water amber - and feeding everything from leviathans to slime eels."),
    """    EMITTER
    {
        kind = Motes
        when = Night
        rate = 3
        lifetime = 3
        speed = 0.1
        size = 0.2
        radius = 0.4
        color = 1,0.75,0.3,0.7
        colorEnd = 1,0.5,0.2,0
    }
""")
sp("laythe_seamat", "seamat", "sessile", ("Blob", "0.65,0.6,0.35,1", "0.85,0.75,0.4,1"), dict(
    clade="laythe_siphonomycetes", displayName="Fungal Seamat", scientificName="Thalassomyces stratus",
    habitat="Water", sessile="true", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Passive", groupSize="1, 2", groupSpread=40,
    rarity=0.7, size=30, speed=0, fleeSpeed=0, fleeDistance=1, alertDistance=1, waterline=0.1, observeRange=60, scienceValue=20,
    description="A floating fungal raft, metres thick and tens of metres across, that grows slowly outward across the sea surface. Mats bloom near coasts where nutrient-rich runoff feeds them; a big bloom can cover an entire bay. Each mat is one colony - and possibly one individual - trailing feeding filaments into the water below."),
    "")
sp("laythe_chalkcoral", "chalkcoral", "sessile", ("Blob", "0.85,0.82,0.72,1", "0.95,0.6,0.5,1"), dict(
    clade="laythe_lithomycetes", displayName="Chalkcap Coral", scientificName="Lithomyces crustatus",
    habitat="Underwater", seafloor="true", sessile="true", biomes="Shallows, Crater Bay, Crescent Bay", temperament="Passive", groupSize="3, 7", groupSpread=5,
    rarity=1.3, size=2.5, speed=0, fleeSpeed=0, fleeDistance=2, alertDistance=3, minAltitude=0, maxAltitude=0, observeRange=20, scienceValue=12,
    description="Branching fungal coral wrapped in a hard chalky shell. It grows a few millimetres a century and has been building Laythe's reefs for over a billion years. Soft feeding tips poke out of pores at the end of each branch, glowing faintly coral-pink, and pull back into the chalk when anything comes close."),
    "")
sp("laythe_puffburst", "puffburst", "sessile", ("Blob", "0.8,0.75,0.6,1", "0.6,0.5,0.35,1"), dict(
    clade="laythe_sporomycetes", displayName="Puffburst", scientificName="Crepitomyces explodens",
    habitat="Ground", sessile="true", biomes="Dunes, Shores, Crater Island, Peaks", temperament="Passive", groupSize="4, 10", groupSpread=1.8,
    rarity=1.4, size=0.6, speed=0, fleeSpeed=0, fleeDistance=1, alertDistance=1, observeRange=10, scienceValue=10,
    description="Papery fungal puffballs that grow in clusters on the black sand. Step on one - or near one - and it bursts in a dense cloud of spores, which drift for kilometres. The clouds are harmless to kerbals, though they leave suits smelling of mushrooms for days."),
    """    BURST
    {
        triggerRange = 1.4
        duration = 0.8
        regrowTime = 600
        message = <color=#D8C890>Pfff! A puffburst explodes in a cloud of spores.</color>
    }
    EMITTER
    {
        kind = Spores
        when = Burst
        offset = 0,0.3,0
        burst = 140
        rate = 0
        lifetime = 7
        speed = 1.6
        size = 0.5
        sizeGrow = 3
        radius = 0.3
        gravity = -0.004
        color = 0.75,0.7,0.5,0.75
        colorEnd = 0.7,0.65,0.5,0
    }
""")

FOSSILS = """
XENO_FOSSIL
{
    name = laythe_sporeash
    body = Laythe
    displayName = Spore-Ash Bed
    silhouette = Xenobiology/Textures/Silhouettes/fossil_stromatolite
    form = Stromatolite
    biomes = Peaks, Crater Island, Dunes
    evidenceFor = laythe_mycota
    evidence = 2
    age = 1.6 billion years
    color = 0.55,0.5,0.35,1
    rarity = 0.8
    minLevel = 1
    studyTime = 30
    scienceValue = 35
    description = Thin layers of volcanic ash packed with fossil fungal threads, 600 million years older than any Laythean animal. Something was growing here long before the Kerbin seed arrived.
}

XENO_FOSSIL
{
    name = laythe_filtercomb
    body = Laythe
    displayName = Leviathan Filter Comb
    silhouette = Xenobiology/Textures/Silhouettes/fossil_bones
    form = Bones
    biomes = Shores, Dunes
    evidenceFor = laythe_cetopinnata, laythe_pinnata
    age = 70 million years
    color = 0.8,0.78,0.7,1
    rarity = 0.7
    studyTime = 20
    scienceValue = 25
    description = A curved plate of fine bony bristles from the cheek of an ancient leviathan, three times the size of any living one.
}

XENO_FOSSIL
{
    name = laythe_krakenbeak
    body = Laythe
    displayName = Kraken Beak
    silhouette = Xenobiology/Textures/Silhouettes/fossil_bones
    form = Bones
    biomes = Shores, Crater Island
    evidenceFor = laythe_lampteuthida, laythe_cephalothalassa
    age = 40 million years
    color = 0.2,0.18,0.2,1
    rarity = 0.4
    minLevel = 2
    studyTime = 35
    scienceValue = 40
    description = A chitinous beak the size of a lander can, washed up and buried in beach sand. Only its owner's eyes were ever found larger.
}

XENO_FOSSIL
{
    name = laythe_raptorlimb
    body = Laythe
    displayName = Raking Limb
    silhouette = Xenobiology/Textures/Silhouettes/fossil_shell
    form = Shell
    biomes = Shores, Dunes, Crater Island
    evidenceFor = laythe_raptopoda
    age = 500 million years
    color = 0.6,0.45,0.3,1
    rarity = 1
    studyTime = 20
    scienceValue = 22
    description = A spiny, jointed grasping limb in fine shale. The earliest raptopods were already hunting with them half a billion years ago.
}

XENO_FOSSIL
{
    name = laythe_chalkreef
    body = Laythe
    displayName = Chalk Reef Terrace
    silhouette = Xenobiology/Textures/Silhouettes/fossil_stromatolite
    form = Stromatolite
    biomes = Shores, Crater Island
    evidenceFor = laythe_lithomycetes, laythe_mycota
    age = 1.1 billion years
    color = 0.85,0.82,0.75,1
    rarity = 1
    studyTime = 25
    scienceValue = 25
    description = A raised terrace of ancient fungal reef, its branches still recognisable after a billion years. The chalkcap corals living offshore are building the same structure today.
}
"""

def fmt(v):
    return str(v)

def main():
    res = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else {}
    out = ["", "// =====================================================================", "//  LAYTHE EXPANSION (generated by Tools/laythe_cfg.py)", "// =====================================================================", ""]
    for name, variant, arch, look, f, blocks in S:
        if variant is None: continue
        folder = variant[0].upper() + variant[1:]
        out.append("XENO_LIFEFORM\n{")
        out.append("    name = " + name)
        out.append("    body = Laythe")
        for k in ("clade", "displayName", "scientificName", "lifeStageOf", "lifeStage"):
            if k in f: out.append("    %s = %s" % (k, f[k]))
        out.append("    silhouette = Xenobiology/Textures/Silhouettes/" + name)
        out.append("    portrait = Xenobiology/Textures/Portraits/" + name)
        for k, v in f.items():
            if k in ("clade", "displayName", "scientificName", "lifeStageOf", "lifeStage", "description", "diet"): continue
            out.append("    %s = %s" % (k, fmt(v)))
        if "diet" in f: out.append("    diet = " + f["diet"])
        out.append("    description = " + f["description"])
        if blocks: out.append(blocks.rstrip("\n"))
        a = dict(ANIMS[arch]); a.update(OVERRIDE.get(variant, {})); r = dict(res.get(variant, {})); r.update(OVERRIDE.get(variant, {}))
        out.append("    MODEL\n    {")
        out.append("        path = Xenobiology/Models/Laythe/%s/%s" % (folder, variant))
        for k in ("idleAnim", "moveAnim", "fleeAnim", "alertAnim", "attackAnim", "leapAnim"):
            v = r.get(k, a.get(k))
            if v: out.append("        %s = %s" % (k, v))
        if "burst" in r or name == "laythe_puffburst": out.append("        burstAnim = burst")
        for k in ("moveAnimSpeed", "fleeAnimSpeed"):
            if k in r: out.append("        %s = %s" % (k, r[k]))
        out.append("    }")
        out.append("    // fallback if the model fails to load")
        out.append("    PROCEDURAL\n    {")
        out.append("        bodyPlan = " + look[0])
        out.append("        color = " + look[1])
        out.append("        accentColor = " + look[2])
        out.append("    }")
        out.append("}\n")
    out.append(FOSSILS)
    sys.stdout.write("\n".join(out))

if __name__ == "__main__":
    main()
