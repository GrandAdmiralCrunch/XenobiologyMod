# Changelog

## 0.1.0 (2026-10-24): first public release
### Content
- 107 animated species on Kerbin (63), Laythe (37), Eve (5) and Jool (2), each with a 3D model, portrait and Field Guide silhouette.
- Trees of life for Kerbin, Duna (extinct), Laythe, Eve and Jool: 91 clades, 30 fossil types and 4 panspermia events.
- Three lairs: the Cyclops' Cave, the Glowworm Grotto and the Glimmering Reef. One landmark fossil: the Fallen Titan.
- Geysers and fumaroles on Laythe's uplands (new `XENO_FEATURE` node). Geyserkites gather around them.
- With Microbiology Expansion: its microbes are placed on the trees of life, and the Mun, Minmus, Dres, Eeloo and Tylo get microbial biospheres, plus two new crossings (the Munar Splash and the Chlorine Rain).

### Gameplay
- Observation (EVA), fossil study, lair surveys and live specimen capture, each giving science.
- Parts: Xenofauna Tracking Camera, Hydrophone, CO-Z Containment Unit.
- Lab analysis: scientists in any science lab analyse CO-Z specimens and fossil samples. Each new species or fossil type analysed gives science and +1 evidence for its lineage.
- Rideable sleeping animals.

### For modders
- Config-driven content: `XENO_BIOSPHERE`, `XENO_CLADE`, `XENO_LIFEFORM`, `XENO_FOSSIL`, `XENO_PANSPERMIA`, `XENO_LAIR`, `XENO_FEATURE`.
- `xeno_tool.py` validates configs, prints trees and renders silhouettes.
- `FOREST {}` lairs (generated forests) are in the plugin but marked experimental. No stock forest ships in this release.
