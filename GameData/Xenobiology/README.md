# Xenobiology

**Animated alien wildlife, fossils and trees of life for Kerbal Space Program 1.12.**

Xenobiology puts living, moving creatures on the planets of the Kerbol system. Herds graze, flocks take off when you land, things swim under Laythe's waves, and some of them do not want you there. Scientists can study fossils in the rock, catch small animals for the lab, and fill in a Field Guide where each world's tree of life is revealed branch by branch, including the panspermia events that carried life from one world to another.

> **Status: v0.1.0, first public release.** Expect rough edges. Please report problems with your `KSP.log` attached (see [Reporting bugs](#reporting-bugs)).

## Features
- **107 animated species** on Kerbin, Laythe, Eve and Jool: grazing herds, birds, insects, ocean life, a cyclops that throws boulders, sky leviathans and more. Each has its own behaviour (skittish, curious, territorial, aggressive), daily routine, sounds and particle effects.
- **Field Guide** (toolbar button): species pages with portraits and silhouettes, a fossil catalogue, and an interactive **tree of life** for every biosphere. Branches stay hidden until you gather enough evidence.
- **Panspermia.** Some trees lead back to another world. Find the evidence and the Field Guide links the two trees: Duna seeded Kerbin, Kerbin's sea life reached Laythe, Laythe's animals fell into Jool's sky.
- **30 fossil types** (one of them a kilometre-long landmark) for scientists to study on EVA. Each adds evidence to the lineages it belongs to.
- **Lairs:** the Cyclops' Cave, the Glowworm Grotto, and the Glimmering Reef, a 200 m coral reef with tunnels and a cavern you can dive through.
- **Geysers and fumaroles** on Laythe's uplands, with geyserkites riding their steam.
- **Parts:** a Xenofauna Tracking Camera, a Hydrophone that hears sea life up to 4 km away, and the CO-Z Containment Unit for live specimens.
- **Lab analysis.** Scientists in a Mobile Processing Lab (or any science lab) can analyse CO-Z specimens and fossil samples for extra science and extra evidence in the tree of life.
- **Rideable animals:** some sleeping creatures can be mounted by an EVA kerbal.
- **Science** in career and science modes for observations, photographs, recordings, fossil surveys, lair surveys, specimens and lab analyses.
- **For modders:** everything is defined in config files, so a planet pack can add a whole ecosystem without C#. See the [Modder's Guide](GameData/Xenobiology/ModdersGuide.md).

## Requirements
- Kerbal Space Program **1.12.x** (developed on 1.12.5)
- [ModuleManager](https://forum.kerbalspaceprogram.com/topic/50533-*) **(required)**

Optional:
- **Microbiology Expansion.** Its microbes become leaves on the trees of life, and the Mun, Minmus, Dres, Eeloo and Tylo get microbial biospheres of their own.
- **Parallax Continued.** Creatures stand on Parallax-displaced terrain.

## Installation
1. Download `Xenobiology-0.1.0.zip` from the [Releases](../../releases) page.
2. Copy the `GameData/Xenobiology` folder from the zip into your KSP `GameData` folder.
3. Make sure ModuleManager is installed.

The download is large (about 370 MB unpacked), because every creature is a full 3D model with textures.

To uninstall, delete `GameData/Xenobiology`. Discoveries are stored in each save (a `XenoScenario` node), and KSP ignores that node while the mod is missing.

## Playing
1. Land on Kerbin (or Laythe, or Eve...) and go on EVA. Wildlife appears a few hundred metres around you.
2. Get within range of a creature and press **O** (or right-click the kerbal and choose *Observe*) to catalogue it.
3. Scientists can **Study Fossil** at outcrops marked by a faint green glow.
4. Open the **Field Guide** from the toolbar to see what you have found and how the trees of life are filling in.

Settings (spawn density, creature limits, key bindings, spoiler-free mode) are in `GameData/Xenobiology/Settings.cfg`. **Alt+F8** opens a debug window.

## Compatibility notes
- Planet packs: worlds that are not installed are skipped. Renamed or rescaled stock bodies may place creatures oddly.
- Performance: the creature caps in `Settings.cfg` (`maxActiveCreatures`, `maxCreatureObjects`) are the main levers if your frame rate drops.

## Reporting bugs
Open an [issue](../../issues) with:
- what you were doing, and on which planet and biome;
- your `KSP.log` (in the KSP folder); lines from Xenobiology start with `[Xenobiology]`;
- your mod list, if it isn't a clean install.

## Building from source
The plugin source is in `Source/`. With the .NET SDK installed:

```
cd Source
dotnet build -c Release -p:KSPDIR="C:\path\to\Kerbal Space Program"
```

The DLL is written to `GameData/Xenobiology/Plugins`. `Tools/` (repository only) holds the Blender scripts that build the creature models, `xeno_dds.py` (texture conversion) and `xeno_tool.py` (config validator, tree printer and silhouette renderer).

## License
Code and assets are released under the MIT License (see [LICENSE](LICENSE)).

## Credits
- ModuleManager by sarbian, Blowfish and contributors.
- `.mu` export through io_object_mu by taniwha.
- Microbiology Expansion compatibility uses that mod's public data; Microbiology Expansion is a separate mod by its own authors.
